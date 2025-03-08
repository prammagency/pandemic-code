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

def sanitize_path(path: str) -> str:
    """
    Sanitize file paths to ensure cross-platform compatibility.
    
    Args:
        path: Input file path
    
    Returns:
        Sanitized path safe for file systems
    """
    # Ensure input is a string
    if not isinstance(path, str):
        path = str(path)
    
    # Remove invalid filename characters
    invalid_chars = r'<>:"/\|?*'
    sanitized_path = ''.join(char for char in path if char not in invalid_chars)
    
    # Replace multiple consecutive spaces
    sanitized_path = re.sub(r'\s+', ' ', sanitized_path)
    
    return sanitized_path.strip()

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
        
        # Expand user directory and resolve symlinks
        expanded_path = os.path.expanduser(path)
        normalized_path = os.path.realpath(expanded_path)
        
        # Ensure absolute path
        if not os.path.isabs(normalized_path):
            normalized_path = os.path.abspath(normalized_path)
        
        # Sanitize path (remove invalid characters)
        sanitized_path = sanitize_path(normalized_path)
        
        # Check existence if required
        if must_exist:
            if not os.path.exists(sanitized_path):
                raise FileNotFoundError(f"{context} does not exist: {sanitized_path}")
            
            # Additional checks for read/write permissions
            if not os.access(sanitized_path, os.R_OK | os.W_OK):
                raise PermissionError(f"No read/write permission for {context}: {sanitized_path}")
        
        return sanitized_path
    
    except Exception as e:
        logger.error(f"{context} validation error: {e}")
        raise

def configure_logging(log_file="action_validator.log", log_level=logging.INFO):
    """
    Configure comprehensive logging with rotation and detailed formatting.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level
    
    Returns:
        Configured logger
    """
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("action_validator")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Potential paths for category map
    category_map_paths = [
        category_map,
        os.path.join(parent_dir, 'mapping', 'ActionID_CategoryMap.json'),
        os.path.join(base_dir, 'mapping', 'ActionID_CategoryMap.json'),
        os.path.join(script_dir, 'ActionID_CategoryMap.json')
    ]

    # Potential paths for action hierarchy
    action_hierarchy_paths = [
        action_hierarchy,
        os.path.join(parent_dir, 'libraries', 'action_hierarchy_library.json'),
        os.path.join(base_dir, 'libraries', 'action_hierarchy_library.json'),
        os.path.join(script_dir, 'action_hierarchy_library.json')
    ]

    # Potential paths for scripts directory
    scripts_dir_paths = [
        scripts_dir,
        script_dir,
        os.path.join(parent_dir, 'scripts'),
        base_dir
    ]

    # Find first valid category map path
    category_map_path = next((
        path for path in category_map_paths 
        if path and os.path.exists(validate_and_normalize_path(path, must_exist=True))
    ), None)

    # Find first valid action hierarchy path
    action_hierarchy_path = next((
        path for path in action_hierarchy_paths 
        if path and os.path.exists(validate_and_normalize_path(path, must_exist=True))
    ), None)

    # Find first valid scripts directory
    scripts_dir_path = next((
        path for path in scripts_dir_paths 
        if path and os.path.isdir(validate_and_normalize_path(path, must_exist=True))
    ), None)

    if not category_map_path:
        raise FileNotFoundError("Could not find a valid category map file")
    
    if not action_hierarchy_path:
        raise FileNotFoundError("Could not find a valid action hierarchy file")
    
    if not scripts_dir_path:
        raise FileNotFoundError("Could not find a valid scripts directory")

    return category_map_path, action_hierarchy_path, scripts_dir_path

# [Rest of the previous script's functions remain the same]

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
            category_map_path, action_hierarchy_path, scripts_dir = resolve_paths(
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
        logger.info(f"Using scripts directory: {scripts_dir}")
        
        # [Rest of the main function remains the same as in the original script]
        # ... (keep the rest of the existing main() function implementation)
    
    except Exception as e:
        logger.critical(f"Unexpected error in validation process: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())