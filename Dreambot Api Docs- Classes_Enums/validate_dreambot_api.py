import pandas as pd
import json
import os
from bs4 import BeautifulSoup
import logging
import re
import subprocess
from datetime import datetime

# Setup logging
log_file = f"fix_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONTENT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\extracted_content"
VALIDATION_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\validation_results"

# Load files needing attention
attention_df = pd.read_csv(os.path.join(VALIDATION_DIR, 'files_needing_attention.csv'))
html_df = pd.read_csv(os.path.join(VALIDATION_DIR, 'html_analysis.csv'))

# Analyze issues
def analyze_issues():
    """Analyze common issues in the files needing attention"""
    issue_patterns = {}
    missing_elements = attention_df['Missing Elements'].dropna()
    
    for items in missing_elements:
        for item in items.split(', '):
            if item in issue_patterns:
                issue_patterns[item] += 1
            else:
                issue_patterns[item] = 1
    
    logger.info("Common issues analysis:")
    for issue, count in sorted(issue_patterns.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {issue}: {count} occurrences")
    
    return issue_patterns

def extract_description_from_html(html_content):
    """Extract description from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try different selectors for description
    for selector in ['.description .block', 'div.block', 'p.lead']:
        desc_elem = soup.select_one(selector)
        if desc_elem and desc_elem.get_text().strip():
            return desc_elem.get_text().strip()
    
    return ""

def extract_methods_from_html(html_content, entity_type):
    """Extract methods from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    methods = []
    
    # Try to determine format version
    is_new_format = bool(soup.select_one('section.method-details'))
    
    if is_new_format:
        # Extract from newer format
        method_sections = soup.select('section.method-details .detail')
        for section in method_sections:
            method_name_elem = section.select_one('h3, h4')
            if not method_name_elem:
                continue
                
            method_name = method_name_elem.get_text().strip()
            
            signature_elem = section.select_one('.member-signature')
            signature = signature_elem.get_text().strip() if signature_elem else ""
            
            desc_elem = section.select_one('div.block')
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            # Basic method info
            methods.append({
                "name": method_name,
                "signature": signature,
                "description": description,
                "parameters": [],
                "return": {"type": "", "description": ""},
                "deprecated": bool(section.select('.deprecated'))
            })
    else:
        # Extract from older format
        method_sections = soup.select('div.details li, div.method-details li')
        for section in method_sections:
            method_name_elem = section.select_one('h4, h3')
            if not method_name_elem:
                continue
                
            method_name = method_name_elem.get_text().strip()
            
            signature_elem = section.select_one('pre')
            signature = signature_elem.get_text().strip() if signature_elem else ""
            
            desc_elem = section.select_one('div.block')
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            methods.append({
                "name": method_name,
                "signature": signature,
                "description": description,
                "parameters": [],
                "return": {"type": "", "description": ""},
                "deprecated": bool(section.select('.deprecatedLabel'))
            })
    
    # If still no methods found, try more general approach
    if not methods:
        # Look for method names in summary table
        method_rows = soup.select('table.memberSummary tr')
        for row in method_rows:
            name_cell = row.select_one('td.colFirst code')
            if not name_cell:
                continue
                
            method_text = name_cell.get_text().strip()
            # Check if it's a method (contains parentheses)
            if '(' in method_text:
                method_name = method_text.split('(')[0].strip()
                
                desc_cell = row.select_one('td.colLast div.block')
                description = desc_cell.get_text().strip() if desc_cell else ""
                
                methods.append({
                    "name": method_name,
                    "signature": method_text,
                    "description": description,
                    "parameters": [],
                    "return": {"type": "", "description": ""},
                    "deprecated": False
                })
    
    return methods

def extract_enum_constants_from_html(html_content):
    """Extract enum constants from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    constants = []
    
    # Try different selectors for enum constants
    constant_sections = soup.select('section.constant-summary tbody tr, table.memberSummary tr')
    
    for section in constant_sections:
        # For newer format
        name_elem = section.select_one('th.col-first code, td.colFirst code')
        if not name_elem:
            continue
            
        name = name_elem.get_text().strip()
        
        desc_elem = section.select_one('td.col-last div.block, td.colLast div.block')
        description = desc_elem.get_text().strip() if desc_elem else ""
        
        constants.append({
            "name": name,
            "description": description
        })
    
    return constants

def fix_json_file(file_path, issues_list):
    """Fix common issues in a JSON file using its HTML counterpart if available"""
    try:
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check for corresponding HTML file
        html_path = file_path.replace('.json', '.html')
        html_content = None
        
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
        
        modified = False
        
        # Fix missing description
        if 'Missing description' in issues_list:
            if html_content:
                description = extract_description_from_html(html_content)
                if description:
                    data['description'] = description
                    modified = True
            
            # If still no description, set a basic description
            if not data.get('description'):
                data['description'] = f"{data.get('type', 'Class')} in the {data.get('package', '')} package."
                modified = True
        
        # Fix missing methods
        if any('methods' in issue for issue in issues_list) and data.get('type') in ['class', 'interface']:
            if html_content:
                methods = extract_methods_from_html(html_content, data.get('type'))
                if methods:
                    data['methods'] = methods
                    modified = True
        
        # Fix missing enum constants
        if any('enum_constants' in issue for issue in issues_list) and data.get('type') == 'enum':
            if html_content:
                constants = extract_enum_constants_from_html(html_content)
                if constants:
                    data['enum_constants'] = constants
                    modified = True
        
        # If modifications were made, save the file
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error fixing {file_path}: {str(e)}")
        return False

def extract_from_html(html_file):
    """Extract content from an HTML file into JSON structure"""
    try:
        # Read HTML file
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Determine basic info
        title_elem = soup.select_one('h1.title, h2.title, title')
        title_text = title_elem.get_text().strip() if title_elem else ""
        
        # Determine entity type
        entity_type = "class"  # Default
        if "Interface" in title_text:
            entity_type = "interface"
        elif "Enum" in title_text:
            entity_type = "enum"
        elif "Annotation" in title_text:
            entity_type = "annotation"
        
        # Extract package and name
        package = ""
        name = ""
        
        # Try to extract from title
        full_name_match = re.search(r'(?:Class|Interface|Enum|Annotation)\s+([\w\.]+)', title_text)
        if full_name_match:
            full_name = full_name_match.group(1)
            parts = full_name.rsplit('.', 1)
            if len(parts) > 1:
                package = parts[0]
                name = parts[1]
            else:
                name = full_name
        
        # If not found, try other approaches
        if not name:
            # Try from filename
            file_basename = os.path.basename(html_file).replace('.html', '')
            parts = file_basename.split('_')
            if len(parts) > 1:
                name = parts[-1]
                package = '_'.join(parts[:-1]).replace('_', '.')
        
        # Create basic structure
        content = {
            "name": name,
            "full_name": f"{package}.{name}" if package else name,
            "full_url": "",
            "type": entity_type,
            "package": package,
            "description": extract_description_from_html(html_content),
            "methods": extract_methods_from_html(html_content, entity_type),
            "fields": [],  # Would need additional extraction
            "constructors": [],  # Would need additional extraction
            "extraction_source": "html_file"
        }
        
        # Add enum constants if it's an enum
        if entity_type == "enum":
            content["enum_constants"] = extract_enum_constants_from_html(html_content)
        
        return content
        
    except Exception as e:
        logger.error(f"Error extracting from {html_file}: {str(e)}")
        raise

def process_priority_files(limit=100):
    """Process the most critical files first"""
    sorted_df = attention_df.sort_values('Completeness')
    count = 0
    fixed = 0
    
    for _, row in sorted_df.iterrows():
        if count >= limit:
            break
            
        file_name = row['File']
        file_path = os.path.join(CONTENT_DIR, file_name)
        
        if os.path.exists(file_path):
            logger.info(f"Fixing {file_name} (Completeness: {row['Completeness']:.2f})")
            issues = row['Missing Elements'].split(', ') if isinstance(row['Missing Elements'], str) else []
            
            if fix_json_file(file_path, issues):
                fixed += 1
                logger.info(f"Successfully fixed {file_name}")
            else:
                logger.warning(f"Could not fix issues in {file_name}")
        
        count += 1
    
    logger.info(f"Processed {count} files, fixed {fixed} files")
    return fixed

def process_html_files_without_json():
    """Process HTML files that need extraction"""
    extraction_needed = html_df[(html_df['Has JSON Equivalent'] == 'False') & 
                              (html_df['Recommended Action'] == 'extract_content')]
    
    logger.info(f"Found {len(extraction_needed)} HTML files to extract content from")
    
    successful = 0
    failed = 0
    
    for _, row in extraction_needed.iterrows():
        html_file = os.path.join(CONTENT_DIR, row['File'])
        
        if not os.path.exists(html_file):
            logger.warning(f"File not found: {html_file}")
            continue
        
        try:
            content = extract_from_html(html_file)
            
            json_file = html_file.replace(".html", ".json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
                
            logger.info(f"Successfully extracted content from {row['File']}")
            successful += 1
            
        except Exception as e:
            logger.error(f"Error extracting from {html_file}: {str(e)}")
            failed += 1
    
    logger.info(f"Extraction completed. Success: {successful}, Failed: {failed}")
    return successful, failed

def main():
    logger.info("Starting extraction improvement process")
    
    # Analyze common issues
    issues = analyze_issues()
    
    # Process priority files
    logger.info("Processing files needing attention...")
    fixed_count = process_priority_files(limit=100)
    
    # Process HTML files without JSON
    logger.info("Processing HTML files without JSON equivalents...")
    html_success, html_failed = process_html_files_without_json()
    
    # Print summary
    logger.info("\nSummary:")
    logger.info(f"Fixed {fixed_count} existing JSON files")
    logger.info(f"Created {html_success} new JSON files from HTML (failed: {html_failed})")
    
    logger.info("\nNext steps:")
    logger.info("1. Run validation again to check improvement")
    logger.info("2. Continue fixing remaining issues")
    logger.info("3. Proceed to data integration and mapping creation")

if __name__ == "__main__":
    main()