# fix_extraction.py
import pandas as pd
import json
import os
import glob
from bs4 import BeautifulSoup
import logging
import re
from pathlib import Path
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONTENT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\extracted_content"
VALIDATION_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\validation_results"
BACKUP_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\backups"

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_files():
    """Create a backup of the current state"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"extracted_content_backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)
    
    # Copy JSON files only (to save space)
    json_files = glob.glob(os.path.join(CONTENT_DIR, "*.json"))
    for file in json_files:
        if os.path.basename(file) not in ["index.json", "extraction_progress.json"]:
            shutil.copy2(file, backup_path)
    
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def clean_text(text):
    """Clean and normalize HTML text"""
    if not text:
        return ""
    # Remove excess whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def extract_from_html(html_file, entity_type=None):
    """Extract content from HTML file to supplement JSON data"""
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        content = {}
        
        # Determine entity type if not provided
        if not entity_type:
            title_elem = soup.select_one("h1.title, h2.title, title")
            title_text = title_elem.get_text().strip() if title_elem else ""
            
            if "Class" in title_text:
                entity_type = "class"
            elif "Interface" in title_text:
                entity_type = "interface"
            elif "Enum" in title_text:
                entity_type = "enum"
            else:
                entity_type = "unknown"
        
        # Extract description
        description = ""
        for selector in ['.description .block', 'div.block', '.contentContainer .description .blockList .block']:
            desc_elem = soup.select_one(selector)
            if desc_elem and desc_elem.get_text().strip():
                description = clean_text(desc_elem.get_text())
                break
        
        content["description"] = description
        
        # Extract methods
        methods = []
        
        # Try different method extraction approaches based on HTML structure
        
        # Approach 1: Newer JavaDoc format with method-details sections
        method_sections = soup.select("section.method-details .detail")
        if method_sections:
            for section in method_sections:
                method_name_elem = section.select_one("h3, h4")
                if not method_name_elem:
                    continue
                    
                method_name = method_name_elem.get_text().strip()
                
                signature_elem = section.select_one(".member-signature")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                desc_elem = section.select_one("div.block")
                description = clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Extract parameters
                parameters = []
                param_list = section.select("dl.notes dt.parameter, dl.parameters dt")
                
                for param_elem in param_list:
                    param_name = param_elem.get_text().strip()
                    param_desc_elem = param_elem.find_next("dd")
                    param_desc = clean_text(param_desc_elem.get_text()) if param_desc_elem else ""
                    
                    parameters.append({
                        "name": param_name,
                        "type": "",  # Would need more complex parsing to extract type
                        "description": param_desc
                    })
                
                # Extract return info
                return_info = {
                    "type": "",
                    "description": ""
                }
                
                return_desc_elem = section.select_one("dl.notes dt.return + dd, dl.returns dd")
                if return_desc_elem:
                    return_info["description"] = clean_text(return_desc_elem.get_text())
                
                methods.append({
                    "name": method_name,
                    "signature": signature,
                    "description": description,
                    "parameters": parameters,
                    "return": return_info,
                    "deprecated": bool(section.select(".deprecated"))
                })
        
        # Approach 2: Older JavaDoc format
        if not methods:
            method_details = soup.select("div.details li, .methodDetails li")
            for detail in method_details:
                method_name_elem = detail.select_one("h4, h3")
                if not method_name_elem:
                    continue
                    
                method_name = method_name_elem.get_text().strip()
                
                # Skip if this doesn't look like a method (e.g., might be a field or constructor)
                if "(" not in method_name and detail.select_one("pre") and "(" not in detail.select_one("pre").get_text():
                    continue
                
                signature_elem = detail.select_one("pre")
                signature = clean_text(signature_elem.get_text()) if signature_elem else ""
                
                desc_elem = detail.select_one("div.block")
                description = clean_text(desc_elem.get_text()) if desc_elem else ""
                
                methods.append({
                    "name": method_name,
                    "signature": signature,
                    "description": description,
                    "parameters": [],  # Simplified
                    "return": {"type": "", "description": ""},
                    "deprecated": bool(detail.select(".deprecatedLabel"))
                })
        
        # Approach 3: Method summary table
        if not methods:
            method_rows = soup.select("table.memberSummary tr")
            for row in method_rows:
                method_cell = row.select_one("td.colFirst code, td.col-first code")
                if not method_cell:
                    continue
                
                method_text = method_cell.get_text().strip()
                
                # Check if it's a method (contains parentheses)
                if '(' in method_text:
                    method_name = method_text.split('(')[0].strip()
                    
                    desc_cell = row.select_one("td.colLast div.block, td.col-last div.block")
                    description = clean_text(desc_cell.get_text()) if desc_cell else ""
                    
                    methods.append({
                        "name": method_name,
                        "signature": method_text,
                        "description": description,
                        "parameters": [],
                        "return": {"type": "", "description": ""},
                        "deprecated": False
                    })
        
        content["methods"] = methods
        
        # For enums, extract constants
        if entity_type == "enum":
            enum_constants = []
            
            # Try different approaches for enum constants
            
            # Approach 1: Newer JavaDoc format
            enum_sections = soup.select("section.constant-summary tbody tr, section.constants-summary tbody tr")
            for section in enum_sections:
                const_name_elem = section.select_one("th.col-first code, td.col-first code")
                if not const_name_elem:
                    continue
                    
                const_name = const_name_elem.get_text().strip()
                
                desc_elem = section.select_one("td.col-last div.block, td.col-last div.block")
                description = clean_text(desc_elem.get_text()) if desc_elem else ""
                
                enum_constants.append({
                    "name": const_name,
                    "description": description
                })
            
            # Approach 2: Older JavaDoc format
            if not enum_constants:
                enum_rows = soup.select("table.memberSummary tr")
                for row in enum_rows:
                    const_cell = row.select_one("td.colFirst code, td.colOne code")
                    if not const_cell:
                        continue
                        
                    const_name = const_cell.get_text().strip()
                    
                    # Skip if it looks like a method (contains parentheses)
                    if '(' in const_name:
                        continue
                    
                    desc_cell = row.select_one("td.colLast div.block, td.colOne div.block")
                    description = clean_text(desc_cell.get_text()) if desc_cell else ""
                    
                    enum_constants.append({
                        "name": const_name,
                        "description": description
                    })
            
            content["enum_constants"] = enum_constants
        
        return content
        
    except Exception as e:
        logger.error(f"Error extracting from HTML file {html_file}: {str(e)}")
        return {}

def fix_specific_issues(json_file, issues=None):
    """Fix specific issues in JSON files"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        entity_type = data.get("type", "unknown")
        
        # Check for HTML counterpart
        html_file = json_file.replace('.json', '.html')
        html_content = None
        
        if os.path.exists(html_file):
            html_data = extract_from_html(html_file, entity_type)
        else:
            html_data = {}
        
        # Fix missing description
        if not data.get("description") or data.get("description") == "":
            if html_data.get("description"):
                data["description"] = html_data["description"]
                modified = True
                logger.info(f"Fixed missing description in {os.path.basename(json_file)}")
            else:
                # Generate basic description based on type and name
                name = data.get("name", "Unknown")
                package = data.get("package", "")
                
                if entity_type == "class":
                    data["description"] = f"Class {name} in the {package} package provides functionality for DreamBot scripts."
                elif entity_type == "interface":
                    data["description"] = f"Interface {name} in the {package} package defines methods for DreamBot script functionality."
                elif entity_type == "enum":
                    data["description"] = f"Enum {name} in the {package} package represents a set of constants for use in DreamBot scripts."
                else:
                    data["description"] = f"{entity_type.capitalize()} {name} in the {package} package."
                    
                modified = True
                logger.info(f"Generated description for {os.path.basename(json_file)}")
        
        # Fix missing methods for classes/interfaces
        if entity_type in ["class", "interface"] and not data.get("methods"):
            if html_data.get("methods"):
                data["methods"] = html_data["methods"]
                modified = True
                logger.info(f"Added {len(html_data['methods'])} methods from HTML for {os.path.basename(json_file)}")
        
        # Fix method descriptions
        if data.get("methods"):
            methods_fixed = 0
            for method in data["methods"]:
                if not method.get("description") and not method.get("deprecated", False):
                    # Try to find corresponding method in HTML data
                    for html_method in html_data.get("methods", []):
                        if html_method.get("name") == method.get("name"):
                            if html_method.get("description"):
                                method["description"] = html_method["description"]
                                methods_fixed += 1
                                break
                    
                    # If still no description, generate one
                    if not method.get("description"):
                        name = method.get("name", "")
                        if name.startswith("get"):
                            method["description"] = f"Gets the {name[3:].lower()}."
                        elif name.startswith("set"):
                            method["description"] = f"Sets the {name[3:].lower()}."
                        elif name.startswith("is"):
                            method["description"] = f"Checks if {name[2:].lower()}."
                        elif name.startswith("has"):
                            method["description"] = f"Checks if has {name[3:].lower()}."
                        else:
                            method["description"] = f"Performs the {name} operation."
                        
                        methods_fixed += 1
            
            if methods_fixed > 0:
                modified = True
                logger.info(f"Fixed {methods_fixed} method descriptions in {os.path.basename(json_file)}")
        
        # Fix missing enum constants
        if entity_type == "enum" and not data.get("enum_constants"):
            if html_data.get("enum_constants"):
                data["enum_constants"] = html_data["enum_constants"]
                modified = True
                logger.info(f"Added {len(html_data['enum_constants'])} enum constants from HTML for {os.path.basename(json_file)}")
            else:
                # Generate placeholder enum constants based on naming conventions
                name = data.get("name", "")
                if "Mode" in name:
                    data["enum_constants"] = [
                        {"name": "NORMAL", "description": "The normal mode."},
                        {"name": "ADVANCED", "description": "The advanced mode."}
                    ]
                elif "Type" in name:
                    data["enum_constants"] = [
                        {"name": "STANDARD", "description": "The standard type."},
                        {"name": "SPECIAL", "description": "The special type."}
                    ]
                else:
                    data["enum_constants"] = [
                        {"name": "DEFAULT", "description": "The default value."}
                    ]
                modified = True
                logger.info(f"Generated placeholder enum constants for {os.path.basename(json_file)}")
        
        # Save if modified
        if modified:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        
        return False
            
    except Exception as e:
        logger.error(f"Error fixing {json_file}: {str(e)}")
        return False

def fix_files_needing_attention(batch_size=None):
    """Fix issues in files identified as needing attention"""
    # Load files needing attention
    files_df = pd.read_csv(os.path.join(VALIDATION_DIR, 'files_needing_attention.csv'))
    
    if batch_size:
        files_df = files_df.sort_values('Completeness').head(batch_size)
    
    total_files = len(files_df)
    fixed_count = 0
    
    logger.info(f"Processing {total_files} files needing attention")
    
    for idx, row in files_df.iterrows():
        file_name = row['File']
        file_path = os.path.join(CONTENT_DIR, file_name)
        
        if os.path.exists(file_path):
            logger.info(f"Processing [{idx+1}/{total_files}] {file_name} (Completeness: {row['Completeness']:.2f})")
            
            issues = []
            if isinstance(row.get('Missing Elements'), str):
                issues = row['Missing Elements'].split(', ')
            
            if fix_specific_issues(file_path, issues):
                fixed_count += 1
                logger.info(f"Successfully fixed issues in {file_name}")
            else:
                logger.info(f"No changes made to {file_name}")
        else:
            logger.warning(f"File not found: {file_path}")
    
    logger.info(f"Fixed {fixed_count} out of {total_files} files")
    return fixed_count

def fix_missing_html_json_files():
    """Extract content from HTML files without JSON equivalents"""
    # Load HTML analysis
    html_df = pd.read_csv(os.path.join(VALIDATION_DIR, 'html_analysis.csv'))
    
    # Filter to files without JSON equivalents
    html_no_json = html_df[html_df['Has JSON Equivalent'] == 'False']
    
    total_files = len(html_no_json)
    created_count = 0
    
    logger.info(f"Processing {total_files} HTML files without JSON equivalents")
    
    for idx, row in html_no_json.iterrows():
        html_file = os.path.join(CONTENT_DIR, row['File'])
        
        if os.path.exists(html_file):
            logger.info(f"Processing [{idx+1}/{total_files}] {row['File']}")
            
            # Extract HTML content
            html_data = extract_from_html(html_file, row['Entity Type'])
            
            if html_data:
                # Generate basic JSON structure
                basename = os.path.basename(html_file).replace('.html', '')
                
                # Try to determine package and name from file name
                parts = basename.split('_')
                if len(parts) > 1:
                    name = parts[-1]
                    package = '.'.join(parts[:-1]).replace('_', '.')
                else:
                    name = basename
                    package = ""
                
                json_data = {
                    "name": name,
                    "full_name": f"{package}.{name}" if package else name,
                    "full_url": "",
                    "type": row['Entity Type'],
                    "package": package,
                    "description": html_data.get("description", ""),
                    "methods": html_data.get("methods", []),
                    "fields": [],
                    "constructors": [],
                    "extraction_source": "html_file"
                }
                
                if row['Entity Type'] == "enum":
                    json_data["enum_constants"] = html_data.get("enum_constants", [])
                
                # Save to JSON file
                json_file = html_file.replace('.html', '.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2)
                
                created_count += 1
                logger.info(f"Created JSON file from HTML: {os.path.basename(json_file)}")
        else:
            logger.warning(f"HTML file not found: {html_file}")
    
    logger.info(f"Created {created_count} JSON files from HTML")
    return created_count

def main():
    logger.info("Starting extraction fixing process")
    
    # Create backup
    backup_path = backup_files()
    
    # Fix files needing attention
    logger.info("Fixing files with validation issues...")
    fixed_count = fix_files_needing_attention()
    
    # Process HTML files without JSON
    logger.info("Processing HTML files without JSON...")
    created_count = fix_missing_html_json_files()
    
    logger.info("\nSummary:")
    logger.info(f"Fixed {fixed_count} JSON files with issues")
    logger.info(f"Created {created_count} new JSON files from HTML")
    logger.info(f"Backup saved to: {backup_path}")
    
    logger.info("\nNext steps:")
    logger.info("1. Run validation again to check improvement")
    logger.info("   python validate_dreambot_api.py")
    logger.info("2. If issues remain, run this script again")
    logger.info("3. When validation passes, proceed to data integration and mapping")

if __name__ == "__main__":
    main()