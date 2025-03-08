import os
import json
import shutil
import argparse
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("organize_psc_files.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("organize_psc_files")

def validate_json_file(file_path: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate that a file contains valid JSON and has minimal required structure.
    
    Args:
        file_path: Path to the JSON file to validate
        
    Returns:
        Tuple of (is_valid, json_content) where json_content is None if invalid
    """
    try:
        with open(file_path, 'r') as f:
            json_content = json.load(f)
        
        # Check minimal required structure
        if not isinstance(json_content, dict):
            logger.warning(f"File {file_path} is not a JSON object")
            return False, None
        
        if "actions" not in json_content or not isinstance(json_content["actions"], list):
            logger.warning(f"File {file_path} does not contain an 'actions' array")
            return False, None
        
        if not json_content["actions"]:
            logger.warning(f"File {file_path} has empty 'actions' array")
            return False, None
        
        return True, json_content
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {file_path}: {e}")
        return False, None
    except Exception as e:
        logger.warning(f"Error reading {file_path}: {e}")
        return False, None

def organize_psc_files(source_dir: str, target_dir: str, category_map_file: str) -> Dict[str, int]:
    """
    Organize PSC JSON files by categorizing them according to the category map.
    
    Args:
        source_dir: Directory containing raw PSC JSON files
        target_dir: Directory to store organized files
        category_map_file: Path to JSON file mapping action IDs to categories
        
    Returns:
        Dictionary with statistics of files processed by category
    """
    # Load category map
    try:
        with open(category_map_file, 'r') as f:
            category_map = json.load(f)
        logger.info(f"Loaded category map with {len(category_map)} action mappings")
    except Exception as e:
        logger.error(f"Error loading category map from {category_map_file}: {e}")
        sys.exit(1)
    
    # Extract unique categories
    categories = set(category_map.values())
    logger.info(f"Found {len(categories)} unique categories: {', '.join(categories)}")
    
    # Create category directories
    for category in categories:
        category_dir = os.path.join(target_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        logger.info(f"Created/verified directory: {category_dir}")
    
    # Create directory for uncategorized files
    uncategorized_dir = os.path.join(target_dir, "uncategorized")
    os.makedirs(uncategorized_dir, exist_ok=True)
    
    # Create directory for invalid files
    invalid_dir = os.path.join(target_dir, "invalid")
    os.makedirs(invalid_dir, exist_ok=True)
    
    # Track statistics
    stats = {
        "total_processed": 0,
        "valid_files": 0,
        "invalid_files": 0,
        "uncategorized_files": 0,
        "categories": {category: 0 for category in categories}
    }
    
    # Process each file in the source directory
    for filename in os.listdir(source_dir):
        if not filename.endswith('.json'):
            continue
        
        input_path = os.path.join(source_dir, filename)
        stats["total_processed"] += 1
        
        # Validate the JSON file
        is_valid, psc_json = validate_json_file(input_path)
        
        if not is_valid:
            # Copy invalid files to invalid directory
            stats["invalid_files"] += 1
            output_path = os.path.join(invalid_dir, filename)
            shutil.copy2(input_path, output_path)
            logger.warning(f"Invalid file {filename} copied to {invalid_dir}")
            continue
        
        # Try to determine category from the file content
        actions = psc_json.get("actions", [])
        root_action_id = actions[0].get("id") if actions else None
        
        if not root_action_id or root_action_id not in category_map:
            # Handle uncategorized files
            stats["uncategorized_files"] += 1
            output_path = os.path.join(uncategorized_dir, filename)
            shutil.copy2(input_path, output_path)
            logger.warning(f"Uncategorized file {filename} with root action {root_action_id} copied to {uncategorized_dir}")
            continue
        
        # File is valid and categorized
        stats["valid_files"] += 1
        category = category_map[root_action_id]
        stats["categories"][category] += 1
        
        # Copy the file to the appropriate category directory
        output_path = os.path.join(target_dir, category, filename)
        shutil.copy2(input_path, output_path)
        logger.info(f"Copied {filename} to {category} category")
    
    # Generate summary
    logger.info(f"Organization complete. Processed {stats['total_processed']} files:")
    logger.info(f"  - Valid files: {stats['valid_files']}")
    logger.info(f"  - Invalid files: {stats['invalid_files']}")
    logger.info(f"  - Uncategorized files: {stats['uncategorized_files']}")
    logger.info("Category distribution:")
    for category, count in stats["categories"].items():
        if count > 0:
            logger.info(f"  - {category}: {count} files")
    
    return stats

def main():
    """Main entry point for the PSC file organization tool."""
    parser = argparse.ArgumentParser(description='Organize PSC JSON files by category')
    parser.add_argument('--source-dir', required=True, help='Source directory containing raw PSC JSON files')
    parser.add_argument('--target-dir', required=True, help='Target directory for organized files')
    parser.add_argument('--category-map', required=True, help='JSON file mapping action IDs to categories')
    parser.add_argument('--generate-report', action='store_true', help='Generate a detailed report of the organization')
    
    args = parser.parse_args()
    
    # Get absolute path for category map if not absolute already
    if not os.path.isabs(args.category_map):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        category_map_path = os.path.join(parent_dir, "mapping", os.path.basename(args.category_map))
        if not os.path.isfile(category_map_path):
            # Try direct path relative to script directory
            category_map_path = os.path.join(parent_dir, args.category_map)
    else:
        category_map_path = args.category_map
    
    # Ensure source directory exists
    if not os.path.isdir(args.source_dir):
        logger.error(f"Source directory does not exist: {args.source_dir}")
        sys.exit(1)
    
    # Ensure category map file exists
    if not os.path.isfile(category_map_path):
        logger.error(f"Category map file does not exist: {category_map_path}")
        sys.exit(1)
    
    # Create target directory if it doesn't exist
    os.makedirs(args.target_dir, exist_ok=True)
    
    # Organize the files
    stats = organize_psc_files(args.source_dir, args.target_dir, category_map_path)
    
    # Generate report if requested
    if args.generate_report:
        report_path = os.path.join(args.target_dir, "organization_report.json")
        try:
            with open(report_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Organization report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Error saving report to {report_path}: {e}")

if __name__ == '__main__':
    main()
