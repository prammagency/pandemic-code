import os
import json
import shutil
import argparse
import sys
import logging
import re
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging (keeping original configuration to ensure compatibility)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("organize_psc_files.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("organize_psc_files")

def sanitize_path(path: str) -> str:
    """
    Sanitize file paths to ensure Windows compatibility and remove invalid characters.
    
    Args:
        path: Input file path
    
    Returns:
        Sanitized path safe for Windows file systems
    """
    # Ensure input is a string
    if not isinstance(path, str):
        path = str(path)
    
    # Remove invalid Windows filename characters
    invalid_chars = r'<>:"/\|?*'
    sanitized_path = ''.join(char for char in path if char not in invalid_chars)
    
    # Replace multiple consecutive spaces with a single space
    sanitized_path = re.sub(r'\s+', ' ', sanitized_path)
    
    # Trim leading/trailing whitespaces
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
        # Convert to string to handle potential non-string inputs
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
            
            # Additional checks for read permissions
            if not os.access(sanitized_path, os.R_OK):
                raise PermissionError(f"No read permission for {context}: {sanitized_path}")
        
        return sanitized_path
    
    except Exception as e:
        logger.error(f"{context} validation error: {e}")
        raise

def safe_makedirs(directory: str):
    """
    Safely create directories with comprehensive error handling.
    
    Args:
        directory: Directory path to create
    
    Raises:
        OSError: If directory cannot be created
    """
    try:
        # Normalize and validate the path
        normalized_dir = validate_and_normalize_path(directory)
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(normalized_dir)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # Create target directory
        os.makedirs(normalized_dir, exist_ok=True)
        
        # Verify directory was created
        if not os.path.isdir(normalized_dir):
            raise OSError(f"Failed to create directory: {normalized_dir}")
        
    except OSError as e:
        logger.error(f"Directory creation error: {e}")
        # Attempt alternative creation method for Windows
        try:
            subprocess.run(['mkdir', normalized_dir], check=True, shell=True)
        except Exception as alt_e:
            logger.critical(f"Absolutely cannot create directory {normalized_dir}: {alt_e}")
            raise

def _json_parse_error(constant):
    """
    Custom JSON parsing handler to provide more context on parsing errors.
    
    Args:
        constant: The problematic constant encountered during JSON parsing
    
    Raises:
        ValueError: With detailed parsing error information
    """
    raise ValueError(f"Invalid JSON constant: {constant}")

def load_json_with_comments(file_path: str) -> Optional[Dict]:
    """
    Load a JSON file with robust error handling and comment stripping.
    
    Args:
        file_path: Path to the JSON file to load
        
    Returns:
        Parsed JSON content or None if parsing failed
    
    Raises:
        JSONDecodeError: For invalid JSON syntax
        IOError: For file reading issues
    """
    try:
        # Validate path with context
        normalized_path = validate_and_normalize_path(
            file_path, 
            must_exist=True, 
            context="JSON File"
        )
        
        with open(normalized_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # More comprehensive comment removal
        # Remove multi-line comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Parse JSON with strict parsing
        return json.loads(content, parse_constant=_json_parse_error)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in {file_path}: {e}")
        return None
    except IOError as e:
        logger.error(f"File reading error for {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        return None

def validate_json_file(file_path: str) -> Tuple[bool, Optional[Dict]]:
    """
    Perform comprehensive validation of PSC JSON files.
    
    Args:
        file_path: Path to the JSON file to validate
        
    Returns:
        Tuple of (is_valid, json_content) where json_content is None if invalid
    """
    try:
        json_content = load_json_with_comments(file_path)
        
        # If loading failed, return invalid
        if json_content is None:
            logger.warning(f"Failed to load JSON content from {file_path}")
            return False, None
        
        # Extensive structural validation
        if not isinstance(json_content, dict):
            logger.warning(f"File {file_path} is not a JSON object")
            return False, None
        
        # Validate 'actions' array
        if "actions" not in json_content:
            logger.warning(f"File {file_path} missing 'actions' array")
            return False, None
        
        actions = json_content.get("actions", [])
        
        if not isinstance(actions, list):
            logger.warning(f"'actions' in {file_path} is not a valid array")
            return False, None
        
        if not actions:
            logger.warning(f"File {file_path} has empty 'actions' array")
            return False, None
        
        # Additional validation for first action
        root_action = actions[0]
        if not isinstance(root_action, dict):
            logger.warning(f"Invalid root action structure in {file_path}")
            return False, None
        
        # Ensure root action has an 'id'
        if 'id' not in root_action or not root_action['id']:
            logger.warning(f"Root action in {file_path} missing valid 'id'")
            return False, None
        
        return True, json_content
    
    except Exception as e:
        logger.error(f"Validation error for {file_path}: {e}")
        return False, None

def find_category_map(potential_paths: List[str]) -> Optional[str]:
    """
    Find the first existing category map file from a list of potential paths.
    
    Args:
        potential_paths: List of possible paths to the category map file
    
    Returns:
        Path to the first existing category map file, or None if not found
    """
    for path in potential_paths:
        try:
            normalized_path = validate_and_normalize_path(path, must_exist=True)
            # Attempt to load the JSON to verify it's valid
            with open(normalized_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
                
            # Additional check to ensure the JSON is a valid mapping
            if not isinstance(json_content, dict):
                logger.warning(f"Invalid category map structure in {normalized_path}")
                continue
            
            return normalized_path
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            continue
    
    return None

def organize_psc_files(source_dir: str, target_dir: str, category_map_file: str) -> Dict[str, Any]:
    """
    Organize PSC JSON files by categorizing them according to the category map.
    
    Args:
        source_dir: Directory containing raw PSC JSON files
        target_dir: Directory to store organized files
        category_map_file: Path to JSON file mapping action IDs to categories
        
    Returns:
        Dictionary with statistics of files processed by category
    """
    # Validate and normalize source and target directories
    source_dir = validate_and_normalize_path(source_dir, must_exist=True)
    target_dir = validate_and_normalize_path(target_dir)
    
    # Load category map
    try:
        with open(category_map_file, 'r', encoding='utf-8') as f:
            category_map = json.load(f)
        
        if not isinstance(category_map, dict):
            logger.error(f"Invalid category map structure in {category_map_file}")
            sys.exit(1)
        
        logger.info(f"Loaded category map with {len(category_map)} action mappings")
    except Exception as e:
        logger.error(f"Error loading category map from {category_map_file}: {e}")
        sys.exit(1)
    
    # Extract unique categories
    categories = set(category_map.values())
    logger.info(f"Found {len(categories)} unique categories: {', '.join(map(str, categories))}")
    
    # Create category directories
    for category in categories:
        # Validate category is a valid directory name
        sanitized_category = sanitize_path(str(category))
        if not sanitized_category:
            logger.warning(f"Invalid category name '{category}', skipping")
            continue
            
        category_dir = os.path.join(target_dir, sanitized_category)
        safe_makedirs(category_dir)
    
    # Create directory for uncategorized files
    uncategorized_dir = os.path.join(target_dir, "uncategorized")
    safe_makedirs(uncategorized_dir)
    
    # Create directory for invalid files
    invalid_dir = os.path.join(target_dir, "invalid")
    safe_makedirs(invalid_dir)
    
    # Track statistics
    stats = {
        "total_processed": 0,
        "valid_files": 0,
        "invalid_files": 0,
        "uncategorized_files": 0,
        "categories": {category: 0 for category in categories}
    }
    
    # Process each file in the source directory
    try:
        file_list = [f for f in os.listdir(source_dir) if f.endswith('.json')]
        logger.info(f"Found {len(file_list)} JSON files in {source_dir}")
    except Exception as e:
        logger.error(f"Error listing files in {source_dir}: {e}")
        sys.exit(1)

    for filename in file_list:
        try:
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
            if not actions:
                # This should be caught by validate_json_file, but just in case
                stats["invalid_files"] += 1
                output_path = os.path.join(invalid_dir, filename)
                shutil.copy2(input_path, output_path)
                logger.warning(f"File {filename} has no actions, copied to {invalid_dir}")
                continue
                
            root_action = actions[0]
            root_action_id = root_action.get("id")
            
            if not root_action_id:
                logger.warning(f"File {filename} has root action with no ID")
                stats["uncategorized_files"] += 1
                output_path = os.path.join(uncategorized_dir, filename)
                shutil.copy2(input_path, output_path)
                continue
            
            if root_action_id not in category_map:
                # Handle uncategorized files
                stats["uncategorized_files"] += 1
                output_path = os.path.join(uncategorized_dir, filename)
                shutil.copy2(input_path, output_path)
                logger.warning(f"Uncategorized file {filename} with root action {root_action_id} copied to {uncategorized_dir}")
                continue
            
            # File is valid and categorized
            stats["valid_files"] += 1
            category = category_map[root_action_id]
            
            # Ensure category is a valid directory name
            sanitized_category = sanitize_path(str(category))
            if not sanitized_category:
                logger.warning(f"Invalid category name '{category}' for action {root_action_id}, using 'uncategorized'")
                sanitized_category = "uncategorized"
                stats["uncategorized_files"] += 1
            else:
                if sanitized_category not in stats["categories"]:
                    stats["categories"][sanitized_category] = 0
                stats["categories"][sanitized_category] += 1
            
            # Create category directory if it doesn't exist yet
            category_dir = os.path.join(target_dir, sanitized_category)
            safe_makedirs(category_dir)
            
            # Copy the file to the appropriate category directory
            output_path = os.path.join(category_dir, filename)
            shutil.copy2(input_path, output_path)
            logger.info(f"Copied {filename} to {sanitized_category} category")
            
        except Exception as e:
            logger.error(f"Unexpected error processing {filename}: {e}")
            stats["invalid_files"] += 1
    
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
    
    # Get absolute paths for all inputs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Resolve category map path
    if not os.path.isabs(args.category_map):
        # Potential paths to search for category map
        potential_paths = [
            os.path.join(parent_dir, "mapping", args.category_map),
            os.path.join(parent_dir, "mapping", os.path.basename(args.category_map)),
            os.path.join(parent_dir, args.category_map),
            os.path.join(script_dir, args.category_map)
        ]
        
        category_map_path = find_category_map(potential_paths)
        
        if category_map_path is None:
            logger.error(f"Could not find category map file: {args.category_map}")
            logger.error(f"Searched in: {', '.join(potential_paths)}")
            sys.exit(1)
    else:
        # Validate the provided absolute path
        try:
            category_map_path = validate_and_normalize_path(args.category_map, must_exist=True)
        except Exception as e:
            logger.error(f"Invalid category map path: {e}")
            sys.exit(1)

    # Normalize source directory
    try:
        source_dir = validate_and_normalize_path(args.source_dir, must_exist=True)
    except Exception as e:
        logger.error(f"Invalid source directory: {e}")
        sys.exit(1)

    # Normalize target directory
    try:
        target_dir = validate_and_normalize_path(args.target_dir)
        # Ensure target directory exists
        safe_makedirs(target_dir)
    except Exception as e:
        logger.error(f"Invalid target directory: {e}")
        sys.exit(1)

    # Organize the files
    logger.info(f"Starting organization process from {source_dir} to {target_dir}")
    stats = organize_psc_files(source_dir, target_dir, category_map_path)

    # Generate report if requested
    if args.generate_report:
        report_path = os.path.join(target_dir, "organization_report.json")
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Organization report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Error saving report to {report_path}: {e}")

    logger.info("Organization process completed successfully")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main script: {e}", exc_info=True)
        sys.exit(1)