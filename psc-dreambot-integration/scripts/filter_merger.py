import os
import json
import re
import logging
from typing import Dict, List, Any, Optional, Union

def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("filter_merger.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def repair_json(json_str: str) -> str:
    """
    Attempt to repair common JSON syntax errors.
    
    Args:
        json_str: The potentially malformed JSON string
        
    Returns:
        A repaired JSON string
    """
    # Remove JavaScript-style comments
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # Fix trailing commas in arrays and objects
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix missing commas between objects
    json_str = re.sub(r'}\s*{', '},{', json_str)
    
    # Fix ellipsis notation (often used in documentation)
    json_str = re.sub(r'"([^"]*)\.\.\."', r'"\1"', json_str)
    
    return json_str

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON file and return its contents, with repair attempts if needed."""
    try:
        # First try normal JSON loading
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {str(e)}. Attempting repair...")
                
                # Try repairing the JSON
                file.seek(0)
                content = file.read()
                repaired_content = repair_json(content)
                
                try:
                    # Try parsing the repaired content
                    return json.loads(repaired_content)
                except json.JSONDecodeError as e2:
                    # If that fails, try a more detailed repair approach
                    logger.warning(f"Simple repair failed: {str(e2)}. Attempting more detailed repair...")
                    
                    # Get the line and character position from the error
                    line_no = e2.lineno
                    col_no = e2.colno
                    
                    # Output context around the error for debugging
                    lines = repaired_content.split('\n')
                    start_line = max(0, line_no - 3)
                    end_line = min(len(lines), line_no + 3)
                    
                    logger.error(f"Error context (lines {start_line+1}-{end_line}):")
                    for i in range(start_line, end_line):
                        marker = ">>> " if i+1 == line_no else "    "
                        logger.error(f"{marker}{i+1}: {lines[i]}")
                        if i+1 == line_no:
                            logger.error(f"    {' ' * (col_no-1)}^")
                    
                    # If it's a specific error we can handle (like missing comma), try to fix it
                    if "Expecting ',' delimiter" in str(e2):
                        lines = repaired_content.split('\n')
                        problem_line = lines[line_no - 1]
                        fixed_line = problem_line[:col_no-1] + ',' + problem_line[col_no-1:]
                        lines[line_no - 1] = fixed_line
                        final_attempt = '\n'.join(lines)
                        
                        try:
                            return json.loads(final_attempt)
                        except:
                            logger.error(f"All repair attempts failed. Manual JSON fix required at line {line_no}, column {col_no}")
                            raise
                    
                    raise
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        raise

def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """Save data to a JSON file with pretty formatting."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved merged data to {file_path}")
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {str(e)}")
        raise

def get_nested_structure(data: Dict[str, Any], key_path: List[str], default: Any = None) -> Any:
    """
    Safely access nested dictionary elements with a path of keys.
    
    Args:
        data: The dictionary to access
        key_path: List of keys to traverse
        default: Default value if path doesn't exist
        
    Returns:
        The value at the specified path or the default value
    """
    current = data
    for key in key_path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

def validate_merged_library(merged_lib: Dict[str, Any]) -> bool:
    """
    Validate the structure of the merged library.
    
    Args:
        merged_lib: The merged library to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check essential sections
    if "filter_classes" not in merged_lib:
        logger.error("Merged library missing 'filter_classes' section")
        return False
    
    if "logical_operators" not in merged_lib:
        logger.warning("Merged library missing 'logical_operators' section")
    
    # Check filter classes structure
    filter_classes = merged_lib["filter_classes"]
    if not filter_classes or not isinstance(filter_classes, dict):
        logger.error("'filter_classes' must be a non-empty dictionary")
        return False
    
    # Check each filter class
    for class_name, class_data in filter_classes.items():
        if not isinstance(class_data, dict):
            logger.error(f"Filter class '{class_name}' must be a dictionary")
            return False
        
        if "filter_types" not in class_data:
            logger.warning(f"Filter class '{class_name}' is missing 'filter_types'")
            continue
            
        filter_types = class_data["filter_types"]
        if not isinstance(filter_types, dict):
            logger.error(f"'filter_types' in '{class_name}' must be a dictionary")
            return False
    
    return True

def merge_filter_libraries(filter_types_lib: Dict[str, Any], types_operators_lib: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge filter_types_library.json with types_operators.json into a comprehensive reference.
    
    Strategy:
    1. Start with the structure from filter_types_library.json
    2. Enhance each filter class with additional details from types_operators.json
    3. Add any missing filter classes from types_operators.json
    4. Ensure operator consistency across the merged library
    5. Add comprehensive examples from both libraries
    
    Args:
        filter_types_lib: The filter_types_library.json content
        types_operators_lib: The types_operators.json content
        
    Returns:
        A merged comprehensive filter library
    """
    # Create a deep copy of the filter_types_lib to avoid modifying the original
    merged_lib = json.loads(json.dumps(filter_types_lib))
    
    # Initialize filter_classes if it doesn't exist
    if "filter_classes" not in merged_lib:
        merged_lib["filter_classes"] = {}
    
    # Extract filter classes from both libraries
    filter_classes_original = merged_lib.get("filter_classes", {})
    types_operators_classes = {}
    
    # Handle different possible structures in types_operators_lib
    if "filter_classes" in types_operators_lib:
        types_operators_classes = types_operators_lib["filter_classes"]
    elif "classes" in types_operators_lib:
        types_operators_classes = types_operators_lib["classes"]
    elif "filters" in types_operators_lib:
        types_operators_classes = types_operators_lib["filters"]
    
    if not isinstance(types_operators_classes, dict):
        logger.warning(f"Cannot extract filter classes from types_operators_lib: expected dict, got {type(types_operators_classes)}")
        types_operators_classes = {}
    
    # Process each filter class in the types_operators library
    for class_name, class_data in types_operators_classes.items():
        if not isinstance(class_data, dict):
            logger.warning(f"Skipping filter class '{class_name}': expected dict, got {type(class_data)}")
            continue
            
        if class_name in filter_classes_original:
            # Class exists in both libraries - merge details
            logger.info(f"Merging details for filter class: {class_name}")
            
            # Get the existing class data
            existing_class = filter_classes_original[class_name]
            
            # Enhance description if available
            class_description = class_data.get("description") or class_data.get("class_description")
            if class_description and (
                "description" not in existing_class or 
                len(class_description) > len(existing_class["description"])
            ):
                existing_class["description"] = class_description
            
            # Process filter types
            if "filter_types" not in existing_class:
                existing_class["filter_types"] = {}
            
            existing_types = existing_class.get("filter_types", {})
            new_types = {}
            
            # Handle different structures
            if "filter_types" in class_data:
                new_types = class_data["filter_types"]
            elif "types" in class_data:
                new_types = class_data["types"]
                
            if not isinstance(new_types, dict):
                logger.warning(f"Skipping filter types for class '{class_name}': expected dict, got {type(new_types)}")
                continue
                
            # Merge filter types
            for type_name, type_data in new_types.items():
                if not isinstance(type_data, dict):
                    logger.warning(f"Skipping filter type '{type_name}' in class '{class_name}': expected dict, got {type(type_data)}")
                    continue
                    
                if type_name in existing_types:
                    # Type exists - enhance with additional details
                    
                    # Merge description
                    if "description" in type_data and (
                        "description" not in existing_types[type_name] or
                        len(type_data["description"]) > len(existing_types[type_name]["description"])
                    ):
                        existing_types[type_name]["description"] = type_data["description"]
                    
                    # Merge data_type if available
                    if "data_type" not in existing_types[type_name]:
                        if "data_type" in type_data:
                            existing_types[type_name]["data_type"] = type_data["data_type"]
                        elif "value_type" in type_data:
                            existing_types[type_name]["data_type"] = type_data["value_type"]
                    
                    # Merge valid operators
                    if "operators" in type_data or "valid_operators" in type_data:
                        operators_key = "valid_operators" if "valid_operators" in type_data else "operators"
                        new_operators = type_data[operators_key]
                        
                        if not isinstance(new_operators, list):
                            logger.warning(f"Skipping operators for type '{type_name}' in class '{class_name}': expected list, got {type(new_operators)}")
                        else:
                            if "valid_operators" not in existing_types[type_name]:
                                existing_types[type_name]["valid_operators"] = new_operators
                            else:
                                # Combine operators and remove duplicates
                                existing_operators = existing_types[type_name]["valid_operators"]
                                if isinstance(existing_operators, list):
                                    existing_types[type_name]["valid_operators"] = list(set(existing_operators + new_operators))
                    
                    # Merge example values
                    if "example_values" in type_data:
                        if "example_values" not in existing_types[type_name]:
                            existing_types[type_name]["example_values"] = type_data["example_values"]
                        else:
                            # Combine example values and remove duplicates if they are lists
                            existing_examples = existing_types[type_name]["example_values"]
                            new_examples = type_data["example_values"]
                            if isinstance(existing_examples, list) and isinstance(new_examples, list):
                                # Convert all elements to strings for comparison, then convert back
                                existing_str = [str(ex) for ex in existing_examples]
                                combined = existing_examples.copy()
                                for ex in new_examples:
                                    if str(ex) not in existing_str:
                                        combined.append(ex)
                                existing_types[type_name]["example_values"] = combined
                            elif isinstance(existing_examples, dict) and isinstance(new_examples, dict):
                                # Merge dictionaries
                                existing_examples.update(new_examples)
                else:
                    # Type doesn't exist - add it
                    logger.info(f"Adding new filter type {type_name} to class {class_name}")
                    existing_types[type_name] = type_data
        else:
            # Class doesn't exist - add it
            logger.info(f"Adding new filter class: {class_name}")
            filter_classes_original[class_name] = class_data
            
            # Ensure it has a filter_types attribute
            if "filter_types" not in filter_classes_original[class_name] and "types" in class_data:
                filter_classes_original[class_name]["filter_types"] = class_data["types"]
                del filter_classes_original[class_name]["types"]
                
            # Make sure class description is correctly labeled
            if "class_description" in filter_classes_original[class_name] and "description" not in filter_classes_original[class_name]:
                filter_classes_original[class_name]["description"] = filter_classes_original[class_name]["class_description"]
    
    # Process logical operators
    if "logical_operators" in types_operators_lib:
        if "logical_operators" not in merged_lib:
            # Handle case where types_operators logical_operators is a list
            if isinstance(types_operators_lib["logical_operators"], list):
                logger.info("Converting logical_operators from list to dictionary format")
                # Convert list to dictionary format expected by merged_lib
                logical_ops_dict = {}
                for op_name in types_operators_lib["logical_operators"]:
                    logical_ops_dict[op_name] = {
                        "description": f"Logical {op_name} operator",
                        "usage": f"Use when combining multiple conditions with {op_name} logic"
                    }
                merged_lib["logical_operators"] = logical_ops_dict
            else:
                # It's already a dictionary, so just assign it
                merged_lib["logical_operators"] = types_operators_lib["logical_operators"]
        else:
            # Merge logical operators - handle both list and dictionary formats
            if isinstance(types_operators_lib["logical_operators"], list):
                logger.info("Merging logical_operators from list format with existing dictionary")
                # Add any missing operators from the list
                for op_name in types_operators_lib["logical_operators"]:
                    if op_name not in merged_lib["logical_operators"]:
                        merged_lib["logical_operators"][op_name] = {
                            "description": f"Logical {op_name} operator",
                            "usage": f"Use when combining multiple conditions with {op_name} logic"
                        }
            else:
                # Handle dictionary format for logical operators
                if isinstance(types_operators_lib["logical_operators"], dict):
                    for op_name, op_data in types_operators_lib["logical_operators"].items():
                        if op_name not in merged_lib["logical_operators"]:
                            merged_lib["logical_operators"][op_name] = op_data
                        else:
                            # Enhance existing logical operator
                            existing_op = merged_lib["logical_operators"][op_name]
                            
                            # Merge description
                            if isinstance(op_data, dict) and "description" in op_data and (
                                "description" not in existing_op or
                                len(op_data["description"]) > len(existing_op["description"])
                            ):
                                existing_op["description"] = op_data["description"]
                            
                            # Merge usage
                            if isinstance(op_data, dict) and "usage" in op_data and "usage" not in existing_op:
                                existing_op["usage"] = op_data["usage"]
                            
                            # Merge example
                            if isinstance(op_data, dict) and "example" in op_data and "example" not in existing_op:
                                existing_op["example"] = op_data["example"]
                else:
                    logger.warning(f"Unexpected format for logical_operators: {type(types_operators_lib['logical_operators'])}")
    
    # Process examples if available
    if "examples" in types_operators_lib and isinstance(types_operators_lib["examples"], list):
        if "examples" not in merged_lib:
            merged_lib["examples"] = []
        
        # Add new examples
        for example in types_operators_lib["examples"]:
            if isinstance(example, dict):
                merged_lib["examples"].append(example)
    
    # Add or update combining_filters information
    if "combining_filters" in types_operators_lib:
        merged_lib["combining_filters"] = types_operators_lib["combining_filters"]
    
    # Add operator_mapping if available
    if "operator_mapping" in filter_types_lib and "operator_mapping" not in merged_lib:
        merged_lib["operator_mapping"] = filter_types_lib["operator_mapping"]
    
    # Add metadata about the merge
    merged_lib["metadata"] = {
        "version": "2.0",
        "description": "Comprehensive filter types library merged from filter_types_library.json and types_operators.json",
        "merge_date": "2025-03-09",
        "source_files": [
            "filter_types_library.json",
            "types_operators.json"
        ]
    }
    
    return merged_lib

def main():
    # Fixed absolute paths for the project
    base_dir = r"D:\RS_AI\pandemic-code"
    libraries_dir = os.path.join(base_dir, "psc-dreambot-integration", "libraries")
    
    # Define file paths
    filter_types_path = os.path.join(libraries_dir, "filter_types_library.json")
    types_operators_path = os.path.join(libraries_dir, "types_operators.json")
    output_path = os.path.join(libraries_dir, "filter_types_library_merged.json")
    
    # Log the paths
    logger.info(f"Filter types library path: {filter_types_path}")
    logger.info(f"Types operators library path: {types_operators_path}")
    logger.info(f"Output path: {output_path}")
    
    try:
        # Load the JSON files
        logger.info("Loading filter types library...")
        filter_types_lib = load_json_file(filter_types_path)
        logger.info(f"Successfully loaded filter types library with {len(filter_types_lib.get('filter_classes', {}))} filter classes")
        
        logger.info("Loading types operators library...")
        types_operators_lib = load_json_file(types_operators_path)
        
        # Log the structure of the loaded files
        logger.info(f"Types operators contains keys: {', '.join(types_operators_lib.keys())}")
        
        if "filters" in types_operators_lib:
            logger.info(f"Found {len(types_operators_lib['filters'])} filter classes in types_operators_lib")
            
        if "logical_operators" in types_operators_lib:
            logger.info(f"Logical operators in types_operators_lib has type: {type(types_operators_lib['logical_operators'])}")
            if isinstance(types_operators_lib["logical_operators"], list):
                logger.info(f"Found logical operators: {', '.join(types_operators_lib['logical_operators'])}")
        
        # Merge the libraries
        logger.info("Merging libraries...")
        merged_lib = merge_filter_libraries(filter_types_lib, types_operators_lib)
        
        # Validate the merged library
        logger.info("Validating merged library...")
        if validate_merged_library(merged_lib):
            logger.info("Merged library validation successful")
            
            # Save the merged library
            logger.info("Saving merged library...")
            save_json_file(merged_lib, output_path)
            
            logger.info("Successfully merged filter types libraries!")
            return True
        else:
            logger.error("Merged library validation failed")
            return False
        
    except Exception as e:
        logger.error(f"Error during merge process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Set up logging
    logger = setup_logging()
    logger.info("Starting filter types library merger script")
    
    # Run the main function
    success = main()
    
    if success:
        logger.info("Script completed successfully")
    else:
        logger.error("Script failed to complete")