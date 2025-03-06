# validate_extraction.py
import pandas as pd
import json
import os
import glob
from bs4 import BeautifulSoup
import logging
import csv
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONTENT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\extracted_content"
VALIDATION_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\validation_results"

# Ensure validation directory exists
os.makedirs(VALIDATION_DIR, exist_ok=True)

def validate_json_file(json_file):
    """Validate the completeness of an extracted JSON file"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Initialize validation result
        result = {
            "file": os.path.basename(json_file),
            "name": data.get("name", "Unknown"),
            "full_name": data.get("full_name", "Unknown"),
            "type": data.get("type", "Unknown"),
            "issues": [],
            "missing_elements": []
        }
        
        # Check for expected content based on entity type
        entity_type = data.get("type", "unknown")
        
        # 1. All entities should have a description
        if not data.get("description") or data.get("description") == "":
            result["issues"].append("Missing description")
        
        # 2. Check class-specific elements
        if entity_type == "class" or entity_type == "interface":
            # Methods check (with exceptions for simple data classes)
            if len(data.get("methods", [])) == 0:
                # Check if this might be a simple data class (has fields but no methods)
                if len(data.get("fields", [])) == 0:
                    result["missing_elements"].append("methods and fields")
                else:
                    # Has fields but no methods - might be intentional for data classes
                    result["missing_elements"].append("methods (possible data class)")
            
            # Validate method completeness
            method_issues = []
            for method in data.get("methods", []):
                if not method.get("description") and not method.get("deprecated", False):
                    method_issues.append(f"Method {method.get('name', 'unknown')} missing description")
                
                # Check for parameter descriptions
                for param in method.get("parameters", []):
                    if not param.get("description"):
                        method_issues.append(f"Method {method.get('name', 'unknown')} parameter {param.get('name', 'unknown')} missing description")
            
            if method_issues:
                result["issues"].extend(method_issues)
        
        # 3. Check enum-specific elements
        if entity_type == "enum":
            if len(data.get("enum_constants", [])) == 0:
                result["missing_elements"].append("enum_constants")
        
        # 4. Check field elements
        field_issues = []
        for field in data.get("fields", []):
            if not field.get("description") and not field.get("deprecated", False):
                field_issues.append(f"Field {field.get('name', 'unknown')} missing description")
        
        if field_issues:
            result["issues"].extend(field_issues)
            
        # Calculate completeness score
        total_issues = len(result["issues"]) + len(result["missing_elements"])
        
        if total_issues == 0:
            result["status"] = "complete"
            result["completeness"] = 1.0
        else:
            result["status"] = "incomplete"
            # Simple heuristic: more than 5 issues = serious problem
            result["completeness"] = max(0, 1 - (total_issues / 10))
        
        return result
    
    except Exception as e:
        logger.error(f"Error validating {json_file}: {str(e)}")
        return {
            "file": os.path.basename(json_file),
            "status": "error",
            "error": str(e),
            "completeness": 0
        }

def analyze_html_file(html_file):
    """Analyze HTML file to determine what content should be extracted"""
    try:
        # Determine if this HTML is for a failed extraction
        json_equivalent = html_file.replace(".html", ".json")
        
        # Check if a corresponding JSON file exists
        has_json = os.path.exists(json_equivalent)
        
        # Initialize result
        result = {
            "file": os.path.basename(html_file),
            "has_json_equivalent": has_json,
            "recommended_action": "",
            "entity_type": "unknown"
        }
        
        # Read HTML content
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        # Get title to determine entity type
        title_elem = soup.select_one("h1.title, h2.title, title")
        if title_elem:
            title_text = title_elem.get_text().strip()
            if "Class" in title_text:
                result["entity_type"] = "class"
            elif "Interface" in title_text:
                result["entity_type"] = "interface"
            elif "Enum" in title_text:
                result["entity_type"] = "enum"
            elif "Annotation" in title_text:
                result["entity_type"] = "annotation"
        
        # Count methods
        method_count = 0
        method_sections = [
            soup.find("section", class_="method-summary"),
            soup.find("section", class_="method-details")
        ]
        
        for section in method_sections:
            if section:
                method_count += len(section.find_all(["h3", "h4", "tr"]))
        
        result["estimated_methods"] = method_count
        
        # Determine recommendation
        if has_json:
            if method_count > 0:
                result["recommended_action"] = "validate_against_json"
            else:
                result["recommended_action"] = "reference_only"
        else:
            if method_count > 0:
                result["recommended_action"] = "extract_content"
            else:
                result["recommended_action"] = "manual_review"
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing HTML file {html_file}: {str(e)}")
        return {
            "file": os.path.basename(html_file),
            "has_json_equivalent": False,
            "recommended_action": "error",
            "error": str(e)
        }

def validate_content_directory():
    """Validate all files in the content directory"""
    # Get all files
    json_files = glob.glob(os.path.join(CONTENT_DIR, "*.json"))
    html_files = glob.glob(os.path.join(CONTENT_DIR, "*.html"))
    
    logger.info(f"Found {len(json_files)} JSON files and {len(html_files)} HTML files")
    
    # Validate JSON files
    json_results = []
    for json_file in json_files:
        # Skip index or progress files
        if os.path.basename(json_file) in ["index.json", "extraction_progress.json", "validation_summary.json"]:
            continue
            
        logger.info(f"Validating JSON file: {os.path.basename(json_file)}")
        result = validate_json_file(json_file)
        json_results.append(result)
    
    # Analyze HTML files
    html_results = []
    for html_file in html_files:
        logger.info(f"Analyzing HTML file: {os.path.basename(html_file)}")
        result = analyze_html_file(html_file)
        html_results.append(result)
    
    # Calculate statistics for JSON files
    json_complete = sum(1 for r in json_results if r["status"] == "complete")
    json_incomplete = sum(1 for r in json_results if r["status"] == "incomplete")
    json_error = sum(1 for r in json_results if r["status"] == "error")
    avg_completeness = sum(r.get("completeness", 0) for r in json_results) / len(json_results) if json_results else 0
    
    # Calculate statistics for HTML files
    html_with_json = sum(1 for r in html_results if r["has_json_equivalent"])
    html_without_json = sum(1 for r in html_results if not r["has_json_equivalent"])
    html_to_extract = sum(1 for r in html_results if r["recommended_action"] == "extract_content")
    
    # Prepare summary report
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "json_files": {
            "total": len(json_results),
            "complete": json_complete,
            "incomplete": json_incomplete,
            "error": json_error,
            "average_completeness": avg_completeness,
            "completion_percentage": (json_complete / len(json_results) * 100) if json_results else 0
        },
        "html_files": {
            "total": len(html_results),
            "with_json_equivalent": html_with_json,
            "without_json_equivalent": html_without_json,
            "recommended_for_extraction": html_to_extract
        },
        "json_results": json_results,
        "html_results": html_results
    }
    
    # Create a list of JSON files requiring attention
    attention_needed = [r for r in json_results if r["status"] != "complete"]
    attention_needed.sort(key=lambda x: x.get("completeness", 0))
    
    # Save detailed validation results
    with open(os.path.join(VALIDATION_DIR, "validation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    # Save CSV summary of JSON files
    with open(os.path.join(VALIDATION_DIR, "json_validation.csv"), "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Name", "Type", "Status", "Completeness", "Issues Count", "Missing Elements"])
        for result in json_results:
            writer.writerow([
                result["file"],
                result.get("name", "Unknown"),
                result.get("type", "Unknown"),
                result.get("status", "Unknown"),
                result.get("completeness", 0),
                len(result.get("issues", [])),
                ", ".join(result.get("missing_elements", []))
            ])
    
    # Save CSV summary of HTML files
    with open(os.path.join(VALIDATION_DIR, "html_analysis.csv"), "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Has JSON Equivalent", "Entity Type", "Estimated Methods", "Recommended Action"])
        for result in html_results:
            writer.writerow([
                result["file"],
                result.get("has_json_equivalent", False),
                result.get("entity_type", "Unknown"),
                result.get("estimated_methods", 0),
                result.get("recommended_action", "Unknown")
            ])
    
    # Save files needing attention
    with open(os.path.join(VALIDATION_DIR, "files_needing_attention.csv"), "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Name", "Type", "Completeness", "Issues Count", "Missing Elements"])
        for result in attention_needed:
            writer.writerow([
                result["file"],
                result.get("name", "Unknown"),
                result.get("type", "Unknown"),
                result.get("completeness", 0),
                len(result.get("issues", [])),
                ", ".join(result.get("missing_elements", []))
            ])
    
    return summary

def print_summary(summary):
    """Print a human-readable summary of validation results"""
    json_stats = summary["json_files"]
    html_stats = summary["html_files"]
    
    print("\n" + "="*50)
    print("DREAMBOT API DOCUMENTATION VALIDATION SUMMARY")
    print("="*50)
    
    print("\nJSON FILES SUMMARY:")
    print(f"  Total JSON files: {json_stats['total']}")
    print(f"  Complete files: {json_stats['complete']} ({json_stats['completion_percentage']:.1f}%)")
    print(f"  Incomplete files: {json_stats['incomplete']}")
    print(f"  Error files: {json_stats['error']}")
    print(f"  Average completeness score: {json_stats['average_completeness']:.2f}")
    
    print("\nHTML FILES SUMMARY:")
    print(f"  Total HTML files: {html_stats['total']}")
    print(f"  Files with JSON equivalent: {html_stats['with_json_equivalent']}")
    print(f"  Files without JSON equivalent: {html_stats['without_json_equivalent']}")
    print(f"  Files recommended for extraction: {html_stats['recommended_for_extraction']}")
    
    print("\nRECOMMENDED NEXT STEPS:")
    
    if json_stats['incomplete'] > 0 or json_stats['error'] > 0:
        print(f"  1. Review and fix {json_stats['incomplete'] + json_stats['error']} incomplete/error JSON files")
        print(f"     (See files_needing_attention.csv for details)")
    
    if html_stats['recommended_for_extraction'] > 0:
        print(f"  2. Extract content from {html_stats['recommended_for_extraction']} HTML files lacking JSON equivalents")
        print(f"     (See html_analysis.csv for details)")
    
    if json_stats['incomplete'] == 0 and json_stats['error'] == 0 and html_stats['recommended_for_extraction'] == 0:
        print("  All files have been successfully processed!")
        print("  Proceed to data integration and mapping creation phase")
    
    print(f"\nDetailed results saved to: {VALIDATION_DIR}")
    print("="*50)

if __name__ == "__main__":
    logger.info("Starting validation process")
    summary = validate_content_directory()
    print_summary(summary)
    logger.info("Validation complete")