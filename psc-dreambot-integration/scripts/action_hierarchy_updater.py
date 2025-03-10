#!/usr/bin/env python3
"""
Action Hierarchy Library Updater

This script ensures the action_hierarchy_library.json contains all actions 
defined in the ActionID_CategoryMap by generating stub entries for any missing actions.
"""

import os
import sys
import re
import json
import argparse
import logging
import logging.handlers
import shutil
from typing import Dict, List, Set, Tuple, Optional

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filenames (not paths) to ensure cross-platform compatibility.
    
    Args:
        filename: Input filename (not full path)
    
    Returns:
        Sanitized filename safe for file systems
    """
    # Ensure input is a string
    if not isinstance(filename, str):
        filename = str(filename)
    
    # Remove invalid filename characters
    invalid_chars = r'<>:"/\|?*'
    sanitized_filename = ''.join(char for char in filename if char not in invalid_chars)
    
    # Replace multiple consecutive spaces
    sanitized_filename = re.sub(r'\s+', ' ', sanitized_filename)
    
    return sanitized_filename.strip()

def validate_and_normalize_path(path: str, must_exist: bool = False, context: str = "Path") -> str:
    """
    Validate and normalize file paths with comprehensive checks.
    
    Args:
        path: Input file path
        must_exist: If True, raise error if path does not exist
        context: Provides context for more informative error messages
    
    Returns:
        Fully normalized, absolute path
    
    Raises:
        ValueError: For invalid path configurations
        FileNotFoundError: If path must exist but does not
    """
    try:
        # Convert to string and strip whitespace
        path = str(path).strip()
        
        # Check for empty path
        if not path:
            raise ValueError(f"{context} cannot be empty")
        
        # Expand user directory and normalize path
        expanded_path = os.path.expanduser(path)
        normalized_path = os.path.normpath(expanded_path)
        
        # Ensure absolute path
        if not os.path.isabs(normalized_path):
            normalized_path = os.path.abspath(normalized_path)
        
        # Check existence if required
        if must_exist and not os.path.exists(normalized_path):
            raise FileNotFoundError(f"{context} does not exist: {normalized_path}")
        
        return normalized_path
    
    except Exception as e:
        logger.error(f"{context} validation error: {str(e)}")
        raise

def configure_logging():
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create a 'logs' directory in the parent directory (project root)
    log_dir = os.path.join(os.path.dirname(script_dir), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up logging configuration
    log_file = os.path.join(log_dir, 'hierarchy_updater.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Configure logging
logger = configure_logging()

def _json_parse_constant(constant):
    """
    Custom JSON parsing handler to provide more context on parsing errors.
    
    Args:
        constant: The problematic constant encountered during JSON parsing
    
    Raises:
        ValueError: With detailed parsing error information
    """
    raise ValueError(f"Invalid JSON constant: {constant}")

def load_json_file(file_path: str, context: str = "JSON") -> Optional[Dict]:
    """
    Load a JSON file with comprehensive error handling.
    
    Args:
        file_path: Path to the JSON file
        context: Context for more informative error messages
    
    Returns:
        Parsed JSON content or None if parsing failed
    """
    try:
        # Validate and normalize path
        normalized_path = validate_and_normalize_path(
            file_path, 
            must_exist=True, 
            context=f"{context} file"
        )
        
        with open(normalized_path, 'r', encoding='utf-8') as f:
            # Remove comments and whitespace
            content = f.read()
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            # Strict JSON parsing
            return json.loads(content, parse_constant=_json_parse_constant)
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {context} file {file_path}: {e}")
        return None

def save_json_file(file_path: str, data: Dict, indent: int = 2) -> bool:
    """
    Save data to a JSON file with robust error handling.
    
    Args:
        file_path: Path to save the JSON file
        data: Data to be saved
        indent: Indentation for pretty-printing
    
    Returns:
        Boolean indicating success of save operation
    """
    try:
        # Validate and normalize path
        normalized_path = validate_and_normalize_path(file_path, context="Output JSON file")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
        
        with open(normalized_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False

def backup_file(file_path: str) -> bool:
    """
    Create a backup of a file before modifying it.
    
    Args:
        file_path: Path to the file to backup
    
    Returns:
        Boolean indicating success of backup operation
    """
    try:
        # Validate paths
        source_path = validate_and_normalize_path(file_path, must_exist=True)
        backup_path = source_path + ".bak"
        
        shutil.copy2(source_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return False

def get_clean_category_map(category_map: Dict) -> Dict:
    """
    Return a cleaned version of the category map without comment entries.
    
    Args:
        category_map: Original category map dictionary
    
    Returns:
        Cleaned category map without comment entries
    """
    return {k: v for k, v in category_map.items() if not k.startswith("/*")}

def find_missing_actions(category_map: Dict, hierarchy: Dict) -> List[str]:
    """
    Find actions that are in the category map but missing from the hierarchy.
    
    Args:
        category_map: Dictionary mapping action IDs to categories
        hierarchy: Existing action hierarchy dictionary
    
    Returns:
        List of action IDs missing from the hierarchy
    """
    clean_map = get_clean_category_map(category_map)
    hierarchy_actions = set(hierarchy.get("actions", {}).keys())
    
    return [
        action_id for action_id in clean_map 
        if action_id not in hierarchy_actions
    ]

def organize_by_category(missing_actions: List[str], category_map: Dict) -> Dict[str, List[str]]:
    """
    Organize missing actions by their category.
    
    Args:
        missing_actions: List of missing action IDs
        category_map: Dictionary mapping action IDs to categories
    
    Returns:
        Dictionary of categories with their missing actions
    """
    clean_map = get_clean_category_map(category_map)
    by_category = {}
    
    for action_id in missing_actions:
        category = clean_map.get(action_id)
        if category:
            by_category.setdefault(category, []).append(action_id)
    
    return by_category

def generate_stub_entry(action_id: str, category: str) -> Dict:
    """
    Generate a stub action hierarchy entry for a missing action.
    
    Args:
        action_id: ID of the missing action
        category: Category of the action
    
    Returns:
        Stub entry dictionary for the action
    """
    return {
        "category": category,
        "description": f"[AUTO-GENERATED] Stub entry for {action_id}",
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
            "parameters": [f"'Stub implementation for {action_id}'"]
        }
    }

def resolve_paths(base_dir: str, category_map: Optional[str], action_hierarchy: Optional[str]) -> Tuple[str, str]:
    """
    Resolve and validate paths for category map and action hierarchy.
    
    Args:
        base_dir: Base directory for path resolution
        category_map: Optional user-provided category map path
        action_hierarchy: Optional user-provided action hierarchy path
    
    Returns:
        Tuple of (category_map_path, action_hierarchy_path)
    
    Raises:
        FileNotFoundError: If no valid paths are found
    """
    # Normalize base directory
    base_dir = os.path.normpath(os.path.abspath(base_dir))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # List of potential paths to check (in order of priority)
    category_map_paths = []
    action_hierarchy_paths = []
    
    # Add user-specified paths if provided
    if category_map:
        category_map_paths.append(category_map)
    if action_hierarchy:
        action_hierarchy_paths.append(action_hierarchy)
    
    # Add paths relative to base_dir
    category_map_paths.append(os.path.join(base_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(base_dir, 'libraries', 'action_hierarchy_library.json'))
    
    # Add paths relative to script_dir's parent
    parent_dir = os.path.dirname(script_dir)
    category_map_paths.append(os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(parent_dir, 'libraries', 'action_hierarchy_library.json'))
    
    # Add paths relative to script_dir
    category_map_paths.append(os.path.join(script_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(script_dir, 'libraries', 'action_hierarchy_library.json'))
    
    # Check each path
    category_map_path = None
    for path in category_map_paths:
        try:
            if os.path.exists(path):
                category_map_path = path
                break
        except:
            continue
    
    action_hierarchy_path = None
    for path in action_hierarchy_paths:
        try:
            if os.path.exists(path):
                action_hierarchy_path = path
                break
        except:
            continue
    
    if not category_map_path:
        raise FileNotFoundError(f"Could not find a valid category map file. Searched: {', '.join(category_map_paths)}")
    
    if not action_hierarchy_path:
        raise FileNotFoundError(f"Could not find a valid action hierarchy file. Searched: {', '.join(action_hierarchy_paths)}")
    
    # Normalize paths
    category_map_path = os.path.normpath(os.path.abspath(category_map_path))
    action_hierarchy_path = os.path.normpath(os.path.abspath(action_hierarchy_path))
    
    return category_map_path, action_hierarchy_path

def update_hierarchy(hierarchy_path: str, category_map_path: str, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Update the action hierarchy with missing actions from the category map.
    
    Args:
        hierarchy_path: Path to the action hierarchy library
        category_map_path: Path to the category map
        dry_run: If True, only simulate updates without making changes
    
    Returns:
        Tuple of (success_status, number_of_added_actions)
    """
    # Load files
    hierarchy = load_json_file(hierarchy_path)
    if not hierarchy:
        logger.error("Failed to load action hierarchy")
        return False, 0
    
    category_map = load_json_file(category_map_path)
    if not category_map:
        logger.error("Failed to load category map")
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
        logger.error("Failed to create backup of hierarchy file")
        return False, 0
    
    # Add stub entries
    added_count = 0
    if not dry_run:
        # Ensure 'actions' key exists
        if 'actions' not in hierarchy:
            hierarchy['actions'] = {}
        
        for category, actions in by_category.items():
            logger.info(f"Adding {len(actions)} actions in category '{category}':")
            for action_id in actions:
                logger.info(f"  - {action_id}")
                hierarchy['actions'][action_id] = generate_stub_entry(action_id, category)
                added_count += 1
        
        # Save updated hierarchy
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
    
    try:
        # Resolve paths for category map and action hierarchy
        try:
            category_map_path, action_hierarchy_path = resolve_paths(
                args.base_dir, 
                args.category_map, 
                args.action_hierarchy
            )
        except FileNotFoundError as e:
            logger.error(str(e))
            return 1
        
        logger.info(f"Using category map: {category_map_path}")
        logger.info(f"Using action hierarchy: {action_hierarchy_path}")
        
        if args.dry_run:
            logger.info("Dry run mode - no changes will be made")
        
        # Update hierarchy
        success, added_count = update_hierarchy(
            action_hierarchy_path, 
            category_map_path, 
            args.dry_run
        )
        
        if success:
            if added_count > 0:
                logger.info(f"Successfully updated the action hierarchy with {added_count} missing actions")
            else:
                logger.info("Action hierarchy is already in sync with the category map")
            return 0
        else:
            logger.error("Failed to update the action hierarchy")
            return 1
    
    except Exception as e:
        logger.critical(f"Unexpected error in hierarchy update process: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    # Use sys.exit to provide meaningful return codes
    sys.exit(main())