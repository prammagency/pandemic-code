import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
import concurrent.futures
from pathlib import Path
import re
import logging
import html2text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dreambot_api_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
INPUT_JSON = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\structured_entities.json"
OUTPUT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\extracted_content"
MAX_WORKERS = 5
REQUEST_DELAY = (1, 3)
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://dreambot.org/"
}

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def identify_page_structure(soup):
    """Identify the page structure to determine appropriate extraction strategy"""
    structure_info = {
        "type": "unknown",
        "format_version": "unknown",
        "has_summary_tables": False,
        "has_detail_sections": False,
        "has_nested_classes": False
    }
    
    # Determine page type based on various indicators
    title_text = ""
    title_elem = soup.select_one("h1.title, h2.title, div.header .title")
    if title_elem:
        title_text = title_elem.get_text().strip()
        
    if "Class" in title_text:
        structure_info["type"] = "class"
    elif "Interface" in title_text:
        structure_info["type"] = "interface"
    elif "Enum" in title_text:
        structure_info["type"] = "enum"
    elif "Annotation" in title_text:
        structure_info["type"] = "annotation"
    
    # Determine format version by checking key structural elements
    if soup.select_one("section.method-summary, section.method-details"):
        structure_info["format_version"] = "new"
    elif soup.select_one("table.memberSummary, .details"):
        structure_info["format_version"] = "old"
    
    # Check for presence of summary tables
    structure_info["has_summary_tables"] = bool(
        soup.select_one("section.method-summary, section.field-summary, table.memberSummary")
    )
    
    # Check for presence of detail sections
    structure_info["has_detail_sections"] = bool(
        soup.select_one("section.method-details, section.field-details, .details")
    )
    
    # Check for presence of nested classes
    structure_info["has_nested_classes"] = bool(
        soup.select_one("section.nested-class-summary, table.nestedClassSummary")
    )
    
    return structure_info

def flexible_select(soup, selectors, attribute=None, return_elements=False):
    """Try multiple selector patterns and extract text or attribute"""
    for selector in selectors:
        try:
            elements = soup.select(selector)
            if elements:
                if return_elements:
                    return elements
                if attribute:
                    values = [elem.get(attribute) for elem in elements if elem.get(attribute)]
                    if values:
                        return values
                else:
                    texts = [clean_text(elem.get_text()) for elem in elements]
                    if any(texts):
                        return texts
        except Exception as e:
            logger.debug(f"Selector failed: {selector}, Error: {str(e)}")
    return [] if not return_elements else None

def extract_nested_classes(soup, structure_info):
    """Extract information about nested classes"""
    nested_classes = []
    
    # Try different selectors based on page structure
    if structure_info["format_version"] == "new":
        nested_section = soup.select_one("section.nested-class-summary")
        if nested_section:
            nested_rows = nested_section.select("tbody tr")
            for row in nested_rows:
                class_cell = row.select_one("td.col-first a")
                if not class_cell:
                    continue
                    
                name = class_cell.get_text().strip()
                
                desc_cell = row.select_one("td.col-last div.block")
                desc = desc_cell.get_text().strip() if desc_cell else ""
                
                modifiers_cell = row.select_one("td.col-first code")
                modifiers = modifiers_cell.get_text().strip().split() if modifiers_cell else []
                
                nested_classes.append({
                    "name": name,
                    "description": clean_text(desc),
                    "modifiers": modifiers
                })
    else:
        # For old format
        nested_table = soup.select_one("table.nestedClassSummary")
        if nested_table:
            nested_rows = nested_table.select("tr")
            for row in nested_rows:
                class_cell = row.select_one("td.colFirst a")
                if not class_cell:
                    continue
                    
                name = class_cell.get_text().strip()
                
                desc_cell = row.select_one("td.colLast div.block")
                desc = desc_cell.get_text().strip() if desc_cell else ""
                
                modifiers_cell = row.select_one("td.colFirst")
                modifiers_text = modifiers_cell.get_text().strip() if modifiers_cell else ""
                modifiers = [m for m in modifiers_text.split() if m != name]
                
                nested_classes.append({
                    "name": name,
                    "description": clean_text(desc),
                    "modifiers": modifiers
                })
    
    # Fallback: Try text-based extraction for nested classes
    if not nested_classes:
        nested_section_headers = soup.select("h2, h3")
        for header in nested_section_headers:
            if "Nested Class" in header.get_text():
                section = header.find_next("ul")
                if section:
                    for li in section.select("li"):
                        name = li.get_text().strip()
                        if name:
                            nested_classes.append({
                                "name": name,
                                "description": "",
                                "modifiers": []
                            })
    
    return nested_classes

def extract_method_summary(soup, structure_info):
    """Extract the method summary table information"""
    methods_summary = []
    
    # For newer format
    if structure_info["format_version"] == "new":
        method_summary = soup.find("section", class_="method-summary")
        if method_summary:
            method_rows = method_summary.select("tbody tr")
            for row in method_rows:
                method_cell = row.select_one("td.col-first code a")
                if not method_cell:
                    continue
                    
                name = method_cell.get_text().strip()
                
                type_cell = row.select_one("td.col-first code")
                return_type = ""
                modifiers = []
                
                if type_cell:
                    full_text = type_cell.get_text().strip()
                    parts = full_text.split()
                    
                    if len(parts) > 1:
                        modifiers = parts[:-1]
                        return_type = parts[-1]
                
                desc_cell = row.select_one("td.col-last div.block")
                desc = desc_cell.get_text().strip() if desc_cell else ""
                
                is_deprecated = bool(row.select_one("td.col-first .deprecated-label"))
                
                methods_summary.append({
                    "name": name,
                    "return_type": return_type,
                    "modifiers": modifiers,
                    "description": clean_text(desc),
                    "deprecated": is_deprecated
                })
    else:
        # For older format
        method_tables = soup.select("table.memberSummary")
        for table in method_tables:
            caption = table.select_one("caption")
            if caption and "method" in caption.get_text().lower():
                method_rows = table.select("tr")
                for row in method_rows:
                    method_cell = row.select_one("td.colFirst code a")
                    if not method_cell:
                        continue
                        
                    name = method_cell.get_text().strip()
                    
                    type_cell = row.select_one("td.colFirst code")
                    return_type = ""
                    modifiers = []
                    
                    if type_cell:
                        full_text = type_cell.get_text().strip()
                        parts = full_text.split()
                        
                        if len(parts) > 1:
                            modifiers = parts[:-1]
                            return_type = parts[-1]
                    
                    desc_cell = row.select_one("td.colLast div.block")
                    desc = desc_cell.get_text().strip() if desc_cell else ""
                    
                    is_deprecated = bool(row.select_one("td.colFirst .deprecatedLabel"))
                    
                    methods_summary.append({
                        "name": name,
                        "return_type": return_type,
                        "modifiers": modifiers,
                        "description": clean_text(desc),
                        "deprecated": is_deprecated
                    })
    
    # Text-based fallback for method summary
    if not methods_summary:
        summary_section = None
        for header in soup.select("h2, h3"):
            if "Method Summary" in header.get_text():
                summary_section = header.find_next("ul")
                break
        
        if summary_section:
            for li in summary_section.select("li"):
                text = li.get_text().strip()
                if text:
                    # Try to extract method name and return type from text
                    match = re.search(r'(\w+)\(.*?\)', text)
                    if match:
                        name = match.group(1)
                        methods_summary.append({
                            "name": name,
                            "return_type": "",
                            "modifiers": [],
                            "description": clean_text(text),
                            "deprecated": False
                        })
    
    return methods_summary

def extract_method_details(soup, structure_info):
    """Extract detailed method information including parameters and return values"""
    methods_details = []
    
    # For newer format
    if structure_info["format_version"] == "new":
        method_details_section = soup.find("section", class_="method-details")
        if method_details_section:
            method_details = method_details_section.find_all("section", class_="detail")
            
            for detail in method_details:
                method_name_elem = detail.find("h3") or detail.find("h4")
                if not method_name_elem:
                    continue
                    
                method_name = method_name_elem.get_text().strip()
                
                signature_elem = detail.find("div", class_="member-signature")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                return_type = ""
                modifiers = []
                
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))([\w<>\[\]\.]+)\s+(\w+)\(', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        return_type = sig_match.group(2).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                parameters = []
                param_list = detail.select("dl.notes dt.parameter, dl.parameters dt")
                
                for param_elem in param_list:
                    param_name = param_elem.get_text().strip()
                    param_desc_elem = param_elem.find_next("dd")
                    param_desc = clean_text(param_desc_elem.get_text()) if param_desc_elem else ""
                    
                    param_type = ""
                    if signature:
                        param_pattern = rf'{param_name}\s+-\s+(.*?)(?:,|\))'
                        param_match = re.search(param_pattern, signature)
                        if param_match:
                            param_type = param_match.group(1).strip()
                    
                    parameters.append({
                        "name": param_name,
                        "type": param_type,
                        "description": param_desc
                    })
                
                return_info = {
                    "type": return_type,
                    "description": ""
                }
                
                return_desc_elem = detail.select_one("dl.notes dt.return + dd, dl.returns dd")
                if return_desc_elem:
                    return_info["description"] = clean_text(return_desc_elem.get_text())
                
                is_deprecated = bool(detail.select(".deprecated"))
                
                methods_details.append({
                    "name": method_name,
                    "signature": signature,
                    "return_type": return_type,
                    "modifiers": modifiers,
                    "description": description,
                    "parameters": parameters,
                    "return": return_info,
                    "deprecated": is_deprecated
                })
    else:
        # For older format
        method_details_section = soup.find("div", class_="details")
        if method_details_section:
            method_anchors = method_details_section.find_all("a", {"name": re.compile(r'.*')})
            
            for anchor in method_anchors:
                # Find the method detail section
                detail = anchor.find_parent("li") or anchor.find_parent("div", class_="detail")
                if not detail:
                    continue
                
                method_name_elem = detail.find("h4") or detail.find("h3")
                if not method_name_elem:
                    continue
                    
                method_name = method_name_elem.get_text().strip()
                
                signature_elem = detail.find("pre")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                return_type = ""
                modifiers = []
                
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))([\w<>\[\]\.]+)\s+(\w+)\(', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        return_type = sig_match.group(2).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                parameters = []
                param_sections = detail.select("dl.paramInfo dt, dl dt.paramLabel")
                
                for param_elem in param_sections:
                    param_name = param_elem.get_text().strip()
                    param_desc_elem = param_elem.find_next("dd")
                    param_desc = clean_text(param_desc_elem.get_text()) if param_desc_elem else ""
                    
                    param_type = ""
                    if signature:
                        param_pattern = rf'{param_name}\s+-\s+(.*?)(?:,|\))'
                        param_match = re.search(param_pattern, signature)
                        if param_match:
                            param_type = param_match.group(1).strip()
                    
                    parameters.append({
                        "name": param_name,
                        "type": param_type,
                        "description": param_desc
                    })
                
                return_info = {
                    "type": return_type,
                    "description": ""
                }
                
                return_desc_elem = detail.select_one("dl dt.returnLabel + dd, dl.returns dd")
                if return_desc_elem:
                    return_info["description"] = clean_text(return_desc_elem.get_text())
                
                is_deprecated = bool(detail.select(".deprecatedLabel"))
                
                methods_details.append({
                    "name": method_name,
                    "signature": signature,
                    "return_type": return_type,
                    "modifiers": modifiers,
                    "description": description,
                    "parameters": parameters,
                    "return": return_info,
                    "deprecated": is_deprecated
                })
    
    # Fallback method extraction using regex from raw HTML
    if not methods_details:
        method_sections = []
        method_detail_headers = soup.select("h2, h3")
        for header in method_detail_headers:
            if "Method Detail" in header.get_text():
                next_elem = header
                while next_elem:
                    next_elem = next_elem.find_next_sibling()
                    if next_elem and next_elem.name in ["h2", "h3"] and "Method Detail" not in next_elem.get_text():
                        break
                    if next_elem:
                        method_sections.append(next_elem)
        
        # If we found method sections, try to extract method information
        for section in method_sections:
            method_name_elem = section.find("h4") or section.find("h3")
            if not method_name_elem:
                continue
                
            method_name = method_name_elem.get_text().strip()
            
            # Look for signature
            signature_elem = section.find("pre") or section.find("code")
            signature = clean_text(signature_elem.get_text()) if signature_elem else ""
            
            # Look for description
            description_elem = section.find("div", class_="block") or section.find(lambda tag: tag.name == "p" and not tag.find_parent("dl"))
            description = clean_text(description_elem.get_text()) if description_elem else ""
            
            # Add basic method info
            methods_details.append({
                "name": method_name,
                "signature": signature,
                "return_type": "",
                "modifiers": [],
                "description": description,
                "parameters": [],
                "return": {"type": "", "description": ""},
                "deprecated": False
            })
    
    return methods_details

def extract_field_details(soup, structure_info):
    """Extract field information"""
    fields = []
    
    # For newer format
    if structure_info["format_version"] == "new":
        field_details_section = soup.find("section", class_="field-details")
        if field_details_section:
            field_details = field_details_section.find_all("section", class_="detail")
            
            for detail in field_details:
                field_name_elem = detail.find("h3") or detail.find("h4")
                if not field_name_elem:
                    continue
                    
                field_name = field_name_elem.get_text().strip()
                
                signature_elem = detail.find("div", class_="member-signature")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                field_type = ""
                modifiers = []
                
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))([\w<>\[\]\.]+)\s+(\w+)', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        field_type = sig_match.group(2).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                is_deprecated = bool(detail.select(".deprecated"))
                
                fields.append({
                    "name": field_name,
                    "signature": signature,
                    "type": field_type,
                    "modifiers": modifiers,
                    "description": description,
                    "deprecated": is_deprecated
                })
    else:
        # For older format
        field_details_section = soup.find("div", class_="details")
        if field_details_section:
            field_anchors = field_details_section.find_all("a", {"name": re.compile(r'.*')})
            
            for anchor in field_anchors:
                # Find the field detail section
                detail = anchor.find_parent("li") or anchor.find_parent("div", class_="detail")
                if not detail:
                    continue
                
                # Skip if this isn't a field section
                if detail.find("pre") and "(" in detail.find("pre").get_text():
                    continue  # Likely a method, not a field
                
                field_name_elem = detail.find("h4") or detail.find("h3")
                if not field_name_elem:
                    continue
                    
                field_name = field_name_elem.get_text().strip()
                
                signature_elem = detail.find("pre")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                field_type = ""
                modifiers = []
                
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))([\w<>\[\]\.]+)\s+(\w+)', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        field_type = sig_match.group(2).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                is_deprecated = bool(detail.select(".deprecatedLabel"))
                
                fields.append({
                    "name": field_name,
                    "signature": signature,
                    "type": field_type,
                    "modifiers": modifiers,
                    "description": description,
                    "deprecated": is_deprecated
                })
    
    # Field summary fallback
    if not fields:
        field_summary = soup.find("section", class_="field-summary") or soup.find("table", class_="memberSummary")
        if field_summary:
            field_rows = field_summary.select("tbody tr")
            for row in field_rows:
                # Try both formats
                field_cell = row.select_one("td.col-first code, td.colFirst code")
                if not field_cell:
                    continue
                    
                field_text = field_cell.get_text().strip()
                field_parts = field_text.split()
                
                if len(field_parts) < 2:
                    continue
                
                field_name = field_parts[-1]
                field_type = field_parts[-2] if len(field_parts) > 1 else ""
                modifiers = field_parts[:-2] if len(field_parts) > 2 else []
                
                desc_cell = row.select_one("td.col-last div.block, td.colLast div.block")
                description = clean_text(desc_cell.get_text()) if desc_cell else ""
                
                fields.append({
                    "name": field_name,
                    "signature": field_text,
                    "type": field_type,
                    "modifiers": modifiers,
                    "description": description,
                    "deprecated": False
                })
    
    return fields

def extract_constructor_details(soup, structure_info):
    """Extract constructor information"""
    constructors = []
    
    # For newer format
    if structure_info["format_version"] == "new":
        constructor_details_section = soup.find("section", class_="constructor-details")
        if constructor_details_section:
            constructor_details = constructor_details_section.find_all("section", class_="detail")
            
            for detail in constructor_details:
                constructor_name_elem = detail.find("h3") or detail.find("h4")
                if not constructor_name_elem:
                    continue
                    
                constructor_name = constructor_name_elem.get_text().strip()
                
                signature_elem = detail.find("div", class_="member-signature")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                modifiers = []
                
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))(\w+)\(', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                parameters = []
                param_list = detail.select("dl.notes dt.parameter, dl.parameters dt")
                
                for param_elem in param_list:
                    param_name = param_elem.get_text().strip()
                    param_desc_elem = param_elem.find_next("dd")
                    param_desc = clean_text(param_desc_elem.get_text()) if param_desc_elem else ""
                    
                    param_type = ""
                    if signature:
                        param_pattern = rf'{param_name}\s+-\s+(.*?)(?:,|\))'
                        param_match = re.search(param_pattern, signature)
                        if param_match:
                            param_type = param_match.group(1).strip()
                    
                    parameters.append({
                        "name": param_name,
                        "type": param_type,
                        "description": param_desc
                    })
                
                is_deprecated = bool(detail.select(".deprecated"))
                
                constructors.append({
                    "name": constructor_name,
                    "signature": signature,
                    "modifiers": modifiers,
                    "description": description,
                    "parameters": parameters,
                    "deprecated": is_deprecated
                })
    else:
        # For older format
        constructor_details_section = soup.find("div", class_="details")
        if constructor_details_section:
            constructor_anchors = constructor_details_section.find_all("a", {"name": re.compile(r'.*')})
            
            for anchor in constructor_anchors:
                # Find the constructor detail section
                detail = anchor.find_parent("li") or anchor.find_parent("div", class_="detail")
                if not detail:
                    continue
                
                constructor_name_elem = detail.find("h4") or detail.find("h3")
                if not constructor_name_elem:
                    continue
                    
                # Check if this is a constructor (no return type in signature)
                signature_elem = detail.find("pre")
                if not signature_elem:
                    continue
                    
                signature = clean_text(signature_elem.get_text())
                
                # Skip methods (has return type before name)
                if re.search(r'[\w<>\[\]\.]+\s+\w+\(', signature):
                    continue
                
                constructor_name = constructor_name_elem.get_text().strip()
                
                modifiers = []
                if signature:
                    sig_match = re.match(r'((?:[\w\s]+))(\w+)\(', signature)
                    if sig_match:
                        modifiers_str = sig_match.group(1).strip()
                        modifiers = modifiers_str.split() if modifiers_str else []
                
                description_elem = detail.find("div", class_="block")
                description = clean_text(description_elem.get_text()) if description_elem else ""
                
                parameters = []
                param_sections = detail.select("dl.paramInfo dt, dl dt.paramLabel")
                
                for param_elem in param_sections:
                    param_name = param_elem.get_text().strip()
                    param_desc_elem = param_elem.find_next("dd")
                    param_desc = clean_text(param_desc_elem.get_text()) if param_desc_elem else ""
                    
                    param_type = ""
                    if signature:
                        param_pattern = rf'{param_name}\s+-\s+(.*?)(?:,|\))'
                        param_match = re.search(param_pattern, signature)
                        if param_match:
                            param_type = param_match.group(1).strip()
                    
                    parameters.append({
                        "name": param_name,
                        "type": param_type,
                        "description": param_desc
                    })
                
                is_deprecated = bool(detail.select(".deprecatedLabel"))
                
                constructors.append({
                    "name": constructor_name,
                    "signature": signature,
                    "modifiers": modifiers,
                    "description": description,
                    "parameters": parameters,
                    "deprecated": is_deprecated
                })
    
    return constructors

def extract_enum_constants(soup, structure_info):
    """Extract enum constant information"""
    constants = []
    
    # Try different approaches based on structure
    if structure_info["format_version"] == "new":
        # Newer format with explicit enum constant sections
        enum_constants_section = soup.find("section", class_="constant-summary")
        if enum_constants_section:
            enum_rows = enum_constants_section.select("tbody tr")
            
            for row in enum_rows:
                const_cell = row.select_one("th.col-first code")
                if not const_cell:
                    continue
                    
                const_name = const_cell.get_text().strip()
                
                desc_cell = row.select_one("td.col-last div.block")
                desc = desc_cell.get_text().strip() if desc_cell else ""
                
                constants.append({
                    "name": const_name,
                    "description": clean_text(desc)
                })
    else:
        # Older format
        enum_constants_section = soup.find("table", class_="memberSummary")
        if enum_constants_section:
            caption = enum_constants_section.find("caption")
            if caption and "enum constants" in caption.get_text().lower():
                enum_rows = enum_constants_section.select("tr")
                
                for row in enum_rows:
                    const_cell = row.select_one("td.colFirst code")
                    if not const_cell:
                        continue
                        
                    const_name = const_cell.get_text().strip()
                    
                    desc_cell = row.select_one("td.colLast div.block")
                    desc = desc_cell.get_text().strip() if desc_cell else ""
                    
                    constants.append({
                        "name": const_name,
                        "description": clean_text(desc)
                    })
    
    # Fallback using enum detail section
    if not constants:
        enum_detail_section = soup.find("div", class_="details") or soup.find("section", class_="constant-details")
        if enum_detail_section:
            enum_anchors = enum_detail_section.find_all("a", {"name": re.compile(r'.*')})
            
            for anchor in enum_anchors:
                detail = anchor.find_parent("li") or anchor.find_parent("div", class_="detail") or anchor.find_parent("section", class_="detail")
                if not detail:
                    continue
                
                const_name_elem = detail.find("h4") or detail.find("h3")
                if not const_name_elem:
                    continue
                    
                const_name = const_name_elem.get_text().strip()
                
                desc_elem = detail.find("div", class_="block")
                desc = desc_elem.get_text().strip() if desc_elem else ""
                
                constants.append({
                    "name": const_name,
                    "description": clean_text(desc)
                })
    
    # Fallback to parsing raw enum declaration
    if not constants:
        enum_decl = soup.find("pre", class_="declaration")
        if enum_decl:
            enum_text = enum_decl.get_text()
            # Look for enum constant names in declaration
            const_matches = re.findall(r'\b([A-Z][A-Z0-9_]*)\b(?:\(.*?\))?,?', enum_text)
            for const_name in const_matches:
                if const_name not in ["enum", "class", "interface"]:
                    constants.append({
                        "name": const_name,
                        "description": ""
                    })
    
    return constants

def merge_method_info(method_summary, method_details):
    """Merge method summary and details information"""
    method_map = {m["name"]: m for m in method_summary}
    
    for detail in method_details:
        name = detail["name"]
        if name in method_map:
            # Update method_map with details info
            for key, value in detail.items():
                # Don't overwrite existing values unless the new one has more information
                if key not in method_map[name] or (method_map[name][key] == "" and value != ""):
                    method_map[name][key] = value
        else:
            # Add new method to map
            method_map[name] = detail
    
    return list(method_map.values())

def text_based_extraction(html, entity_name, entity_type):
    """Extract information based on text patterns when structure parsing fails"""
    # Convert HTML to plain text
    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.ignore_images = True
    h2t.ignore_tables = False
    text = h2t.handle(html)
    
    result = {
        "methods": [],
        "fields": [],
        "constructors": [],
        "enum_constants": [],
        "extraction_method": "text_based"
    }
    
    # Extract method sections
    method_sections = re.split(r'#+\s+Method Detail', text, flags=re.IGNORECASE)
    if len(method_sections) > 1:
        method_text = method_sections[1]
        # Split into individual methods
        method_blocks = re.split(r'###\s+', method_text)
        
        for block in method_blocks:
            if not block.strip():
                continue
                
            # Extract method name
            name_match = re.search(r'^(\w+)', block)
            if not name_match:
                continue
                
            name = name_match.group(1)
            
            # Try to extract signature
            signature = ""
            sig_match = re.search(r'```\s*(.+?)\s*```', block, re.DOTALL)
            if sig_match:
                signature = sig_match.group(1).strip()
            
            # Try to extract description
            description = ""
            desc_match = re.search(r'```.*?\n(.*?)(?:\n\*\*|\n\*\s|$)', block, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            
            # Try to extract parameters
            parameters = []
            param_matches = re.finditer(r'\*\*Parameters:\*\*\s+(\w+)\s+-\s+(.*?)(?=\n\*\*|\n\*\s|$)', block, re.DOTALL)
            for param_match in param_matches:
                param_name = param_match.group(1)
                param_desc = param_match.group(2).strip()
                parameters.append({
                    "name": param_name,
                    "type": "",
                    "description": param_desc
                })
            
            # Try to extract return info
            return_info = {"type": "", "description": ""}
            return_match = re.search(r'\*\*Returns:\*\*\s+(.*?)(?=\n\*\*|\n\*\s|$)', block, re.DOTALL)
            if return_match:
                return_info["description"] = return_match.group(1).strip()
            
            result["methods"].append({
                "name": name,
                "signature": signature,
                "description": description,
                "parameters": parameters,
                "return": return_info,
                "modifiers": [],
                "return_type": "",
                "deprecated": False
            })
    
    # Extract field sections similarly
    field_sections = re.split(r'#+\s+Field Detail', text, flags=re.IGNORECASE)
    if len(field_sections) > 1:
        field_text = field_sections[1]
        field_blocks = re.split(r'###\s+', field_text)
        
        for block in field_blocks:
            if not block.strip():
                continue
                
            # Extract field name
            name_match = re.search(r'^(\w+)', block)
            if not name_match:
                continue
                
            name = name_match.group(1)
            
            # Try to extract signature
            signature = ""
            sig_match = re.search(r'```\s*(.+?)\s*```', block, re.DOTALL)
            if sig_match:
                signature = sig_match.group(1).strip()
            
            # Try to extract description
            description = ""
            desc_match = re.search(r'```.*?\n(.*?)(?:\n\*\*|\n\*\s|$)', block, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            
            result["fields"].append({
                "name": name,
                "signature": signature,
                "description": description,
                "type": "",
                "modifiers": [],
                "deprecated": False
            })
    
    # For enums, extract constants
    if entity_type == "enum":
        enum_matches = re.finditer(r'###\s+(\w+)\s+(.*?)(?=\n###|\Z)', text, re.DOTALL)
        for enum_match in enum_matches:
            const_name = enum_match.group(1)
            const_desc = enum_match.group(2).strip()
            
            result["enum_constants"].append({
                "name": const_name,
                "description": const_desc
            })
    
    return result

def extract_entity_content(url, entity_type, entity_name, package):
    """Extract detailed content for a specific entity (class, enum, interface, etc.)"""
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching URL: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Identify page structure
            structure_info = identify_page_structure(soup)
            logger.info(f"Identified structure: {structure_info}")
            
            # Get the main description
            main_desc_elem = soup.select_one(".description .block") or soup.select_one("section.description .block") or soup.select_one("div.block")
            description = clean_text(main_desc_elem.get_text()) if main_desc_elem else ""
            
            # Check if page title contains the entity name
            title_elem = soup.select_one("h1.title") or soup.select_one("h2.title")
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Get the full class name including package
            full_name = package + "." + entity_name if package else entity_name
            
            # Initialize the content structure
            content = {
                "name": entity_name,
                "full_name": full_name,
                "full_url": url,
                "type": entity_type,
                "package": package,
                "description": description,
                "page_structure": structure_info
            }
            
            # Extract inheritance information
            inheritance_elem = soup.select_one(".inheritance")
            if inheritance_elem:
                content["inheritance"] = [a.get_text().strip() for a in inheritance_elem.select("a")]
            else:
                content["inheritance"] = []
            
            # Extract interfaces implemented
            impl_elem = soup.select_one(".implements")
            if impl_elem:
                content["interfaces_implemented"] = [a.get_text().strip() for a in impl_elem.select("a")]
            else:
                content["interfaces_implemented"] = []
            
            # Extract nested classes
            content["nested_classes"] = extract_nested_classes(soup, structure_info)
            
            # Extract method information
            method_summary = extract_method_summary(soup, structure_info)
            method_details = extract_method_details(soup, structure_info)
            content["methods"] = merge_method_info(method_summary, method_details)
            
            # Extract field information
            content["fields"] = extract_field_details(soup, structure_info)
            
            # Extract constructor information for classes
            if entity_type in ["class"]:
                content["constructors"] = extract_constructor_details(soup, structure_info)
            else:
                content["constructors"] = []
            
            # Extract enum constants for enums
            if entity_type == "enum":
                content["enum_constants"] = extract_enum_constants(soup, structure_info)
            
            # Validate that we extracted the expected content
            extraction_success = (
                (entity_type in ["class", "interface"] and (content["methods"] or content["fields"] or content["constructors"])) or
                (entity_type == "enum" and content["enum_constants"]) or
                (entity_type == "annotation")
            )
            
            if not extraction_success:
                logger.warning(f"Primary extraction may have failed for {entity_name}. Trying text-based approach.")
                
                # Try text-based extraction as a fallback
                text_results = text_based_extraction(response.text, entity_name, entity_type)
                
                # Merge results
                if text_results["methods"]:
                    content["methods"] = merge_method_info(content["methods"], text_results["methods"])
                if text_results["fields"]:
                    content["fields"] = content["fields"] + text_results["fields"]
                if entity_type == "enum" and text_results["enum_constants"]:
                    content["enum_constants"] = content["enum_constants"] + text_results["enum_constants"]
                
                content["extraction_fallback_used"] = True
                
                # Save the raw HTML for later inspection
                html_file = os.path.join(OUTPUT_DIR, f"{full_name.replace('.', '_')}.html")
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"Saved raw HTML to {html_file} for inspection")
            
            return content
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{MAX_RETRIES} failed for {url}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                delay = random.uniform(2, 5)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to extract content from {url} after {MAX_RETRIES} attempts")
                return {
                    "name": entity_name,
                    "full_name": package + "." + entity_name if package else entity_name,
                    "full_url": url,
                    "type": entity_type,
                    "package": package,
                    "description": "Error: Failed to extract content",
                    "extraction_error": str(e)
                }

def process_entity(entity_data):
    """Process a single entity and save its content to a file"""
    entity_type = entity_data.get("type", "unknown")
    entity_name = entity_data.get("name", "unknown")
    url = entity_data.get("url", "")
    package = entity_data.get("package", "")
    
    if not url:
        logger.warning(f"No URL provided for {entity_name}")
        return False
    
    # Generate a filename based on full class name
    full_name = package + "." + entity_name if package else entity_name
    safe_name = full_name.replace(".", "_")
    output_file = os.path.join(OUTPUT_DIR, f"{safe_name}.json")
    
    # Skip if already processed
    if os.path.exists(output_file):
        logger.info(f"Skipping already processed entity: {full_name}")
        return True
    
    logger.info(f"Processing {entity_type}: {full_name}")
    
    # Extract content
    content = extract_entity_content(url, entity_type, entity_name, package)
    
    # Save to file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)
        logger.info(f"Successfully saved {full_name} to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save {full_name}: {str(e)}")
        return False
    
    # Add delay to avoid rate limiting
    time.sleep(random.uniform(*REQUEST_DELAY))
    
    return True

def flatten_entities(structured_data):
    """Convert the structured entity data into a flat list for processing"""
    all_entities = []
    
    for package, package_data in structured_data.items():
        # Process each category of entities
        for category in ["classes", "enums", "interfaces", "annotations", "others"]:
            for entity in package_data.get(category, []):
                # Determine the entity type based on category or entity data
                if category == "classes":
                    entity_type = "class"
                elif category == "enums":
                    entity_type = "enum"
                elif category == "interfaces":
                    entity_type = "interface"
                elif category == "annotations":
                    entity_type = "annotation"
                else:
                    # For "others", use the type field if available
                    entity_type = entity.get("type", "unknown")
                
                # Create a new entity record with type and package information
                entity_record = {
                    "name": entity.get("name", ""),
                    "url": entity.get("url", ""),
                    "type": entity_type,
                    "package": package
                }
                
                all_entities.append(entity_record)
    
    return all_entities

def create_index_file(output_dir):
    """Create an index file that lists all extracted entities"""
    try:
        index = []
        for file_path in Path(output_dir).glob("*.json"):
            if file_path.name == "extraction_progress.json" or file_path.name == "index.json":
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                index_entry = {
                    "name": data.get("name", ""),
                    "full_name": data.get("full_name", ""),
                    "type": data.get("type", ""),
                    "package": data.get("package", ""),
                    "file": file_path.name,
                    "method_count": len(data.get("methods", [])),
                    "field_count": len(data.get("fields", [])),
                    "constructor_count": len(data.get("constructors", [])),
                    "enum_constant_count": len(data.get("enum_constants", [])) if "enum_constants" in data else 0,
                    "fallback_used": data.get("extraction_fallback_used", False),
                    "has_error": "extraction_error" in data
                }
                
                index.append(index_entry)
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
        
        # Sort index by full name
        index.sort(key=lambda x: x.get("full_name", ""))
        
        # Write index file
        index_file = os.path.join(output_dir, "index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
            
        logger.info(f"Created index file with {len(index)} entries")
    
    except Exception as e:
        logger.error(f"Error creating index file: {str(e)}")

def test_sample_extraction():
    """Test extraction on sample pages to ensure coverage before full run"""
    sample_pages = [
        {"type": "class", "name": "ClientSettings", "url": "https://dreambot.org/javadocs/org/dreambot/api/ClientSettings.html", "package": "org.dreambot.api"},
        {"type": "enum", "name": "ClientSettings.SettingsTab", "url": "https://dreambot.org/javadocs/org/dreambot/api/ClientSettings.SettingsTab.html", "package": "org.dreambot.api"},
        {"type": "class", "name": "Client", "url": "https://dreambot.org/javadocs/org/dreambot/api/Client.html", "package": "org.dreambot.api"},
        {"type": "interface", "name": "Filter", "url": "https://dreambot.org/javadocs/org/dreambot/api/methods/filter/Filter.html", "package": "org.dreambot.api.methods.filter"}
    ]
    
    logger.info("Running sample extraction tests...")
    samples_dir = os.path.join(OUTPUT_DIR, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    
    overall_success = True
    
    for page in sample_pages:
        try:
            logger.info(f"Testing extraction for {page['type']}: {page['name']}")
            content = extract_entity_content(page["url"], page["type"], page["name"], page["package"])
            
            # Log extraction statistics
            method_count = len(content.get("methods", []))
            field_count = len(content.get("fields", []))
            constructor_count = len(content.get("constructors", []))
            enum_count = len(content.get("enum_constants", [])) if "enum_constants" in content else 0
            
            logger.info(f"  - Methods: {method_count}")
            logger.info(f"  - Fields: {field_count}")
            logger.info(f"  - Constructors: {constructor_count}")
            if page["type"] == "enum":
                logger.info(f"  - Enum Constants: {enum_count}")
            
            # Validate against expected content
            success = True
            if page["type"] == "class" and method_count == 0 and field_count == 0 and constructor_count == 0:
                logger.error(f"❌ Failed: No content extracted for {page['name']}")
                success = False
                overall_success = False
            elif page["type"] == "enum" and enum_count == 0:
                logger.error(f"❌ Failed: No enum constants extracted for {page['name']}")
                success = False
                overall_success = False
            else:
                logger.info(f"✅ Success: Content extracted for {page['name']}")
            
            # Save the test results
            sample_file = os.path.join(samples_dir, f"{page['name'].replace('.', '_')}_test.json")
            with open(sample_file, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error testing {page['name']}: {str(e)}")
            overall_success = False
    
    logger.info("Sample extraction tests completed.")
    return overall_success

def main():
    try:
        # First run tests on sample pages
        logger.info("Running preliminary extraction tests...")
        test_success = test_sample_extraction()
        
        if not test_success:
            logger.warning("Sample extraction tests failed. Review logs before proceeding with full extraction.")
            proceed = input("Continue with full extraction anyway? (y/n): ")
            if proceed.lower() != 'y':
                logger.info("Extraction aborted by user.")
                return
        
        # Load entity data
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            structured_data = json.load(f)
        
        # Convert structured data to flat list
        all_entities = flatten_entities(structured_data)
        
        logger.info(f"Found {len(all_entities)} entities to process")
        
        # Create a progress tracking file
        progress_file = os.path.join(OUTPUT_DIR, "extraction_progress.json")
        progress_data = {
            "total_entities": len(all_entities),
            "processed_entities": 0,
            "successful_entities": 0,
            "failed_entities": 0,
            "start_time": time.time(),
            "last_update_time": time.time()
        }
        
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, indent=2)
        
        # Process entities in parallel
        successful_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_entity = {executor.submit(process_entity, entity): entity for entity in all_entities}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_entity)):
                entity = future_to_entity[future]
                try:
                    result = future.result()
                    if result:
                        successful_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error processing {entity.get('name')}: {str(e)}")
                    failed_count += 1
                
                # Update progress regularly
                if (i + 1) % 10 == 0 or (i + 1) == len(all_entities):
                    progress_data = {
                        "total_entities": len(all_entities),
                        "processed_entities": i + 1,
                        "successful_entities": successful_count,
                        "failed_entities": failed_count,
                        "start_time": progress_data["start_time"],
                        "last_update_time": time.time()
                    }
                    
                    with open(progress_file, "w", encoding="utf-8") as f:
                        json.dump(progress_data, f, indent=2)
                    
                    elapsed_time = time.time() - progress_data["start_time"]
                    completion_percentage = ((i + 1) / len(all_entities)) * 100
                    logger.info(f"Progress: {i+1}/{len(all_entities)} ({completion_percentage:.2f}%) - Elapsed time: {elapsed_time:.2f}s")
        
        # Final statistics
        logger.info(f"Extraction complete!")
        logger.info(f"Successfully processed: {successful_count}/{len(all_entities)}")
        logger.info(f"Failed to process: {failed_count}/{len(all_entities)}")
        
        # Create a summary index file
        create_index_file(OUTPUT_DIR)
        
    except Exception as e:
        logger.error(f"An error occurred in the main process: {str(e)}")

if __name__ == "__main__":
    main()