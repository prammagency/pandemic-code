#!/usr/bin/env python3
"""
Action Synchronization and Validation Script

This script validates and synchronizes all components of the PSC standardization framework
with the ActionID_CategoryMap to ensure consistency across the entire system.
"""

import json
import os
import sys
import argparse
import logging
from typing import Dict, List, Set, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("action_validator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("action_validator")

def load_json_file(file_path: str) -> Optional[Dict]:
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None

def save_json_file(file_path: str, data: Dict) -> bool:
    """Save data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False

def get_clean_category_map(category_map: Dict) -> Dict:
    """Return a cleaned version of the category map without comment entries."""
    return {k: v for k, v in category_map.items() if not k.startswith("/*")}

def validate_category_map(category_map_path: str) -> Tuple[bool, Optional[Dict]]:
    """Validate the ActionID_CategoryMap for proper structure."""
    category_map = load_json_file(category_map_path)
    if not category_map:
        return False, None
    
    # Check for comment entries and real entries
    clean_map = get_clean_category_map(category_map)
    
    if len(clean_map) == 0:
        logger.error("Category map contains no valid action mappings")
        return False, None
    
    # Check for unique categories
    categories = set(clean_map.values())
    logger.info(f"Found {len(categories)} unique categories in the map")
    
    return True, category_map

def validate_against_action_hierarchy(category_map: Dict, hierarchy_path: str) -> Tuple[bool, List[str], List[str]]:
    """Validate that all actions in the category map exist in the action hierarchy."""
    hierarchy = load_json_file(hierarchy_path)
    if not hierarchy:
        return False, [], []
    
    clean_map = get_clean_category_map(category_map)
    
    # Check for actions in map but not in hierarchy
    missing_in_hierarchy = []
    for action_id in clean_map:
        if action_id not in hierarchy.get("actions", {}):
            missing_in_hierarchy.append(action_id)
    
    # Check for actions in hierarchy but not in map
    missing_in_map = []
    for action_id in hierarchy.get("actions", {}):
        if action_id not in clean_map:
            missing_in_map.append(action_id)
    
    logger.info(f"Found {len(missing_in_hierarchy)} actions in map but missing from hierarchy")
    logger.info(f"Found {len(missing_in_map)} actions in hierarchy but missing from map")
    
    return len(missing_in_hierarchy) == 0 and len(missing_in_map) == 0, missing_in_hierarchy, missing_in_map

def update_action_hierarchy(hierarchy_path: str, missing_actions: List[str], category_map: Dict) -> bool:
    """Update the action hierarchy to include missing actions with stub entries."""
    hierarchy = load_json_file(hierarchy_path)
    if not hierarchy:
        return False
    
    clean_map = get_clean_category_map(category_map)
    
    # Add stub entries for missing actions
    for action_id in missing_actions:
        if action_id in clean_map:
            category = clean_map[action_id]
            hierarchy["actions"][action_id] = {
                "category": category,
                "description": f"[AUTO-GENERATED] {action_id}",
                "can_be_root": True,
                "valid_parents": ["root"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"]
            }
            logger.info(f"Added stub entry for {action_id} in category {category}")
    
    # Save updated hierarchy
    return save_json_file(hierarchy_path, hierarchy)

def update_category_map(category_map_path: str, missing_actions: List[str], hierarchy: Dict) -> bool:
    """Update the category map to include actions from the hierarchy."""
    category_map = load_json_file(category_map_path)
    if not category_map:
        return False
    
    # Add entries for missing actions
    for action_id in missing_actions:
        if action_id in hierarchy.get("actions", {}):
            action_info = hierarchy["actions"][action_id]
            category = action_info.get("category", "uncategorized")
            
            # Find the appropriate section comment
            section_found = False
            section_comment = f"/* {category.upper()} */"
            
            # Try to insert near similar categories
            for existing_key in list(category_map.keys()):
                if existing_key.startswith("/*") and category.upper() in existing_key:
                    section_comment = existing_key
                    section_found = True
                    break
            
            if not section_found:
                # Add a new section comment
                category_map[section_comment] = "/* COMMENTS AREN'T PART OF JSON, JUST FOR READABILITY */"
            
            # Add the action
            category_map[action_id] = category
            logger.info(f"Added {action_id} to category map under {category}")
    
    # Save updated category map
    return save_json_file(category_map_path, category_map)

def validate_scripts_against_map(scripts_dir: str, category_map: Dict) -> Tuple[bool, Dict]:
    """Validate that scripts correctly handle the category map structure."""
    issues = {}
    clean_map = get_clean_category_map(category_map)
    categories = set(clean_map.values())
    
    # Files to check
    script_files = [
        os.path.join(scripts_dir, "organize_psc_files.py"),
        os.path.join(scripts_dir, "psc_standardizer.py"),
        os.path.join(scripts_dir, "batch_process.sh")
    ]
    
    for script_path in script_files:
        if not os.path.exists(script_path):
            logger.warning(f"Script file not found: {script_path}")
            continue
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        script_issues = []
        
        # Check for common issues
        if script_path.endswith("organize_psc_files.py"):
            if "startswith(\"/*\")" not in content and "startswith('/*')" not in content:
                script_issues.append("Missing filter for comment entries in category map")
        
        if script_path.endswith("batch_process.sh"):
            # Check if all categories are handled
            for category in categories:
                if category not in content:
                    script_issues.append(f"Category '{category}' not referenced in batch script")
        
        if script_issues:
            issues[os.path.basename(script_path)] = script_issues
    
    return len(issues) == 0, issues

def suggest_script_fixes(issues: Dict) -> Dict:
    """Generate suggested fixes for script issues."""
    suggestions = {}
    
    for script, script_issues in issues.items():
        script_suggestions = []
        
        if script == "organize_psc_files.py" and "Missing filter for comment entries" in str(script_issues):
            script_suggestions.append(
                "Add code to filter comment entries:\n"
                "# Filter out comment entries\n"
                "category_map = {k: v for k, v in category_map.items() if not k.startswith(\"/*\")}\n"
                "logger.info(f\"Loaded category map with {len(category_map)} action mappings (excluding comments)\")"
            )
        
        if script == "batch_process.sh" and "not referenced in batch script" in str(script_issues):
            script_suggestions.append(
                "Update the game-specific library logic to handle all categories:\n"
                "# Determine which libraries to use based on category\n"
                "case \"$category\" in\n"
                "    combat|entities_npcs)\n"
                "        EXTRA_ARGS=\"$EXTRA_ARGS --use-monster-library\"\n"
                "        ;;\n"
                "    equipment|inventory)\n"
                "        EXTRA_ARGS=\"$EXTRA_ARGS --use-equipment-library\"\n"
                "        ;;\n"
                "    walking|banking)\n"
                "        EXTRA_ARGS=\"$EXTRA_ARGS --use-location-library\"\n"
                "        ;;\n"
                "esac"
            )
        
        if script == "psc_standardizer.py":
            script_suggestions.append(
                "Add validation against category map:\n"
                "# Load category map for validation\n"
                "category_map_path = os.path.join(os.path.dirname(__file__), '..', 'mapping', 'ActionID_CategoryMap.json')\n"
                "try:\n"
                "    with open(category_map_path, 'r') as f:\n"
                "        category_map = json.load(f)\n"
                "        # Filter out comment keys\n"
                "        category_map = {k: v for k, v in category_map.items() if not k.startswith(\"/*\")}\n"
                "except Exception as e:\n"
                "    logger.warning(f\"Could not load category map: {e}. Proceeding without category validation.\")\n"
                "    category_map = {}"
            )
        
        if script_suggestions:
            suggestions[script] = script_suggestions
    
    return suggestions

def main():
    """Main function for the action validator."""
    parser = argparse.ArgumentParser(description='Validate and synchronize actions across the PSC framework')
    parser.add_argument('--base-dir', default='.', help='Base directory of the PSC framework')
    parser.add_argument('--category-map', help='Path to ActionID_CategoryMap.json')
    parser.add_argument('--action-hierarchy', help='Path to action_hierarchy_library.json')
    parser.add_argument('--scripts-dir', help='Path to scripts directory')
    parser.add_argument('--update-hierarchy', action='store_true', help='Update action hierarchy with missing entries')
    parser.add_argument('--update-map', action='store_true', help='Update category map with missing entries')
    parser.add_argument('--check-scripts', action='store_true', help='Check scripts for compatibility with category map')
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    base_dir = os.path.abspath(args.base_dir)
    category_map_path = args.category_map or os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json')
    action_hierarchy_path = args.action_hierarchy or os.path.join(parent_dir, 'libraries', 'action_hierarchy_library.json')
    scripts_dir = args.scripts_dir or script_dir
    
    logger.info(f"Using category map: {category_map_path}")
    logger.info(f"Using action hierarchy: {action_hierarchy_path}")
    logger.info(f"Using scripts directory: {scripts_dir}")
    
    # Validate category map
    is_valid_map, category_map = validate_category_map(category_map_path)
    if not is_valid_map:
        logger.error("Category map validation failed")
        return 1
    
    # Validate against action hierarchy
    is_consistent, missing_in_hierarchy, missing_in_map = validate_against_action_hierarchy(
        category_map, action_hierarchy_path
    )
    
    if not is_consistent:
        logger.warning("Inconsistencies found between category map and action hierarchy")
        
        if missing_in_hierarchy:
            logger.warning("Actions in map but missing from hierarchy:")
            for action in missing_in_hierarchy:
                logger.warning(f"  - {action}")
            
            if args.update_hierarchy:
                logger.info("Updating action hierarchy with missing entries...")
                if update_action_hierarchy(action_hierarchy_path, missing_in_hierarchy, category_map):
                    logger.info("Action hierarchy updated successfully")
                else:
                    logger.error("Failed to update action hierarchy")
        
        if missing_in_map:
            logger.warning("Actions in hierarchy but missing from map:")
            for action in missing_in_map:
                logger.warning(f"  - {action}")
            
            if args.update_map:
                logger.info("Updating category map with missing entries...")
                hierarchy = load_json_file(action_hierarchy_path)
                if hierarchy and update_category_map(category_map_path, missing_in_map, hierarchy):
                    logger.info("Category map updated successfully")
                else:
                    logger.error("Failed to update category map")
    else:
        logger.info("Category map and action hierarchy are consistent!")
    
    # Check scripts
    if args.check_scripts:
        logger.info("Validating scripts for compatibility with category map...")
        scripts_valid, script_issues = validate_scripts_against_map(scripts_dir, category_map)
        
        if not scripts_valid:
            logger.warning("Issues found with scripts:")
            for script, issues in script_issues.items():
                logger.warning(f"  {script}:")
                for issue in issues:
                    logger.warning(f"    - {issue}")
            
            # Generate suggestions
            suggestions = suggest_script_fixes(script_issues)
            if suggestions:
                logger.info("Suggested fixes:")
                for script, fixes in suggestions.items():
                    logger.info(f"  {script}:")
                    for fix in fixes:
                        logger.info(f"    {fix}")
        else:
            logger.info("All scripts appear compatible with the category map")
    
    logger.info("Validation complete")
    return 0 if is_valid_map and is_consistent else 1

if __name__ == '__main__':
    sys.exit(main())
