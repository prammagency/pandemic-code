#!/usr/bin/env python3
"""
Action Hierarchy Library Updater

This script ensures the action_hierarchy_library.json contains all actions 
defined in the ActionID_CategoryMap by generating stub entries for any missing actions.
"""

import os
import sys
import json
import argparse
import logging
import shutil
from typing import Dict, List, Set, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hierarchy_updater.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("hierarchy_updater")

def load_json_file(file_path: str) -> Optional[Dict]:
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None

def save_json_file(file_path: str, data: Dict, indent: int = 2) -> bool:
    """Save data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False

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

def get_clean_category_map(category_map: Dict) -> Dict:
    """Return a cleaned version of the category map without comment entries."""
    return {k: v for k, v in category_map.items() if not k.startswith("/*")}

def find_missing_actions(category_map: Dict, hierarchy: Dict) -> List[str]:
    """Find actions that are in the category map but missing from the hierarchy."""
    clean_map = get_clean_category_map(category_map)
    hierarchy_actions = set(hierarchy.get("actions", {}).keys())
    
    missing_actions = []
    for action_id in clean_map:
        if action_id not in hierarchy_actions:
            missing_actions.append(action_id)
    
    return missing_actions

def organize_by_category(missing_actions: List[str], category_map: Dict) -> Dict[str, List[str]]:
    """Organize missing actions by their category."""
    clean_map = get_clean_category_map(category_map)
    by_category = {}
    
    for action_id in missing_actions:
        category = clean_map.get(action_id)
        if category:
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(action_id)
    
    return by_category

def generate_stub_entry(action_id: str, category: str) -> Dict:
    """Generate a stub action hierarchy entry for a missing action."""
    return {
        "category": category,
        "description": f"[AUTO-GENERATED] {action_id}",
        "can_be_root": True,
        "valid_parents": ["root"],
        "properties": {
            "required": [],
            "optional": []
        },
        "valid_children": ["*"],
        "dreambot_api_mapping": {
            "class": "org.dreambot.api.methods.MethodProvider",
            "method": "log",
            "parameters": [f"'Not implemented: {action_id}'"]
        }
    }

def update_hierarchy(hierarchy_path: str, category_map_path: str, dry_run: bool = False) -> Tuple[bool, int]:
    """Update the action hierarchy with missing actions from the category map."""
    # Load files
    hierarchy = load_json_file(hierarchy_path)
    if not hierarchy:
        return False, 0
    
    category_map = load_json_file(category_map_path)
    if not category_map:
        return False, 0
    
    # Find missing actions
    missing_actions = find_missing_actions(category_map, hierarchy)
    if not missing_actions:
        logger.info("No missing actions found - hierarchy is complete!")
        return True, 0
    
    logger.info(f"Found {len(missing_actions)} actions in category map missing from hierarchy")
    
    # Organize by category
    by_category = organize_by_category(missing_actions, category_map)
    
    # Create backup before modifying
    if not dry_run and not backup_file(hierarchy_path):
        return False, 0
    
    # Add stub entries
    added_count = 0
    for category, actions in by_category.items():
        logger.info(f"Adding {len(actions)} actions in category '{category}':")
        for action_id in actions:
            logger.info(f"  - {action_id}")
            if not dry_run:
                hierarchy["actions"][action_id] = generate_stub_entry(action_id, category)
                added_count += 1
    
    # Save updated hierarchy
    if not dry_run:
        if save_json_file(hierarchy_path, hierarchy):
            logger.info(f"Successfully added {added_count} missing actions to the hierarchy")
            return True, added_count
        else:
            logger.error("Failed to save updated hierarchy")
            return False, 0
    else:
        logger.info(f"Dry run - would have added {len(missing_actions)} actions to the hierarchy")
        return True, 0

def main():
    """Main function for the hierarchy updater."""
    parser = argparse.ArgumentParser(description='Update action hierarchy with missing actions from category map')
    parser.add_argument('--base-dir', default='.', help='Base directory of the PSC framework')
    parser.add_argument('--category-map', help='Path to ActionID_CategoryMap.json')
    parser.add_argument('--action-hierarchy', help='Path to action_hierarchy_library.json')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    # Determine paths - using absolute paths with parent directory
    base_dir = os.path.abspath(args.base_dir)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    category_map_path = args.category_map or os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json')
    action_hierarchy_path = args.action_hierarchy or os.path.join(parent_dir, 'libraries', 'action_hierarchy_library.json')
    
    logger.info(f"Using category map: {category_map_path}")
    logger.info(f"Using action hierarchy: {action_hierarchy_path}")
    
    if args.dry_run:
        logger.info("Dry run mode - no changes will be made")
    
    # Check if files exist
    if not os.path.exists(category_map_path):
        logger.error(f"Category map not found: {category_map_path}")
        return 1
    
    if not os.path.exists(action_hierarchy_path):
        logger.error(f"Action hierarchy not found: {action_hierarchy_path}")
        return 1
    
    # Update hierarchy
    success, added_count = update_hierarchy(action_hierarchy_path, category_map_path, args.dry_run)
    
    if success:
        if added_count > 0:
            logger.info(f"Successfully updated the action hierarchy with {added_count} missing actions")
        else:
            logger.info("Action hierarchy is already in sync with the category map")
        return 0
    else:
        logger.error("Failed to update the action hierarchy")
        return 1

if __name__ == '__main__':
    sys.exit(main())
