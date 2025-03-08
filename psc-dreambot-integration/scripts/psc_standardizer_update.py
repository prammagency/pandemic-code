#!/usr/bin/env python3
"""
PSC Standardizer Update Script

This script updates the PSC Standardizer to properly integrate with the comprehensive 
ActionID_CategoryMap and ensures proper handling of all action categories.
"""

import os
import re
import sys
import argparse
import logging
import shutil
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("standardizer_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("standardizer_update")

def backup_file(file_path: str) -> bool:
    """Create a backup of a file before modifying it."""
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return False

def update_organize_psc_files(file_path: str) -> bool:
    """Update organize_psc_files.py to properly handle comment entries in the category map."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create backup
    if not backup_file(file_path):
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if the file already filters comment entries
        if "startswith(\"/*\")" in content or "startswith('/*')" in content:
            logger.info(f"File {file_path} already filters comment entries")
            return True
        
        # Pattern to find where to insert the filter
        pattern = r"(\s+# Load category map[\s\S]+?try:[\s\S]+?with open\([^)]+\) as f:[\s\S]+?category_map = json\.load\(f\)[\s\S]+?logger\.info\([^)]+\))"
        
        # Add filter code after loading the category map
        filter_code = """
        # Filter out comment entries
        category_map = {k: v for k, v in category_map.items() if not k.startswith("/*")}
        logger.info(f"Loaded category map with {len(category_map)} action mappings (excluding comments)")"""
        
        updated_content = re.sub(pattern, r"\1" + filter_code, content)
        
        # Save updated file
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info(f"Updated {file_path} to filter comment entries")
        return True
    except Exception as e:
        logger.error(f"Failed to update {file_path}: {e}")
        # Restore backup
        shutil.copy2(file_path + ".bak", file_path)
        logger.info(f"Restored backup of {file_path}")
        return False

def update_psc_standardizer(file_path: str) -> bool:
    """Update psc_standardizer.py to validate against the category map."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create backup
    if not backup_file(file_path):
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if the file already loads the category map
        if "category_map_path = " in content and "category_map = json.load" in content:
            logger.info(f"File {file_path} already loads the category map")
            return True
        
        # Pattern to find where to insert the category map loading
        # Look for the main function definition
        main_pattern = r"(def main\(\):[\s\S]+?args = parser\.parse_args\(\)[\s\S]+?if not args\.command:[\s\S]+?parser\.print_help\(\)[\s\S]+?return[\s\S]+?# Set paths for libraries)"
        
        # Add category map loading code before loading libraries
        category_map_code = """
    # Set paths for libraries
    libraries_path = os.path.join(os.path.dirname(__file__), '..', 'libraries')
    
    # Set path for category map
    category_map_path = os.path.join(os.path.dirname(__file__), '..', 'mapping', 'ActionID_CategoryMap.json')
    """
        
        updated_content = re.sub(main_pattern, r"\1" + category_map_code, content)
        
        # Now add category map loading to standardize_psc_file function
        standardize_pattern = r"(def standardize_psc_file\([^)]+\):[\s\S]+?logger\.info\(f\"Standardizing file: \{input_file\}\"\))"
        
        category_map_loading_code = """
    # Load category map for validation if available
    category_map_path = os.path.join(os.path.dirname(__file__), '..', 'mapping', 'ActionID_CategoryMap.json')
    category_map = {}
    try:
        with open(category_map_path, 'r') as f:
            cm = json.load(f)
            # Filter out comment keys
            category_map = {k: v for k, v in cm.items() if not k.startswith("/*")}
        logger.info(f"Loaded category map with {len(category_map)} action mappings")
    except Exception as e:
        logger.warning(f"Could not load category map: {e}. Proceeding without category validation.")
    """
        
        updated_content = re.sub(standardize_pattern, r"\1" + category_map_loading_code, updated_content)
        
        # Add action validation against category map
        validate_pattern = r"(def process_actions\([^)]+\):[\s\S]+?for action in actions:[\s\S]+?action_id = action\.get\(\"id\"\)[\s\S]+?if not action_id:[\s\S]+?continue[\s\S]+?# Get action information from hierarchy)"
        
        validation_code = """
            # Get action information from hierarchy
            action_info = action_hierarchy["actions"].get(action_id, {})
            if not action_info:
                if action_id in category_map:
                    logger.warning(f"Action ID '{action_id}' found in category map but not in action hierarchy")
                else:
                    logger.warning(f"Unknown action ID '{action_id}' not found in category map or action hierarchy")
                continue
            """
        
        updated_content = re.sub(validate_pattern, r"\1" + validation_code, updated_content)
        
        # Save updated file
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info(f"Updated {file_path} to validate against category map")
        return True
    except Exception as e:
        logger.error(f"Failed to update {file_path}: {e}")
        # Restore backup
        shutil.copy2(file_path + ".bak", file_path)
        logger.info(f"Restored backup of {file_path}")
        return False

def update_batch_process(file_path: str, categories: List[str]) -> bool:
    """Update batch_process.sh to handle all categories from the map."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create backup
    if not backup_file(file_path):
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if the file already uses a case statement for categories
        if "case \"$category\" in" in content:
            logger.info(f"File {file_path} already uses a case statement for categories")
            return True
        
        # Find the extra args section
        extra_args_pattern = r"([ \t]+# Step 3: Standardize.*?EXTRA_ARGS=\"\".*?# Enable game-specific libraries based on category)(.*?)([ \t]+mkdir -p \"\$STD_DIR/\$category\")"
        
        # Create a case statement that handles all categories
        monster_categories = "|".join(["combat", "entities_npcs", "entities_player"])
        equipment_categories = "|".join(["equipment", "inventory"])
        location_categories = "|".join(["walking", "banking"])
        
        case_statement = """
        # Enable game-specific libraries based on category
        case "$category" in
            """ + monster_categories + """)
                EXTRA_ARGS="$EXTRA_ARGS --use-monster-library"
                ;;
            """ + equipment_categories + """)
                EXTRA_ARGS="$EXTRA_ARGS --use-equipment-library"
                ;;
            """ + location_categories + """)
                EXTRA_ARGS="$EXTRA_ARGS --use-location-library"
                ;;
        esac
        """
        
        # Replace the hard-coded library selection with the case statement
        updated_content = re.sub(extra_args_pattern, r"\1" + case_statement + r"\3", content)
        
        # Add category map existence check
        check_pattern = r"(# Check that the category map exists.*?if \[ ! -f \"\$CATEGORY_MAP\" \]; then)"
        
        if check_pattern not in content:
            # Add category map check after argument parsing
            arg_parsing_pattern = r"(done[\s\S]+?# Create necessary directories)"
            
            category_check = """
# Check that the category map exists
if [ ! -f "$CATEGORY_MAP" ]; then
    echo "Error: Category map file does not exist: $CATEGORY_MAP"
    exit 1
fi

# Verify category if specified
if [ -n "$SPECIFIC_CATEGORY" ]; then
    # Get unique categories from the category map (exclude comment lines)
    VALID_CATEGORY=$(grep -v "\/\*" "$CATEGORY_MAP" | grep -o "\"$SPECIFIC_CATEGORY\"" | wc -l)
    if [ $VALID_CATEGORY -eq 0 ]; then
        echo "Error: Specified category '$SPECIFIC_CATEGORY' not found in category map"
        echo "Please check the available categories in the map file: $CATEGORY_MAP"
        exit 1
    fi
fi
"""
            updated_content = re.sub(arg_parsing_pattern, r"\1" + category_check, updated_content)
        
        # Save updated file
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        logger.info(f"Updated {file_path} to handle all categories from the map")
        return True
    except Exception as e:
        logger.error(f"Failed to update {file_path}: {e}")
        # Restore backup
        shutil.copy2(file_path + ".bak", file_path)
        logger.info(f"Restored backup of {file_path}")
        return False

def main():
    """Main function to update the PSC standardization tools."""
    parser = argparse.ArgumentParser(description='Update PSC standardization tools to integrate with ActionID_CategoryMap')
    parser.add_argument('--base-dir', default='.', help='Base directory of the PSC framework')
    parser.add_argument('--category-map', help='Path to ActionID_CategoryMap.json')
    parser.add_argument('--skip-backup', action='store_true', help='Skip creating backups of files')
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    base_dir = os.path.abspath(args.base_dir)
    category_map_path = args.category_map or os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json')
    scripts_dir = script_dir

    organize_psc_path = os.path.join(scripts_dir, 'organize_psc_files.py')
    standardizer_path = os.path.join(scripts_dir, 'psc_standardizer.py')
    batch_process_path = os.path.join(scripts_dir, 'batch_process.bat')
    
    # Check if files exist
    if not os.path.exists(category_map_path):
        logger.error(f"Category map not found: {category_map_path}")
        return 1
    
    if not os.path.exists(organize_psc_path):
        logger.error(f"organize_psc_files.py not found: {organize_psc_path}")
        return 1
    
    if not os.path.exists(standardizer_path):
        logger.error(f"psc_standardizer.py not found: {standardizer_path}")
        return 1
    
    if not os.path.exists(batch_process_path):
        logger.error(f"batch_process.sh not found: {batch_process_path}")
        return 1
    
    # Load category map to get categories
    import json
    try:
        with open(category_map_path, 'r') as f:
            category_map = json.load(f)
        # Filter out comment entries
        categories = set([v for k, v in category_map.items() if not k.startswith("/*")])
        logger.info(f"Found {len(categories)} unique categories in category map")
    except Exception as e:
        logger.error(f"Failed to load category map: {e}")
        return 1
    
    # Update files
    success = True
    
    logger.info("Updating organize_psc_files.py...")
    if not update_organize_psc_files(organize_psc_path):
        success = False
    
    logger.info("Updating psc_standardizer.py...")
    if not update_psc_standardizer(standardizer_path):
        success = False
    
    logger.info("Updating batch_process.sh...")
    if not update_batch_process(batch_process_path, list(categories)):
        success = False
    
    if success:
        logger.info("All files updated successfully to integrate with ActionID_CategoryMap")
    else:
        logger.error("Some updates failed - check the log for details")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())