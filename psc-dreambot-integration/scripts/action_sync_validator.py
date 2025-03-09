#!/usr/bin/env python3
"""
Action Synchronization and Validation Script

This script validates and synchronizes all components of the PSC standardization framework
with the ActionID_CategoryMap to ensure consistency across the entire system.
"""

import json
import os
import sys
import re
import argparse
import logging
import logging.handlers
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
    """
    Configure comprehensive logging with rotation and detailed formatting.
    
    Returns:
        Configured logger
    """
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create a 'logs' directory in the parent directory (project root)
    log_dir = os.path.join(os.path.dirname(script_dir), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up log file path
    log_file = os.path.join(log_dir, 'action_validator.log')
    
    # Create logger
    logger = logging.getLogger("action_validator")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

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

def resolve_paths(base_dir: str, category_map: Optional[str], action_hierarchy: Optional[str], scripts_dir: Optional[str]) -> Tuple[str, str, str]:
    """
    Resolve and validate paths for category map, action hierarchy, and scripts directory.
    
    Args:
        base_dir: Base directory for path resolution
        category_map: Optional user-provided category map path
        action_hierarchy: Optional user-provided action hierarchy path
        scripts_dir: Optional user-provided scripts directory path
    
    Returns:
        Tuple of (category_map_path, action_hierarchy_path, scripts_dir_path)
    
    Raises:
        FileNotFoundError: If no valid paths are found
    """
    # Normalize base directory
    base_dir = os.path.normpath(os.path.abspath(base_dir))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    # List of potential paths to check (in order of priority)
    category_map_paths = []
    action_hierarchy_paths = []
    scripts_dir_paths = []
    
    # Add user-specified paths if provided
    if category_map:
        category_map_paths.append(category_map)
    if action_hierarchy:
        action_hierarchy_paths.append(action_hierarchy)
    if scripts_dir:
        scripts_dir_paths.append(scripts_dir)
    
    # Add paths relative to base_dir
    category_map_paths.append(os.path.join(base_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(base_dir, 'libraries', 'action_hierarchy_library.json'))
    scripts_dir_paths.append(os.path.join(base_dir, 'data', 'raw'))
    
    # Add paths relative to script_dir's parent
    category_map_paths.append(os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(parent_dir, 'libraries', 'action_hierarchy_library.json'))
    scripts_dir_paths.append(os.path.join(parent_dir, 'data', 'raw'))
    
    # Add paths relative to script_dir
    category_map_paths.append(os.path.join(script_dir, 'mapping', 'ActionID_CategoryMap.json'))
    action_hierarchy_paths.append(os.path.join(script_dir, 'libraries', 'action_hierarchy_library.json'))
    scripts_dir_paths.append(script_dir)
    
    # Default to script_dir for scripts_dir_paths
    scripts_dir_paths.append(script_dir)
    
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
    
    scripts_dir_path = None
    for path in scripts_dir_paths:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                scripts_dir_path = path
                break
        except:
            continue
    
    if not category_map_path:
        raise FileNotFoundError(f"Could not find a valid category map file. Searched: {', '.join(category_map_paths)}")
    
    if not action_hierarchy_path:
        raise FileNotFoundError(f"Could not find a valid action hierarchy file. Searched: {', '.join(action_hierarchy_paths)}")
    
    if not scripts_dir_path:
        raise FileNotFoundError(f"Could not find a valid scripts directory. Searched: {', '.join(scripts_dir_paths)}")
    
    # Normalize paths
    category_map_path = os.path.normpath(os.path.abspath(category_map_path))
    action_hierarchy_path = os.path.normpath(os.path.abspath(action_hierarchy_path))
    scripts_dir_path = os.path.normpath(os.path.abspath(scripts_dir_path))
    
    return category_map_path, action_hierarchy_path, scripts_dir_path

def find_all_json_files(directory: str) -> List[str]:
    """
    Find all JSON files in a directory and its subdirectories.
    
    Args:
        directory: Root directory to search
    
    Returns:
        List of paths to JSON files
    """
    json_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    return json_files

def extract_action_ids_from_json(json_file: str) -> Set[str]:
    """
    Extract all action IDs used in a JSON file.
    
    Args:
        json_file: Path to the JSON file
    
    Returns:
        Set of action IDs found in the file
    """
    action_ids = set()
    
    try:
        data = load_json_file(json_file)
        if not data:
            return action_ids
        
        # Check if this is a PSC script
        if 'actions' in data and isinstance(data['actions'], list):
            # Process root actions
            for action in data['actions']:
                if 'id' in action and isinstance(action['id'], str):
                    action_ids.add(action['id'])
                
                # Process children recursively
                action_ids.update(extract_action_ids_from_node(action))
    
    except Exception as e:
        logger.error(f"Error extracting action IDs from {json_file}: {e}")
    
    return action_ids

def extract_action_ids_from_node(node: Dict) -> Set[str]:
    """
    Recursively extract action IDs from a node and its children.
    
    Args:
        node: The node to process
    
    Returns:
        Set of action IDs found in the node and its children
    """
    action_ids = set()
    
    # Skip if not a dictionary
    if not isinstance(node, dict):
        return action_ids
    
    # Process children if present
    if 'children' in node and isinstance(node['children'], list):
        for child in node['children']:
            if isinstance(child, dict) and 'id' in child and isinstance(child['id'], str):
                action_ids.add(child['id'])
                # Process recursively
                action_ids.update(extract_action_ids_from_node(child))
    
    return action_ids

def validate_actions(category_map_path: str, action_hierarchy_path: str, scripts_dir: str) -> bool:
    """
    Validate all actions across the PSC framework.
    
    Args:
        category_map_path: Path to the category map
        action_hierarchy_path: Path to the action hierarchy
        scripts_dir: Path to the scripts directory
    
    Returns:
        Boolean indicating overall validation success
    """
    # Load necessary files
    category_map = load_json_file(category_map_path, "Category map")
    if not category_map:
        return False
    
    action_hierarchy = load_json_file(action_hierarchy_path, "Action hierarchy")
    if not action_hierarchy:
        return False
    
    # Extract sets of action IDs
    category_map_actions = set(category_map.keys())
    # Remove comment entries if any
    category_map_actions = {action for action in category_map_actions if not action.startswith("/*")}
    
    hierarchy_actions = set(action_hierarchy.get('actions', {}).keys())
    
    script_actions = set()
    if os.path.exists(scripts_dir) and os.path.isdir(scripts_dir):
        # Find all JSON files in scripts directory
        json_files = find_all_json_files(scripts_dir)
        logger.info(f"Found {len(json_files)} JSON files in {scripts_dir}")
        
        # Extract action IDs from JSON files
        for json_file in json_files:
            script_actions.update(extract_action_ids_from_json(json_file))
    
    # Log sizes
    logger.info(f"Actions in category map: {len(category_map_actions)}")
    logger.info(f"Actions in hierarchy: {len(hierarchy_actions)}")
    logger.info(f"Actions in scripts: {len(script_actions)}")
    
    # Find inconsistencies
    missing_in_hierarchy = category_map_actions - hierarchy_actions
    missing_in_category_map = hierarchy_actions - category_map_actions
    script_only_actions = script_actions - category_map_actions - hierarchy_actions
    
    # Log inconsistencies
    overall_success = True
    
    if missing_in_hierarchy:
        logger.warning(f"Found {len(missing_in_hierarchy)} actions in category map missing from hierarchy:")
        for action in sorted(missing_in_hierarchy):
            logger.warning(f"  - {action}")
        overall_success = False
    
    if missing_in_category_map:
        logger.warning(f"Found {len(missing_in_category_map)} actions in hierarchy missing from category map:")
        for action in sorted(missing_in_category_map):
            logger.warning(f"  - {action}")
        overall_success = False
    
    if script_only_actions:
        logger.warning(f"Found {len(script_only_actions)} actions in scripts not present in category map or hierarchy:")
        for action in sorted(script_only_actions):
            logger.warning(f"  - {action}")
        overall_success = False
    
    if overall_success:
        logger.info("All actions are in sync across the PSC framework")
    else:
        logger.warning("Found inconsistencies in action definitions")
    
    return overall_success

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
    
    try:
        # Resolve paths for category map, action hierarchy, and scripts directory
        try:
            category_map_path, action_hierarchy_path, scripts_dir_path = resolve_paths(
                args.base_dir, 
                args.category_map, 
                args.action_hierarchy,
                args.scripts_dir
            )
        except FileNotFoundError as e:
            logger.error(str(e))
            return 1
        
        logger.info(f"Using category map: {category_map_path}")
        logger.info(f"Using action hierarchy: {action_hierarchy_path}")
        logger.info(f"Using scripts directory: {scripts_dir_path}")
        
        # Validate actions across the framework
        validation_success = validate_actions(
            category_map_path, 
            action_hierarchy_path, 
            scripts_dir_path if args.check_scripts else None
        )
        
        if validation_success:
            logger.info("Validation completed successfully")
            return 0
        else:
            logger.warning("Validation completed with inconsistencies")
            return 1
    
    except Exception as e:
        logger.critical(f"Unexpected error in validation process: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())