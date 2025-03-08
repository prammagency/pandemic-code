#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PSC Standardizer - Tool for analyzing, standardizing, and validating PSC JSON files

This script processes Pandemic Script Creator (PSC) JSON files to:
1. Analyze the structure and report inconsistencies
2. Standardize the structure according to reference libraries
3. Validate the standardized structure
4. Generate DreamBot Java code from standardized PSC JSON

Usage:
    python psc_standardizer.py analyze --input-file <path> --output-file <path>
    python psc_standardizer.py standardize --input-file <path> --output-file <path>
    python psc_standardizer.py validate --input-file <path> --output-file <path>
    python psc_standardizer.py generate-code --input-file <path> --output-file <path>

Author: [Your Name]
Date: [Current Date]
"""

import argparse
import json
import os
import re
import sys
import copy
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple


class PSCStandardizer:
    """Main class for standardizing PSC JSON files."""
    
def __init__(self, libraries_dir: str = "../libraries"):
    """
    Initialize the standardizer with paths to the library files.
    
    Args:
        libraries_dir: Directory containing the library JSON files
    """
    # Use absolute path resolution based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    if os.path.isabs(libraries_dir):
        self.libraries_dir = Path(libraries_dir)
    else:
        self.libraries_dir = Path(os.path.join(parent_dir, "libraries"))
    
    self.libraries = {}
    self.load_libraries()
    
def load_libraries(self) -> None:
    """Load all standardized libraries from JSON files."""
    library_files = {
        "actions": "action_hierarchy_library.json",
        "filters": "filter_types_library.json",
        "control_flow": "control_flow_library.json",
        "properties": "property_values_library.json"
    }
    
    missing_libraries = []
    
    for lib_key, lib_file in library_files.items():
        try:
            lib_path = self.libraries_dir / lib_file
            with open(lib_path, 'r') as f:
                self.libraries[lib_key] = json.load(f)
            print(f"Loaded library: {lib_key} from {lib_path}")
        except FileNotFoundError:
            missing_libraries.append(lib_file)
            self.libraries[lib_key] = {}
        
        if missing_libraries:
            print(f"WARNING: Could not find the following library files in {self.libraries_dir}:")
            for lib_file in missing_libraries:
                print(f"  - {lib_file}")
            print("Standardization may be incomplete without these libraries.")
    
    def analyze_psc_json(self, input_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a PSC JSON file and generate a report of its structure.
        
        Args:
            input_file: Path to the PSC JSON file to analyze
            output_file: Optional path to save the analysis report
            
        Returns:
            Dictionary containing the analysis results
        """
        print(f"Analyzing PSC JSON file: {input_file}")
        
        try:
            with open(input_file, 'r') as f:
                psc_data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Input file not found: {input_file}")
            return {"error": "Input file not found"}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}")
            return {"error": f"Invalid JSON: {e}"}
        
        # Initialize analysis results
        analysis = {
            "filename": input_file,
            "action_count": 0,
            "unique_actions": set(),
            "action_categories": {},
            "nesting_depth": 0,
            "filter_usage": {},
            "missing_properties": [],
            "inconsistent_structures": [],
            "unknown_actions": [],
            "invalid_nestings": []
        }
        
        # Analyze script structure
        if isinstance(psc_data, list):
            analysis["structure_type"] = "list"
            for action in psc_data:
                self._analyze_action(action, None, analysis)
        elif isinstance(psc_data, dict):
            analysis["structure_type"] = "object"
            # Check for top-level script structure
            if "actions" in psc_data and isinstance(psc_data["actions"], list):
                analysis["script_info"] = {
                    "name": psc_data.get("name", ""),
                    "version": psc_data.get("version", ""),
                    "sleep": psc_data.get("sleep", "")
                }
                for action in psc_data["actions"]:
                    self._analyze_action(action, None, analysis)
            else:
                # Single action object
                self._analyze_action(psc_data, None, analysis)
        else:
            analysis["structure_type"] = "unknown"
            analysis["error"] = "Invalid PSC JSON structure"
        
        # Convert sets to lists for JSON serialization
        analysis["unique_actions"] = list(analysis["unique_actions"])
        
        # Generate summary
        analysis["summary"] = {
            "total_actions": analysis["action_count"],
            "unique_action_count": len(analysis["unique_actions"]),
            "max_nesting_depth": analysis["nesting_depth"],
            "missing_property_count": len(analysis["missing_properties"]),
            "inconsistent_structure_count": len(analysis["inconsistent_structures"]),
            "unknown_action_count": len(analysis["unknown_actions"]),
            "invalid_nesting_count": len(analysis["invalid_nestings"])
        }
        
        # Save analysis if output file is specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"Analysis saved to: {output_file}")
        
        return analysis
    
    def _analyze_action(self, action: Dict[str, Any], parent_action: Optional[Dict[str, Any]], analysis: Dict[str, Any], depth: int = 0) -> None:
        """
        Recursively analyze an action and its children.
        
        Args:
            action: The action to analyze
            parent_action: The parent action, or None if this is a root action
            analysis: The analysis results dictionary
            depth: Current nesting depth
        """
        analysis["action_count"] += 1
        
        # Check for missing ID
        if "id" not in action:
            analysis["inconsistent_structures"].append({
                "issue": "missing_id",
                "path": self._get_action_path(action, parent_action),
                "action": action
            })
            return
        
        action_id = action["id"]
        analysis["unique_actions"].add(action_id)
        
        # Update nesting depth
        analysis["nesting_depth"] = max(analysis["nesting_depth"], depth)
        
        # Check action against action library
        action_def = self._get_action_definition(action_id)
        if action_def:
            # Update category statistics
            category = action_def.get("category", "unknown")
            if category not in analysis["action_categories"]:
                analysis["action_categories"][category] = 0
            analysis["action_categories"][category] += 1
            
            # Check parent-child relationship
            if parent_action and "valid_parents" in action_def:
                valid_parents = action_def["valid_parents"]
                parent_id = parent_action["id"]
                
                # Handle wildcard patterns in valid_parents
                valid = False
                for pattern in valid_parents:
                    if pattern == "root":
                        continue  # Skip "root" pattern when checking parents
                    elif pattern == "*":
                        valid = True
                        break
                    elif pattern.endswith("*") and parent_id.startswith(pattern[:-1]):
                        valid = True
                        break
                    elif pattern == parent_id:
                        valid = True
                        break
                
                if not valid:
                    analysis["invalid_nestings"].append({
                        "action_id": action_id,
                        "parent_id": parent_id,
                        "path": self._get_action_path(action, parent_action),
                        "valid_parents": valid_parents
                    })
            
            # Check required properties
            if "properties" in action_def and "required" in action_def["properties"]:
                for req_prop in action_def["properties"]["required"]:
                    if "properties" not in action or req_prop not in action["properties"]:
                        analysis["missing_properties"].append({
                            "action_id": action_id,
                            "missing_property": req_prop,
                            "path": self._get_action_path(action, parent_action)
                        })
        else:
            # Unknown action
            analysis["unknown_actions"].append({
                "action_id": action_id,
                "path": self._get_action_path(action, parent_action)
            })
        
        # Analyze filter usage
        if "properties" in action:
            for prop_name, prop_value in action["properties"].items():
                if isinstance(prop_value, dict) and "class" in prop_value:
                    filter_class = prop_value["class"]
                    if filter_class not in analysis["filter_usage"]:
                        analysis["filter_usage"][filter_class] = 0
                    analysis["filter_usage"][filter_class] += 1
                    
                    # Check for inconsistent filter structure
                    if not self._is_valid_filter(prop_value):
                        analysis["inconsistent_structures"].append({
                            "issue": "invalid_filter",
                            "action_id": action_id,
                            "property": prop_name,
                            "filter": prop_value,
                            "path": self._get_action_path(action, parent_action)
                        })
        
        # Recursively analyze children
        if "children" in action and isinstance(action["children"], list):
            # Check if action can have children
            can_have_children = True
            if action_def and "valid_children" not in action_def:
                can_have_children = False
            
            if not can_have_children:
                analysis["inconsistent_structures"].append({
                    "issue": "invalid_children",
                    "action_id": action_id,
                    "path": self._get_action_path(action, parent_action),
                    "message": f"Action {action_id} should not have children"
                })
            
            for child in action["children"]:
                self._analyze_action(child, action, analysis, depth + 1)
    
    def _get_action_path(self, action: Dict[str, Any], parent_action: Optional[Dict[str, Any]]) -> str:
        """
        Generate a string representation of the action's path in the script.
        
        Args:
            action: The current action
            parent_action: The parent action, or None if this is a root action
            
        Returns:
            String representation of the action's path
        """
        if parent_action is None:
            return f"root/{action.get('id', 'unknown')}"
        else:
            return f"{self._get_action_path(parent_action, None)}/{action.get('id', 'unknown')}"
    
    def _get_action_definition(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the definition of an action from the action library.
        
        Args:
            action_id: The ID of the action
            
        Returns:
            The action definition, or None if not found
        """
        if "actions" not in self.libraries or "actions" not in self.libraries["actions"]:
            return None
        
        return self.libraries["actions"]["actions"].get(action_id)
    
    def _is_valid_filter(self, filter_value: Dict[str, Any]) -> bool:
        """
        Check if a filter structure is valid according to the filter library.
        
        Args:
            filter_value: The filter structure to check
            
        Returns:
            True if the filter is valid, False otherwise
        """
        if not isinstance(filter_value, dict) or "class" not in filter_value:
            return False
        
        filter_class = filter_value["class"]
        
        # Check if filter class exists
        if "filter_classes" not in self.libraries["filters"] or filter_class not in self.libraries["filters"]["filter_classes"]:
            return False
        
        # For simple filter (NONE logic)
        if "logic" not in filter_value or filter_value["logic"] == "NONE":
            return "type" in filter_value and "operator" in filter_value and "value" in filter_value
        
        # For complex filter (AND/OR logic)
        if filter_value.get("logic") in ["AND", "OR"]:
            return "conditions" in filter_value and isinstance(filter_value["conditions"], list)
        
        return False
    
    def standardize_psc_json(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        Standardize a PSC JSON file according to the reference libraries.
        
        Args:
            input_file: Path to the PSC JSON file to standardize
            output_file: Path to save the standardized JSON
            
        Returns:
            Dictionary containing standardization results
        """
        print(f"Standardizing PSC JSON file: {input_file}")
        
        try:
            with open(input_file, 'r') as f:
                psc_data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Input file not found: {input_file}")
            return {"error": "Input file not found"}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}")
            return {"error": f"Invalid JSON: {e}"}
        
        # Initialize standardization results
        results = {
            "input_file": input_file,
            "output_file": output_file,
            "original_action_count": 0,
            "standardized_action_count": 0,
            "fixes": {
                "missing_properties_added": 0,
                "filter_structures_normalized": 0,
                "nesting_fixed": 0,
                "dreambot_mappings_added": 0
            },
            "warnings": []
        }
        
        # Standardize data structure
        std_data = copy.deepcopy(psc_data)
        
        if isinstance(std_data, list):
            # List of actions at root
            standardized_actions = []
            for action in std_data:
                standardized_action = self._standardize_action(action, None, results)
                if standardized_action:
                    standardized_actions.append(standardized_action)
            std_data = standardized_actions
        
        elif isinstance(std_data, dict):
            # Check for top-level script structure
            if "actions" in std_data and isinstance(std_data["actions"], list):
                # Script with metadata and actions list
                standardized_actions = []
                for action in std_data["actions"]:
                    standardized_action = self._standardize_action(action, None, results)
                    if standardized_action:
                        standardized_actions.append(standardized_action)
                std_data["actions"] = standardized_actions
                
                # Ensure required script properties exist
                if "name" not in std_data:
                    std_data["name"] = "Standardized Script"
                    results["warnings"].append("Added missing script name")
                
                if "version" not in std_data:
                    std_data["version"] = 1.0
                    results["warnings"].append("Added missing script version")
                
                if "sleep" not in std_data:
                    std_data["sleep"] = "500"
                    results["warnings"].append("Added missing script sleep value")
            else:
                # Single action object
                std_data = self._standardize_action(std_data, None, results)
        
        # Save standardized data
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(std_data, f, indent=2)
        
        print(f"Standardized JSON saved to: {output_file}")
        
        # Add summary to results
        results["summary"] = {
            "fixes_applied": sum(results["fixes"].values()),
            "warnings_count": len(results["warnings"])
        }
        
        return results
    
    def _standardize_action(self, action: Dict[str, Any], parent_action: Optional[Dict[str, Any]], results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Standardize an action according to the reference libraries.
        
        Args:
            action: The action to standardize
            parent_action: The parent action, or None if this is a root action
            results: Dictionary to accumulate standardization results
            
        Returns:
            Standardized action, or None if the action should be removed
        """
        results["original_action_count"] += 1
        
        # Skip action if it doesn't have an ID
        if "id" not in action:
            results["warnings"].append(f"Skipped action with missing ID: {action}")
            return None
        
        action_id = action["id"]
        
        # Get action definition from library
        action_def = self._get_action_definition(action_id)
        if not action_def:
            results["warnings"].append(f"Unknown action ID: {action_id}")
            
            # Create basic definition for unknown action
            action_def = {
                "category": "unknown",
                "description": f"Unknown action: {action_id}",
                "can_be_root": True,
                "valid_parents": ["root", "*"],
                "properties": {
                    "required": [],
                    "optional": []
                }
            }
        
        # Create standardized action copy
        std_action = copy.deepcopy(action)
        
        # Add category if missing
        if "category" not in std_action and "category" in action_def:
            std_action["category"] = action_def["category"]
        
        # Ensure properties exist
        if "properties" not in std_action:
            std_action["properties"] = {}
        
        # Add required properties if missing
        if "properties" in action_def and "required" in action_def["properties"]:
            for prop_name in action_def["properties"]["required"]:
                if prop_name not in std_action["properties"]:
                    # Find default value for this property
                    default_value = self._get_default_property_value(prop_name)
                    std_action["properties"][prop_name] = default_value
                    results["fixes"]["missing_properties_added"] += 1
        
        # Standardize filter structures
        for prop_name, prop_value in std_action["properties"].items():
            if isinstance(prop_value, dict) and "class" in prop_value:
                normalized_filter = self._normalize_filter_structure(prop_value)
                if normalized_filter != prop_value:
                    std_action["properties"][prop_name] = normalized_filter
                    results["fixes"]["filter_structures_normalized"] += 1
        
        # Add DreamBot API mapping if missing
        if "dreambot_api_mapping" not in std_action and "dreambot_api_mapping" in action_def:
            std_action["dreambot_api_mapping"] = action_def["dreambot_api_mapping"]
            results["fixes"]["dreambot_mappings_added"] += 1
        
        # Process children recursively
        if "children" in std_action and isinstance(std_action["children"], list):
            can_have_children = True
            if "valid_children" not in action_def:
                can_have_children = False
            
            if can_have_children:
                standardized_children = []
                for child in std_action["children"]:
                    standardized_child = self._standardize_action(child, std_action, results)
                    if standardized_child:
                        standardized_children.append(standardized_child)
                std_action["children"] = standardized_children
            else:
                # Remove invalid children
                del std_action["children"]
                results["fixes"]["nesting_fixed"] += 1
                results["warnings"].append(f"Removed invalid children from action: {action_id}")
        
        results["standardized_action_count"] += 1
        return std_action
    
    def _normalize_filter_structure(self, filter_value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a filter structure according to the filter library.
        
        Args:
            filter_value: The filter structure to normalize
            
        Returns:
            Normalized filter structure
        """
        # Make a copy to avoid modifying the original
        normalized = copy.deepcopy(filter_value)
        
        filter_class = normalized["class"]
        
        # Get filter class definition from library
        filter_class_def = None
        if "filter_classes" in self.libraries["filters"]:
            filter_class_def = self.libraries["filters"]["filter_classes"].get(filter_class)
        
        if not filter_class_def:
            # Unknown filter class, can't properly normalize
            if "logic" not in normalized:
                normalized["logic"] = "NONE"
            return normalized
        
        # Handle simple filter (NONE logic)
        if "logic" not in normalized or normalized["logic"] == "NONE":
            normalized["logic"] = "NONE"
            
            # Ensure type is present
            if "type" not in normalized:
                # Use first available type from filter class
                filter_types = filter_class_def.get("filter_types", {})
                if filter_types:
                    first_type = next(iter(filter_types))
                    normalized["type"] = first_type
            
            # Ensure operator is present
            if "operator" not in normalized and "type" in normalized:
                filter_type = normalized["type"]
                filter_type_def = filter_class_def.get("filter_types", {}).get(filter_type, {})
                
                if "valid_operators" in filter_type_def and filter_type_def["valid_operators"]:
                    # Use first valid operator
                    normalized["operator"] = filter_type_def["valid_operators"][0]
            
            # Ensure value is present
            if "value" not in normalized and "type" in normalized:
                filter_type = normalized["type"]
                filter_type_def = filter_class_def.get("filter_types", {}).get(filter_type, {})
                
                if "example_values" in filter_type_def and filter_type_def["example_values"]:
                    # Use first example value
                    normalized["value"] = filter_type_def["example_values"][0]
        
        # Handle complex filter (AND/OR logic)
        elif normalized["logic"] in ["AND", "OR"]:
            if "conditions" not in normalized or not isinstance(normalized["conditions"], list):
                # Convert simple filter to complex filter
                if "type" in normalized and "operator" in normalized and "value" in normalized:
                    condition = {
                        "type": normalized["type"],
                        "operator": normalized["operator"],
                        "value": normalized["value"]
                    }
                    normalized["conditions"] = [condition]
                    for key in ["type", "operator", "value"]:
                        if key in normalized:
                            del normalized[key]
                else:
                    # Initialize empty conditions list
                    normalized["conditions"] = []
        
        return normalized
    
    def _get_default_property_value(self, property_name: str) -> Any:
        """
        Get a default value for a property from the property library.
        
        Args:
            property_name: Name of the property
            
        Returns:
            Default value for the property
        """
        if "common_properties" not in self.libraries["properties"]:
            return ""
        
        prop_def = self.libraries["properties"]["common_properties"].get(property_name)
        if not prop_def:
            return ""
        
        if "examples" in prop_def and prop_def["examples"]:
            # Use first example as default
            return prop_def["examples"][0]
        
        # Default values based on property type
        prop_type = prop_def.get("type", "string")
        if "numeric" in prop_type:
            return 0
        elif "boolean" in prop_type:
            return False
        elif "coordinate" in prop_type:
            return {"x": 0, "y": 0, "z": 0}
        else:
            return ""
    
    def validate_psc_json(self, input_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a PSC JSON file against the reference libraries.
        
        Args:
            input_file: Path to the PSC JSON file to validate
            output_file: Optional path to save the validation report
            
        Returns:
            Dictionary containing validation results
        """
        print(f"Validating PSC JSON file: {input_file}")
        
        try:
            with open(input_file, 'r') as f:
                psc_data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Input file not found: {input_file}")
            return {"error": "Input file not found"}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}")
            return {"error": f"Invalid JSON: {e}"}
        
        # Initialize validation results
        results = {
            "input_file": input_file,
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Perform schema validation
        schema_errors = self._validate_schema(psc_data)
        if schema_errors:
            results["valid"] = False
            results["errors"].extend(schema_errors)
        
        # Perform semantic validation
        semantic_errors = self._validate_semantics(psc_data)
        if semantic_errors:
            results["valid"] = False
            results["errors"].extend(semantic_errors)
        
        # Save validation results if output file is specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Validation report saved to: {output_file}")
        
        return results
    
    def _validate_schema(self, psc_data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate the schema of PSC JSON data.
        
        Args:
            psc_data: The PSC JSON data to validate
            
        Returns:
            List of schema validation errors
        """
        errors = []
        
        # Basic structure validation
        if isinstance(psc_data, dict):
            # Check for top-level script structure
            if "actions" in psc_data:
                if not isinstance(psc_data["actions"], list):
                    errors.append({
                        "type": "schema",
                        "path": "root.actions",
                        "message": "actions must be an array"
                    })
                else:
                    # Validate each action in the actions array
                    for i, action in enumerate(psc_data["actions"]):
                        action_errors = self._validate_action_schema(action, f"root.actions[{i}]")
                        errors.extend(action_errors)
            else:
                # Single action object
                action_errors = self._validate_action_schema(psc_data, "root")
                errors.extend(action_errors)
        
        elif isinstance(psc_data, list):
            # List of actions at root
            for i, action in enumerate(psc_data):
                action_errors = self._validate_action_schema(action, f"root[{i}]")
                errors.extend(action_errors)
        
        else:
            errors.append({
                "type": "schema",
                "path": "root",
                "message": "PSC JSON must be an object or an array"
            })
        
        return errors
    
    def _validate_action_schema(self, action: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
        """
        Validate the schema of a single action.
        
        Args:
            action: The action to validate
            path: JSON path to the action
            
        Returns:
            List of schema validation errors
        """
        errors = []
        
        # Check action is an object
        if not isinstance(action, dict):
            errors.append({
                "type": "schema",
                "path": path,
                "message": "Action must be an object"
            })
            return errors
        
        # Check for required id field
        if "id" not in action:
            errors.append({
                "type": "schema",
                "path": f"{path}.id",
                "message": "Action must have an id"
            })
        elif not isinstance(action["id"], str):
            errors.append({
                "type": "schema",
                "path": f"{path}.id",
                "message": "Action id must be a string"
            })
        
        # Check properties structure if present
        if "properties" in action:
            if not isinstance(action["properties"], dict):
                errors.append({
                    "type": "schema",
                    "path": f"{path}.properties",
                    "message": "properties must be an object"
                })
            else:
                # Validate filter structures
                for prop_name, prop_value in action["properties"].items():
                    if isinstance(prop_value, dict) and "class" in prop_value:
                        filter_errors = self._validate_filter_schema(prop_value, f"{path}.properties.{prop_name}")
                        errors.extend(filter_errors)
        
        # Check children structure if present
        if "children" in action:
            if not isinstance(action["children"], list):
                errors.append({
                    "type": "schema",
                    "path": f"{path}.children",
                    "message": "children must be an array"
                })
            else:
                # Validate each child action
                for i, child in enumerate(action["children"]):
                    child_errors = self._validate_action_schema(child, f"{path}.children[{i}]")
                    errors.extend(child_errors)
        
        return errors
    
    def _validate_filter_schema(self, filter_value: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
        """
        Validate the schema of a filter structure.
        
        Args:
            filter_value: The filter structure to validate
            path: JSON path to the filter
            
        Returns:
            List of schema validation errors
        """
        errors = []
        
        # Check required class field
        if "class" not in filter_value:
            errors.append({
                "type": "schema",
                "path": f"{path}.class",
                "message": "Filter must have a class"
            })
        elif not isinstance(filter_value["class"], str):
            errors.append({
                "type": "schema",
                "path": f"{path}.class",
                "message": "Filter class must be a string"
            })
        
        # Check logic field
        if "logic" not in filter_value:
            errors.append({
                "type": "schema",
                "path": f"{path}.logic",
                "message": "Filter must have a logic field"
            })
        elif filter_value["logic"] not in ["NONE", "AND", "OR"]:
            errors.append({
                "type": "schema",
                "path": f"{path}.logic",
                "message": "Filter logic must be NONE, AND, or OR"
            })
        
        # Check fields based on logic
        if "logic" in filter_value:
            if filter_value["logic"] == "NONE":
                # Simple filter
                required_fields = ["type", "operator", "value"]
                for field in required_fields:
                    if field not in filter_value:
                        errors.append({
                            "type": "schema",
                            "path": f"{path}.{field}",
                            "message": f"Simple filter must have a {field} field"
                        })
            
            elif filter_value["logic"] in ["AND", "OR"]:
                # Complex filter
                if "conditions" not in filter_value:
                    errors.append({
                        "type": "schema",
                        "path": f"{path}.conditions",
                        "message": "Complex filter must have a conditions array"
                    })
                elif not isinstance(filter_value["conditions"], list):
                    errors.append({
                        "type": "schema",
                        "path": f"{path}.conditions",
                        "message": "conditions must be an array"
                    })
                else:
                    # Validate each condition
                    for i, condition in enumerate(filter_value["conditions"]):
                        if not isinstance(condition, dict):
                            errors.append({
                                "type": "schema",
                                "path": f"{path}.conditions[{i}]",
                                "message": "Filter condition must be an object"
                            })
                        else:
                            for field in ["type", "operator", "value"]:
                                if field not in condition:
                                    errors.append({
                                        "type": "schema",
                                        "path": f"{path}.conditions[{i}].{field}",
                                        "message": f"Filter condition must have a {field} field"
                                    })
        
        return errors
    
    def _validate_semantics(self, psc_data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate the semantics of PSC JSON data.
        
        Args:
            psc_data: The PSC JSON data to validate
            
        Returns:
            List of semantic validation errors
        """
        errors = []
        
        # Set up validation context
        context = {
            "variables": set(),  # Track declared variables
            "lists": set(),      # Track declared lists
            "timers": set()      # Track declared timers
        }
        
        # Validate actions based on structure
        if isinstance(psc_data, dict) and "actions" in psc_data:
            # Script with actions list
            for i, action in enumerate(psc_data["actions"]):
                action_errors = self._validate_action_semantics(action, None, context, f"root.actions[{i}]")
                errors.extend(action_errors)
        
        elif isinstance(psc_data, list):
            # List of actions at root
            for i, action in enumerate(psc_data):
                action_errors = self._validate_action_semantics(action, None, context, f"root[{i}]")
                errors.extend(action_errors)
        
        elif isinstance(psc_data, dict):
            # Single action object
            action_errors = self._validate_action_semantics(psc_data, None, context, "root")
            errors.extend(action_errors)
        
        return errors
    
    def _validate_action_semantics(self, action: Dict[str, Any], parent_action: Optional[Dict[str, Any]], 
                                  context: Dict[str, Set[str]], path: str) -> List[Dict[str, Any]]:
        """
        Validate the semantics of a single action.
        
        Args:
            action: The action to validate
            parent_action: The parent action, or None if this is a root action
            context: Validation context (variables, lists, etc.)
            path: JSON path to the action
            
        Returns:
            List of semantic validation errors
        """
        errors = []
        
        # Skip validation if action doesn't have an ID
        if "id" not in action:
            return errors
        
        action_id = action["id"]
        
        # Get action definition from library
        action_def = self._get_action_definition(action_id)
        if not action_def:
            errors.append({
                "type": "semantic",
                "path": f"{path}.id",
                "message": f"Unknown action ID: {action_id}"
            })
        else:
            # Validate parent-child relationship
            if parent_action and "valid_parents" in action_def:
                valid_parents = action_def["valid_parents"]
                parent_id = parent_action["id"]
                
                # Handle wildcard patterns in valid_parents
                valid = False
                for pattern in valid_parents:
                    if pattern == "root":
                        continue  # Skip "root" pattern when checking parents
                    elif pattern == "*":
                        valid = True
                        break
                    elif pattern.endswith("*") and parent_id.startswith(pattern[:-1]):
                        valid = True
                        break
                    elif pattern == parent_id:
                        valid = True
                        break
                
                if not valid:
                    errors.append({
                        "type": "semantic",
                        "path": path,
                        "message": f"Action {action_id} cannot be a child of {parent_id}"
                    })
            
            # Validate can_be_root if this is a root action
            if parent_action is None and "can_be_root" in action_def and not action_def["can_be_root"]:
                errors.append({
                    "type": "semantic",
                    "path": path,
                    "message": f"Action {action_id} cannot be a root action"
                })
            
            # Validate required properties
            if "properties" in action_def and "required" in action_def["properties"]:
                for req_prop in action_def["properties"]["required"]:
                    if "properties" not in action or req_prop not in action["properties"]:
                        errors.append({
                            "type": "semantic",
                            "path": f"{path}.properties",
                            "message": f"Missing required property: {req_prop}"
                        })
        
        # Validate variable/list/timer operations and references
        if "properties" in action:
            # Track variable declarations
            if action_id == "SET_VARIABLE" and "Variable name" in action["properties"]:
                var_name = action["properties"]["Variable name"]
                context["variables"].add(var_name)
            
            # Track list declarations
            if action_id == "CREATE_LIST" and "List name" in action["properties"]:
                list_name = action["properties"]["List name"]
                context["lists"].add(list_name)
            
            # Track timer declarations
            if action_id == "CREATE_TIMER" and "Timer name" in action["properties"]:
                timer_name = action["properties"]["Timer name"]
                context["timers"].add(timer_name)
            
            # Validate variable references
            for prop_name, prop_value in action["properties"].items():
                if prop_name == "Variable name" and action_id != "SET_VARIABLE" and prop_value not in context["variables"]:
                    errors.append({
                        "type": "semantic",
                        "path": f"{path}.properties.{prop_name}",
                        "message": f"Reference to undefined variable: {prop_value}"
                    })
                
                # Validate list references
                if prop_name == "List name" and action_id not in ["CREATE_LIST"] and prop_value not in context["lists"]:
                    errors.append({
                        "type": "semantic",
                        "path": f"{path}.properties.{prop_name}",
                        "message": f"Reference to undefined list: {prop_value}"
                    })
                
                # Validate timer references
                if prop_name == "Timer name" and action_id not in ["CREATE_TIMER"] and prop_value not in context["timers"]:
                    errors.append({
                        "type": "semantic",
                        "path": f"{path}.properties.{prop_name}",
                        "message": f"Reference to undefined timer: {prop_value}"
                    })
                
                # Validate filter structures
                if isinstance(prop_value, dict) and "class" in prop_value:
                    filter_errors = self._validate_filter_semantics(prop_value, context, f"{path}.properties.{prop_name}")
                    errors.extend(filter_errors)
        
        # Validate children
        if "children" in action and isinstance(action["children"], list):
            # Check if action can have children
            can_have_children = True
            if action_def and "valid_children" not in action_def:
                can_have_children = False
            
            if not can_have_children:
                errors.append({
                    "type": "semantic",
                    "path": f"{path}.children",
                    "message": f"Action {action_id} should not have children"
                })
            
            # Validate minimum children count
            if action_def and "min_children" in action_def and len(action["children"]) < action_def["min_children"]:
                errors.append({
                    "type": "semantic",
                    "path": f"{path}.children",
                    "message": f"Action {action_id} requires at least {action_def['min_children']} children"
                })
            
            # Validate each child
            for i, child in enumerate(action["children"]):
                child_errors = self._validate_action_semantics(child, action, context, f"{path}.children[{i}]")
                errors.extend(child_errors)
        
        return errors
    
    def _validate_filter_semantics(self, filter_value: Dict[str, Any], context: Dict[str, Set[str]], path: str) -> List[Dict[str, Any]]:
        """
        Validate the semantics of a filter structure.
        
        Args:
            filter_value: The filter structure to validate
            context: Validation context (variables, lists, etc.)
            path: JSON path to the filter
            
        Returns:
            List of semantic validation errors
        """
        errors = []
        
        filter_class = filter_value.get("class")
        
        # Check if filter class exists in library
        if "filter_classes" not in self.libraries["filters"] or filter_class not in self.libraries["filters"]["filter_classes"]:
            errors.append({
                "type": "semantic",
                "path": f"{path}.class",
                "message": f"Unknown filter class: {filter_class}"
            })
            return errors
        
        filter_class_def = self.libraries["filters"]["filter_classes"][filter_class]
        
        # Validate simple filter (NONE logic)
        if "logic" in filter_value and filter_value["logic"] == "NONE":
            if "type" in filter_value:
                filter_type = filter_value["type"]
                
                # Check if type exists for this filter class
                if "filter_types" not in filter_class_def or filter_type not in filter_class_def["filter_types"]:
                    errors.append({
                        "type": "semantic",
                        "path": f"{path}.type",
                        "message": f"Unknown filter type {filter_type} for class {filter_class}"
                    })
                else:
                    filter_type_def = filter_class_def["filter_types"][filter_type]
                    
                    # Validate operator
                    if "operator" in filter_value:
                        operator = filter_value["operator"]
                        if "valid_operators" in filter_type_def and operator not in filter_type_def["valid_operators"]:
                            errors.append({
                                "type": "semantic",
                                "path": f"{path}.operator",
                                "message": f"Invalid operator {operator} for filter type {filter_type}"
                            })
                    
                    # Validate value
                    if "value" in filter_value:
                        value = filter_value["value"]
                        
                        # Check for variable references
                        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                            var_name = value[2:-1]
                            if var_name not in context["variables"]:
                                errors.append({
                                    "type": "semantic",
                                    "path": f"{path}.value",
                                    "message": f"Reference to undefined variable: {var_name}"
                                })
                        
                        # Check for list references
                        if "operator" in filter_value and filter_value["operator"] == "IS_IN_LIST" and isinstance(value, str):
                            if value not in context["lists"]:
                                errors.append({
                                    "type": "semantic",
                                    "path": f"{path}.value",
                                    "message": f"Reference to undefined list: {value}"
                                })
        
        # Validate complex filter (AND/OR logic)
        elif "logic" in filter_value and filter_value["logic"] in ["AND", "OR"]:
            if "conditions" in filter_value and isinstance(filter_value["conditions"], list):
                for i, condition in enumerate(filter_value["conditions"]):
                    if not isinstance(condition, dict):
                        continue
                    
                    # Validate condition type
                    if "type" in condition:
                        condition_type = condition["type"]
                        
                        # Check if type exists for this filter class
                        if "filter_types" not in filter_class_def or condition_type not in filter_class_def["filter_types"]:
                            errors.append({
                                "type": "semantic",
                                "path": f"{path}.conditions[{i}].type",
                                "message": f"Unknown filter type {condition_type} for class {filter_class}"
                            })
                        else:
                            filter_type_def = filter_class_def["filter_types"][condition_type]
                            
                            # Validate operator
                            if "operator" in condition:
                                operator = condition["operator"]
                                if "valid_operators" in filter_type_def and operator not in filter_type_def["valid_operators"]:
                                    errors.append({
                                        "type": "semantic",
                                        "path": f"{path}.conditions[{i}].operator",
                                        "message": f"Invalid operator {operator} for filter type {condition_type}"
                                    })
                            
                            # Validate value
                            if "value" in condition:
                                value = condition["value"]
                                
                                # Check for variable references
                                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                                    var_name = value[2:-1]
                                    if var_name not in context["variables"]:
                                        errors.append({
                                            "type": "semantic",
                                            "path": f"{path}.conditions[{i}].value",
                                            "message": f"Reference to undefined variable: {var_name}"
                                        })
                                
                                # Check for list references
                                if "operator" in condition and condition["operator"] == "IS_IN_LIST" and isinstance(value, str):
                                    if value not in context["lists"]:
                                        errors.append({
                                            "type": "semantic",
                                            "path": f"{path}.conditions[{i}].value",
                                            "message": f"Reference to undefined list: {value}"
                                        })
        
        return errors
    
    def generate_dreambot_code(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        Generate DreamBot Java code from a standardized PSC JSON file.
        
        Args:
            input_file: Path to the standardized PSC JSON file
            output_file: Path to save the generated Java code
            
        Returns:
            Dictionary containing code generation results
        """
        print(f"Generating DreamBot code from: {input_file}")
        
        try:
            with open(input_file, 'r') as f:
                psc_data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Input file not found: {input_file}")
            return {"error": "Input file not found"}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}")
            return {"error": f"Invalid JSON: {e}"}
        
        # Initialize code generation results
        results = {
            "input_file": input_file,
            "output_file": output_file,
            "action_count": 0,
            "warnings": []
        }
        
        # Generate script name from input file if not available
        script_name = "GeneratedScript"
        if isinstance(psc_data, dict) and "name" in psc_data:
            script_name = psc_data["name"]
        else:
            script_name = os.path.splitext(os.path.basename(input_file))[0]
            script_name = re.sub(r'[^a-zA-Z0-9]', '', script_name)
            if not script_name:
                script_name = "GeneratedScript"
        
        # Ensure first letter is uppercase (for Java class name)
        script_name = script_name[0].upper() + script_name[1:]
        
        # Generate Java code
        java_code = self._generate_script_class(script_name, psc_data, results)
        
        # Save generated code
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(java_code)
        
        print(f"DreamBot Java code saved to: {output_file}")
        
        # Add summary to results
        results["summary"] = {
            "script_name": script_name,
            "action_count": results["action_count"],
            "warnings_count": len(results["warnings"])
        }
        
        return results
    
    def _generate_script_class(self, class_name: str, psc_data: Union[List[Dict[str, Any]], Dict[str, Any]], 
                              results: Dict[str, Any]) -> str:
        """
        Generate a complete DreamBot script class from PSC data.
        
        Args:
            class_name: Name of the Java class to generate
            psc_data: The PSC JSON data to convert to Java code
            results: Dictionary to accumulate code generation results
            
        Returns:
            Complete Java class as a string
        """
        # Initialize imports set
        imports = set([
            "org.dreambot.api.methods.Calculations",
            "org.dreambot.api.methods.container.impl.Inventory",
            "org.dreambot.api.methods.container.impl.bank.Bank",
            "org.dreambot.api.methods.container.impl.equipment.Equipment",
            "org.dreambot.api.methods.dialogues.Dialogues",
            "org.dreambot.api.methods.filter.Filter",
            "org.dreambot.api.methods.input.Keyboard",
            "org.dreambot.api.methods.interactive.GameObjects",
            "org.dreambot.api.methods.interactive.NPCs",
            "org.dreambot.api.methods.interactive.Players",
            "org.dreambot.api.methods.item.GroundItems",
            "org.dreambot.api.methods.map.Area",
            "org.dreambot.api.methods.map.Tile",
            "org.dreambot.api.methods.skills.Skill",
            "org.dreambot.api.methods.skills.Skills",
            "org.dreambot.api.methods.walking.impl.Walking",
            "org.dreambot.api.methods.widget.Widgets",
            "org.dreambot.api.script.AbstractScript",
            "org.dreambot.api.script.Category",
            "org.dreambot.api.script.ScriptManifest",
            "org.dreambot.api.wrappers.items.Item",
            "org.dreambot.api.wrappers.interactive.GameObject",
            "org.dreambot.api.wrappers.interactive.NPC",
            "org.dreambot.api.wrappers.items.GroundItem",
            "java.util.HashMap",
            "java.util.Map",
            "java.util.ArrayList",
            "java.util.List",
            "java.util.Random"
        ])
        
        # Get script information
        script_info = {
            "name": class_name,
            "description": "Generated from PSC",
            "version": 1.0,
            "sleep": 500  # Default sleep time in milliseconds
        }
        
        if isinstance(psc_data, dict):
            if "name" in psc_data:
                script_info["name"] = psc_data["name"]
            if "version" in psc_data:
                script_info["version"] = psc_data["version"]
            if "sleep" in psc_data:
                try:
                    script_info["sleep"] = int(psc_data["sleep"])
                except ValueError:
                    pass
        
        # Start building the Java class
        code = []
        
        # Add imports
        for import_stmt in sorted(imports):
            code.append(f"import {import_stmt};")
        code.append("")
        
        # Add class declaration and ScriptManifest
        code.append(f'@ScriptManifest(name = "{script_info["name"]}", description = "{script_info["description"]}", author = "PSC", version = {script_info["version"]}, category = Category.MISC)')
        code.append(f"public class {class_name} extends AbstractScript {{")
        code.append("")
        
        # Add class fields
        code.append("    // Script variables")
        code.append("    private Map<String, Object> variables = new HashMap<>();")
        code.append("    private Map<String, List<Object>> lists = new HashMap<>();")
        code.append("    private Map<String, Long> timers = new HashMap<>();")
        code.append("    private Random random = new Random();")
        code.append("    private boolean firstRun = true;")
        code.append("")
        
        # Add onStart method
        code.append("    @Override")
        code.append("    public void onStart() {")
        code.append("        log(\"Starting PSC Generated Script\");")
        code.append("    }")
        code.append("")
        
        # Add onLoop method
        code.append("    @Override")
        code.append("    public int onLoop() {")
        
        # Generate action code
        if isinstance(psc_data, dict) and "actions" in psc_data and isinstance(psc_data["actions"], list):
            # Script with actions list
            for action in psc_data["actions"]:
                code.extend(self._generate_action_code(action, results, 8))
        elif isinstance(psc_data, list):
            # List of actions at root
            for action in psc_data:
                code.extend(self._generate_action_code(action, results, 8))
        elif isinstance(psc_data, dict):
            # Single action object
            code.extend(self._generate_action_code(psc_data, results, 8))
        
        # End onLoop method with random sleep
        code.append("")
        code.append(f"        return Calculations.random({script_info['sleep'] - 100}, {script_info['sleep'] + 100});")
        code.append("    }")
        code.append("")
        
        # Add helper methods
        code.extend(self._generate_helper_methods())
        
        # Add onExit method
        code.append("    @Override")
        code.append("    public void onExit() {")
        code.append("        log(\"Script finished!\");")
        code.append("    }")
        code.append("}")
        
        # Join and return the complete code
        return "\n".join(code)
    
    def _generate_action_code(self, action: Dict[str, Any], results: Dict[str, Any], indent: int = 0) -> List[str]:
        """
        Generate Java code for a single action.
        
        Args:
            action: The action to generate code for
            results: Dictionary to accumulate code generation results
            indent: Indentation level in spaces
            
        Returns:
            List of lines of Java code
        """
        results["action_count"] += 1
        
        if "id" not in action:
            return [" " * indent + "// Missing action ID"]
        
        action_id = action["id"]
        code_lines = []
        
        # Add comment for the action
        code_lines.append(" " * indent + f"// Action: {action_id}")
        
        # Get action definition from library
        action_def = self._get_action_definition(action_id)
        if not action_def:
            code_lines.append(" " * indent + f"// Warning: Unknown action {action_id}")
            results["warnings"].append(f"Unknown action: {action_id}")
            return code_lines
        
        # Get DreamBot API mapping
        dreambot_mapping = action.get("dreambot_api_mapping")
        if not dreambot_mapping:
            dreambot_mapping = action_def.get("dreambot_api_mapping")
        
        if not dreambot_mapping:
            code_lines.append(" " * indent + f"// Warning: No DreamBot API mapping for {action_id}")
            results["warnings"].append(f"No DreamBot API mapping: {action_id}")
            return code_lines
        
        # Generate code based on action type
        if action_id.startswith("IF_"):
            # Generate if statement
            condition_code = self._generate_condition_code(action, dreambot_mapping, action.get("properties", {}))
            code_lines.append(" " * indent + f"if ({condition_code}) {{")
            
            # Generate code for children
            if "children" in action and isinstance(action["children"], list):
                for child in action["children"]:
                    child_code = self._generate_action_code(child, results, indent + 4)
                    code_lines.extend(child_code)
            
            code_lines.append(" " * indent + "}")
        
        elif action_id.startswith("WHILE_"):
            # Generate while loop
            condition_code = self._generate_condition_code(action, dreambot_mapping, action.get("properties", {}))
            code_lines.append(" " * indent + f"while ({condition_code}) {{")
            
            # Generate code for children
            if "children" in action and isinstance(action["children"], list):
                for child in action["children"]:
                    child_code = self._generate_action_code(child, results, indent + 4)
                    code_lines.extend(child_code)
            
            code_lines.append(" " * indent + "}")
        
        elif action_id == "FOR_EACH":
            # Generate for-each loop
            properties = action.get("properties", {})
            list_name = properties.get("List name", "unknown_list")
            var_name = properties.get("Variable name", "item")
            
            code_lines.append(" " * indent + f"for (Object {var_name} : getList(\"{list_name}\")) {{")
            
            # Generate code for children
            if "children" in action and isinstance(action["children"], list):
                for child in action["children"]:
                    child_code = self._generate_action_code(child, results, indent + 4)
                    code_lines.extend(child_code)
            
            code_lines.append(" " * indent + "}")
        
        elif action_id == "AND_BRANCH":
            # Generate logical AND branch
            if "children" in action and isinstance(action["children"], list):
                # Collect condition actions
                condition_actions = []
                exec_actions = []
                
                for child in action["children"]:
                    if child.get("id", "").startswith("IF_"):
                        condition_actions.append(child)
                    else:
                        exec_actions.append(child)
                
                if condition_actions:
                    # Generate combined condition
                    conditions = []
                    for cond_action in condition_actions:
                        cond_mapping = cond_action.get("dreambot_api_mapping")
                        if not cond_mapping:
                            cond_def = self._get_action_definition(cond_action.get("id", ""))
                            if cond_def:
                                cond_mapping = cond_def.get("dreambot_api_mapping")
                        
                        if cond_mapping:
                            condition = self._generate_condition_code(cond_action, cond_mapping, cond_action.get("properties", {}))
                            conditions.append(condition)
                    
                    if conditions:
                        code_lines.append(" " * indent + f"if ({' && '.join(conditions)}) {{")
                        
                        # Generate code for execution actions
                        for exec_action in exec_actions:
                            exec_code = self._generate_action_code(exec_action, results, indent + 4)
                            code_lines.extend(exec_code)
                        
                        # Generate code for children of condition actions
                        for cond_action in condition_actions:
                            if "children" in cond_action and isinstance(cond_action["children"], list):
                                for child in cond_action["children"]:
                                    child_code = self._generate_action_code(child, results, indent + 4)
                                    code_lines.extend(child_code)
                        
                        code_lines.append(" " * indent + "}")
        
        elif action_id == "OR_BRANCH":
            # Generate logical OR branch
            if "children" in action and isinstance(action["children"], list):
                # Collect condition actions
                condition_actions = []
                exec_actions = []
                
                for child in action["children"]:
                    if child.get("id", "").startswith("IF_"):
                        condition_actions.append(child)
                    else:
                        exec_actions.append(child)
                
                if condition_actions:
                    # Generate combined condition
                    conditions = []
                    for cond_action in condition_actions:
                        cond_mapping = cond_action.get("dreambot_api_mapping")
                        if not cond_mapping:
                            cond_def = self._get_action_definition(cond_action.get("id", ""))
                            if cond_def:
                                cond_mapping = cond_def.get("dreambot_api_mapping")
                        
                        if cond_mapping:
                            condition = self._generate_condition_code(cond_action, cond_mapping, cond_action.get("properties", {}))
                            conditions.append(condition)
                    
                    if conditions:
                        code_lines.append(" " * indent + f"if ({' || '.join(conditions)}) {{")
                        
                        # Generate code for execution actions
                        for exec_action in exec_actions:
                            exec_code = self._generate_action_code(exec_action, results, indent + 4)
                            code_lines.extend(exec_code)
                        
                        # Generate code for children of condition actions
                        for cond_action in condition_actions:
                            if "children" in cond_action and isinstance(cond_action["children"], list):
                                for child in cond_action["children"]:
                                    child_code = self._generate_action_code(child, results, indent + 4)
                                    code_lines.extend(child_code)
                        
                        code_lines.append(" " * indent + "}")
        
        elif action_id == "IF_FIRST_RUN":
            # Generate first-run check
            code_lines.append(" " * indent + "if (firstRun) {")
            
            # Generate code for children
            if "children" in action and isinstance(action["children"], list):
                for child in action["children"]:
                    child_code = self._generate_action_code(child, results, indent + 4)
                    code_lines.extend(child_code)
            
            # Add code to set firstRun to false
            code_lines.append(" " * indent + "    firstRun = false;")
            code_lines.append(" " * indent + "}")
        
        elif action_id == "SET_VARIABLE":
            # Generate variable assignment
            properties = action.get("properties", {})
            var_name = properties.get("Variable name", "unknown_var")
            
            # Handle special variable value types
            if "Value" in properties:
                value = properties["Value"]
                
                if isinstance(value, dict) and "id" in value:
                    # Handle nested action that provides a value
                    if value["id"] == "SET_VARIABLE_TO_CURRENT_TIME":
                        code_lines.append(" " * indent + f"setVariable(\"{var_name}\", System.currentTimeMillis());")
                    else:
                        code_lines.append(" " * indent + f"// Warning: Unsupported nested action in SET_VARIABLE: {value['id']}")
                        results["warnings"].append(f"Unsupported nested action in SET_VARIABLE: {value['id']}")
                else:
                    # Regular value
                    java_value = self._convert_value_to_java(value)
                    code_lines.append(" " * indent + f"setVariable(\"{var_name}\", {java_value});")
            else:
                code_lines.append(" " * indent + f"// Warning: SET_VARIABLE missing Value property")
                results["warnings"].append("SET_VARIABLE missing Value property")
        
        elif action_id == "CREATE_LIST":
            # Generate list creation
            properties = action.get("properties", {})
            list_name = properties.get("List name", "unknown_list")
            code_lines.append(" " * indent + f"createList(\"{list_name}\");")
        
        elif action_id == "ADD_TO_LIST":
            # Generate add to list
            properties = action.get("properties", {})
            list_name = properties.get("List name", "unknown_list")
            value = properties.get("Value", "")
            java_value = self._convert_value_to_java(value)
            code_lines.append(" " * indent + f"addToList(\"{list_name}\", {java_value});")
        
        elif action_id == "REMOVE_FROM_LIST":
            # Generate remove from list
            properties = action.get("properties", {})
            list_name = properties.get("List name", "unknown_list")
            value = properties.get("Value", "")
            java_value = self._convert_value_to_java(value)
            code_lines.append(" " * indent + f"removeFromList(\"{list_name}\", {java_value});")
        
        elif action_id == "CREATE_TIMER":
            # Generate timer creation
            properties = action.get("properties", {})
            timer_name = properties.get("Timer name", "unknown_timer")
            time_ms = properties.get("Time", "1000")
            code_lines.append(" " * indent + f"createTimer(\"{timer_name}\", {time_ms});")
        
        elif action_id == "RESTART_TIMER":
            # Generate timer restart
            properties = action.get("properties", {})
            timer_name = properties.get("Timer name", "unknown_timer")
            code_lines.append(" " * indent + f"restartTimer(\"{timer_name}\");")
        
        elif action_id.startswith("SLEEP_"):
            # Generate sleep code
            properties = action.get("properties", {})
            
            if action_id == "SLEEP_BETWEEN":
                min_ms = properties.get("Minimum", "500")
                max_ms = properties.get("Maximum", "1000")
                code_lines.append(" " * indent + f"sleep(Calculations.random({min_ms}, {max_ms}));")
            
            elif action_id == "SLEEP_NORMAL_DISTRIBUTION":
                mean = properties.get("Mean", "1000")
                variance = properties.get("Variance", "200")
                code_lines.append(" " * indent + f"sleepGaussian({mean}, {variance});")
            
            else:
                code_lines.append(" " * indent + f"// Warning: Unsupported sleep action: {action_id}")
                results["warnings"].append(f"Unsupported sleep action: {action_id}")
        
        else:
            # Generate standard API method call
            mapping_type = dreambot_mapping.get("type", "method_call")
            
            if mapping_type == "method_call":
                # Standard method call
                api_class = dreambot_mapping.get("class")
                api_method = dreambot_mapping.get("method")
                api_params = dreambot_mapping.get("parameters", [])
                
                if api_class and api_method:
                    # Map properties to parameters
                    properties = action.get("properties", {})
                    param_values = []
                    
                    for param in api_params:
                        param_value = self._map_property_to_parameter(properties, param)
                        param_values.append(param_value)
                    
                    # Build method call
                    param_str = ", ".join(param_values)
                    
                    # Handle chained method calls
                    if "chain" in dreambot_mapping:
                        chain = dreambot_mapping["chain"]
                        chain_method = chain.get("method")
                        chain_params = chain.get("parameters", [])
                        
                        chain_param_values = []
                        for param in chain_params:
                            chain_param_value = self._map_property_to_parameter(properties, param)
                            chain_param_values.append(chain_param_value)
                        
                        chain_param_str = ", ".join(chain_param_values)
                        
                        code_lines.append(" " * indent + f"{api_class}.{api_method}({param_str}).{chain_method}({chain_param_str});")
                    else:
                        code_lines.append(" " * indent + f"{api_class}.{api_method}({param_str});")
                else:
                    code_lines.append(" " * indent + f"// Warning: Incomplete API mapping for {action_id}")
                    results["warnings"].append(f"Incomplete API mapping: {action_id}")
            
            elif mapping_type == "custom_module":
                # Custom module reference
                module = dreambot_mapping.get("module")
                code_lines.append(" " * indent + f"// Custom module: {module}")
                code_lines.append(" " * indent + f"execute{module.capitalize()}Module();")
            
            elif mapping_type in ["variable_assignment", "timer_creation", "list_creation", "timer_restart", "timer_check", "list_add", "list_remove", "list_contains", "for_each_loop", "first_run_check"]:
                # These types handled in specific action cases above
                pass
            
            else:
                code_lines.append(" " * indent + f"// Warning: Unsupported mapping type: {mapping_type}")
                results["warnings"].append(f"Unsupported mapping type: {mapping_type}")
        
        return code_lines
    
    def _generate_condition_code(self, action: Dict[str, Any], mapping: Dict[str, Any], properties: Dict[str, Any]) -> str:
        """
        Generate Java code for a condition.
        
        Args:
            action: The action containing the condition
            mapping: The DreamBot API mapping for the condition
            properties: The action properties
            
        Returns:
            Java code for the condition
        """
        mapping_type = mapping.get("type", "method_call")
        
        if mapping_type == "method_call":
            # Standard method call condition
            api_class = mapping.get("class")
            api_method = mapping.get("method")
            api_params = mapping.get("parameters", [])
            
            if api_class and api_method:
                # Map properties to parameters
                param_values = []
                
                for param in api_params:
                    param_value = self._map_property_to_parameter(properties, param)
                    param_values.append(param_value)
                
                # Build method call
                param_str = ", ".join(param_values)
                condition = f"{api_class}.{api_method}({param_str})"
                
                # Handle comparison
                if "comparison" in mapping:
                    comp = mapping["comparison"]
                    comp_method = comp.get("method")
                    
                    if comp_method == "!= null":
                        condition = f"{condition} != null"
                    elif comp_method == "== null":
                        condition = f"{condition} == null"
                    else:
                        comp_params = comp.get("parameters", [])
                        comp_param_values = []
                        
                        for param in comp_params:
                            if param == "result":
                                continue  # Skip "result" placeholder
                            comp_param_value = self._map_property_to_parameter(properties, param)
                            comp_param_values.append(comp_param_value)
                        
                        # Special handling for percentage calculation
                        if "calculation" in comp and comp["calculation"] == "percentage":
                            base_value = f"{api_class}.{comp_method}({', '.join(comp_param_values)})"
                            current_value = condition
                            condition = f"({current_value} * 100 / {base_value})"
                        
                        # Apply comparison operator
                        if "compare_to" in comp and "operator" in comp:
                            compare_to = self._map_property_to_parameter(properties, comp["compare_to"])
                            operator = self._map_property_to_parameter(properties, comp["operator"])
                            
                            # Convert operator to Java operator
                            java_op = "=="
                            if operator == "EQUALS":
                                java_op = "=="
                            elif operator == "NOT_EQUALS":
                                java_op = "!="
                            elif operator == "GREATER_THAN":
                                java_op = ">"
                            elif operator == "LESS_THAN":
                                java_op = "<"
                            elif operator == "GREATER_THAN_EQUALS":
                                java_op = ">="
                            elif operator == "LESS_THAN_EQUALS":
                                java_op = "<="
                            
                            condition = f"{condition} {java_op} {compare_to}"
                
                # Apply logic inversion if needed
                if mapping.get("logic_inversion", False):
                    condition = f"!({condition})"
                
                return condition
        
        elif mapping_type == "timer_check":
            timer_name = self._map_property_to_parameter(properties, "Timer name")
            condition = f"isTimerFinished({timer_name})"
            return condition
        
        elif mapping_type == "list_contains":
            list_name = self._map_property_to_parameter(properties, "List name")
            value = self._map_property_to_parameter(properties, "Value")
            condition = f"listContains({list_name}, {value})"
            return condition
        
        elif mapping_type == "first_run_check":
            return "firstRun"
        
        # Default fallback
        return "false /* Unsupported condition type */"
    
    def _map_property_to_parameter(self, properties: Dict[str, Any], param_name: str) -> str:
        """
        Map a PSC property to a Java method parameter.
        
        Args:
            properties: The action properties
            param_name: The parameter name or mapping key
            
        Returns:
            Java code for the parameter value
        """
        # Handle direct property mapping
        if param_name in properties:
            return self._convert_value_to_java(properties[param_name])
        
        # Handle property path (e.g. "Filter Item By.value")
        if "." in param_name:
            parts = param_name.split(".")
            prop_name = parts[0]
            sub_field = parts[1]
            
            if prop_name in properties and isinstance(properties[prop_name], dict):
                if sub_field in properties[prop_name]:
                    return self._convert_value_to_java(properties[prop_name][sub_field])
                elif properties[prop_name].get("logic") == "NONE" and sub_field == "value":
                    # Handle NONE logic filter value
                    return self._convert_value_to_java(properties[prop_name].get("value", ""))
        
        # Handle special parameters
        if param_name == "\"Use\"":
            return "\"Use\""
        
        if param_name.startswith("new Tile("):
            # Extract coordinates from property names
            x = self._convert_value_to_java(properties.get("x", 0))
            y = self._convert_value_to_java(properties.get("y", 0))
            z = self._convert_value_to_java(properties.get("z", 0))
            return f"new Tile({x}, {y}, {z})"
        
        if param_name == "Skill.HITPOINTS":
            return "Skill.HITPOINTS"
        
        # Handle operators
        if param_name in ["number.operator", "health.operator", "distance.operator"]:
            # Find the relevant property
            prop_name = param_name.split(".")[0]
            if prop_name in properties and isinstance(properties[prop_name], dict):
                op = properties[prop_name].get("operator", "EQUALS")
                # Convert to Java operator for comparison in code
                return f"\"{op}\""
        
        # For any other cases, return null
        return "null"
    
    def _convert_value_to_java(self, value: Any) -> str:
        """
        Convert a Python value to Java code.
        
        Args:
            value: The value to convert
            
        Returns:
            Java code representing the value
        """
        if value is None:
            return "null"
        
        if isinstance(value, bool):
            return "true" if value else "false"
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # Check for special values
            if value == "All":
                return "Integer.MAX_VALUE"
            
            # Check for variable references
            if value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                return f"getVariable(\"{var_name}\")"
            
            # Regular string
            return f"\"{value}\""
        
        if isinstance(value, dict):
            if "class" in value and "operator" in value and "value" in value:
                # This is a filter condition
                filter_str = self._generate_filter_code(value)
                return filter_str
            
            if all(k in value for k in ["x", "y", "z"]):
                # Tile coordinates
                return f"new Tile({value['x']}, {value['y']}, {value['z']})"
            
            # Other dictionaries
            return "null /* Complex object not supported */"
        
        if isinstance(value, list):
            # Convert to Java array initialization
            items = [self._convert_value_to_java(item) for item in value]
            return f"new Object[] {{{', '.join(items)}}}"
        
        # Default fallback
        return "null /* Unsupported type */"
    
    def _generate_filter_code(self, filter_value: Dict[str, Any]) -> str:
        """
        Generate Java code for a filter structure.
        
        Args:
            filter_value: The filter structure
            
        Returns:
            Java code for the filter
        """
        filter_class = filter_value.get("class")
        
        if not filter_class:
            return "null /* Invalid filter */"
        
        # Map filter class to DreamBot filter class
        filter_class_map = {
            "Item": "item",
            "NPC": "npc",
            "GameObject": "obj",
            "GroundItem": "item",
            "Player": "player"
        }
        
        param_name = filter_class_map.get(filter_class, "e")
        
        # Simple filter (NONE logic)
        if "logic" not in filter_value or filter_value["logic"] == "NONE":
            filter_type = filter_value.get("type")
            operator = filter_value.get("operator")
            value = filter_value.get("value")
            
            if not all([filter_type, operator, value is not None]):
                return "null /* Incomplete filter */"
            
            # Convert value to Java
            java_value = self._convert_value_to_java(value)
            
            # Generate filter condition based on filter type and operator
            condition = self._generate_filter_condition(filter_class, filter_type, operator, java_value, param_name)
            
            return f"{param_name} -> {condition}"
        
        # Complex filter (AND/OR logic)
        elif filter_value.get("logic") in ["AND", "OR"] and "conditions" in filter_value:
            conditions = []
            
            for condition in filter_value["conditions"]:
                if not all(k in condition for k in ["type", "operator", "value"]):
                    continue
                
                filter_type = condition["type"]
                operator = condition["operator"]
                value = condition["value"]
                
                # Convert value to Java
                java_value = self._convert_value_to_java(value)
                
                # Generate condition
                cond = self._generate_filter_condition(filter_class, filter_type, operator, java_value, param_name)
                conditions.append(cond)
            
            if not conditions:
                return "null /* No valid conditions */"
            
            # Join conditions with appropriate logic operator
            logic_op = "&&" if filter_value["logic"] == "AND" else "||"
            joined_conditions = f" {logic_op} ".join(conditions)
            
            return f"{param_name} -> {joined_conditions}"
        
        return "null /* Unsupported filter structure */"
    
    def _generate_filter_condition(self, filter_class: str, filter_type: str, operator: str, java_value: str, param_name: str) -> str:
        """
        Generate a Java condition for a filter.
        
        Args:
            filter_class: Filter class name
            filter_type: Filter type name
            operator: Filter operator
            java_value: Java code for the filter value
            param_name: Parameter name for the lambda
            
        Returns:
            Java code for the filter condition
        """
        # Map common getters based on filter class and type
        getters = {
            "Item": {
                "NAME": "getName()",
                "ID": "getID()",
                "STACKABLE": "isStackable()",
                "NOTED": "isNoted()",
                "VALUE": "getPrice()"
            },
            "NPC": {
                "NAME": "getName()",
                "ID": "getID()",
                "LEVEL": "getLevel()",
                "INTERACTING_WITH_ME": "isInteractingWithMe()",
                "DISTANCE": "distance(Players.getLocal().getTile())"
            },
            "GameObject": {
                "NAME": "getName()",
                "ID": "getID()",
                "DISTANCE": "distance(Players.getLocal().getTile())",
                "ACTION": "hasAction"  # Special case
            },
            "GroundItem": {
                "NAME": "getName()",
                "ID": "getID()",
                "DISTANCE": "distance(Players.getLocal().getTile())",
                "STACKSIZE": "getAmount()"
            },
            "Player": {
                "NAME": "getName()",
                "LEVEL": "getLevel()",
                "DISTANCE": "distance(Players.getLocal().getTile())",
                "INTERACTING_WITH_ME": "isInteractingWithMe()"
            }
        }
        
        # Map operators to Java operators/methods
        op_map = {
            "EQUALS": "==",
            "NOT_EQUALS": "!=",
            "GREATER_THAN": ">",
            "LESS_THAN": "<",
            "GREATER_THAN_EQUALS": ">=",
            "LESS_THAN_EQUALS": "<=",
            "CONTAINS": ".contains",
            "STARTS_WITH": ".startsWith",
            "ENDS_WITH": ".endsWith",
            "MATCHES_REGEX": ".matches"
        }
        
        # Get the getter for this filter class and type
        getter = getters.get(filter_class, {}).get(filter_type)
        
        if not getter:
            return "true /* Unsupported filter type */"
        
        # Special handling for specific cases
        if filter_type == "ACTION" and filter_class == "GameObject":
            return f"{param_name}.{getter}({java_value})"
        
        # Handle different data types
        if filter_type in ["NAME", "ACTION"]:
            # String values
            if operator in ["EQUALS", "NOT_EQUALS"]:
                return f"{param_name}.{getter}.equalsIgnoreCase({java_value})"
            elif operator in ["CONTAINS", "STARTS_WITH", "ENDS_WITH", "MATCHES_REGEX"]:
                method = op_map[operator]
                return f"{param_name}.{getter}.toLowerCase(){method}({java_value}.toLowerCase())"
            else:
                return "true /* Unsupported string operator */"
        
        elif filter_type in ["STACKABLE", "NOTED", "INTERACTING_WITH_ME"]:
            # Boolean values
            if operator == "EQUALS":
                return f"{param_name}.{getter} == {java_value}"
            else:
                return "true /* Unsupported boolean operator */"
        
        else:
            # Numeric values
            if operator in ["EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS"]:
                java_op = op_map[operator]
                return f"{param_name}.{getter} {java_op} {java_value}"
            elif operator == "BETWEEN":
                # Assume value is array with two elements
                return f"({param_name}.{getter} >= {java_value}[0] && {param_name}.{getter} <= {java_value}[1])"
            else:
                return "true /* Unsupported numeric operator */"
    
    def _generate_helper_methods(self) -> List[str]:
        """
        Generate helper methods for the script class.
        
        Returns:
            List of lines of Java code for helper methods
        """
        code = []
        
        # Variable management methods
        code.append("    // Helper methods for variable management")
        code.append("    private void setVariable(String name, Object value) {")
        code.append("        variables.put(name, value);")
        code.append("    }")
        code.append("")
        
        code.append("    private Object getVariable(String name) {")
        code.append("        return variables.getOrDefault(name, null);")
        code.append("    }")
        code.append("")
        
        code.append("    private String getStringVariable(String name) {")
        code.append("        Object value = getVariable(name);")
        code.append("        return value != null ? value.toString() : \"\";")
        code.append("    }")
        code.append("")
        
        code.append("    private int getIntVariable(String name, int defaultValue) {")
        code.append("        Object value = getVariable(name);")
        code.append("        if (value instanceof Number) {")
        code.append("            return ((Number) value).intValue();")
        code.append("        } else if (value instanceof String) {")
        code.append("            try {")
        code.append("                return Integer.parseInt((String) value);")
        code.append("            } catch (NumberFormatException e) {")
        code.append("                return defaultValue;")
        code.append("            }")
        code.append("        }")
        code.append("        return defaultValue;")
        code.append("    }")
        code.append("")
        
        # List management methods
        code.append("    // Helper methods for list management")
        code.append("    private void createList(String name) {")
        code.append("        lists.put(name, new ArrayList<>());")
        code.append("    }")
        code.append("")
        
        code.append("    private List<Object> getList(String name) {")
        code.append("        return lists.getOrDefault(name, new ArrayList<>());")
        code.append("    }")
        code.append("")
        
        code.append("    private void addToList(String name, Object value) {")
        code.append("        List<Object> list = getList(name);")
        code.append("        list.add(value);")
        code.append("        lists.put(name, list);")
        code.append("    }")
        code.append("")
        
        code.append("    private void removeFromList(String name, Object value) {")
        code.append("        List<Object> list = getList(name);")
        code.append("        list.remove(value);")
        code.append("        lists.put(name, list);")
        code.append("    }")
        code.append("")
        
        code.append("    private boolean listContains(String name, Object value) {")
        code.append("        return getList(name).contains(value);")
        code.append("    }")
        code.append("")
        
        # Timer management methods
        code.append("    // Helper methods for timer management")
        code.append("    private void createTimer(String name, long duration) {")
        code.append("        timers.put(name, System.currentTimeMillis() + duration);")
        code.append("    }")
        code.append("")
        
        code.append("    private void restartTimer(String name) {")
        code.append("        if (timers.containsKey(name)) {")
        code.append("            long duration = timers.get(name) - System.currentTimeMillis();")
        code.append("            if (duration < 0) {")
        code.append("                duration = 1000; // Default 1 second if timer already elapsed")
        code.append("            }")
        code.append("            timers.put(name, System.currentTimeMillis() + duration);")
        code.append("        } else {")
        code.append("            timers.put(name, System.currentTimeMillis() + 1000);")
        code.append("        }")
        code.append("    }")
        code.append("")
        
        code.append("    private boolean isTimerFinished(String name) {")
        code.append("        if (!timers.containsKey(name)) {")
        code.append("            return true;")
        code.append("        }")
        code.append("        return System.currentTimeMillis() >= timers.get(name);")
        code.append("    }")
        code.append("")
        
        # Sleep method for normal distribution
        code.append("    // Helper method for normal distribution sleep")
        code.append("    private void sleepGaussian(int mean, int standardDeviation) {")
        code.append("        double gaussian = random.nextGaussian();")
        code.append("        int sleep = (int) (gaussian * standardDeviation + mean);")
        code.append("        sleep = Math.max(100, sleep); // Ensure minimum sleep time")
        code.append("        sleep(sleep);")
        code.append("    }")
        code.append("")
        
        return code


def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description="PSC Standardizer - Tool for processing PSC JSON files")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get script directory for path resolution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    default_libraries_dir = os.path.join(parent_dir, "libraries")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a PSC JSON file")
    analyze_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    analyze_parser.add_argument("--output-file", help="Path to save the analysis report (optional)")
    analyze_parser.add_argument("--libraries-dir", default=default_libraries_dir, help="Path to the libraries directory")
    
    # Standardize command
    standardize_parser = subparsers.add_parser("standardize", help="Standardize a PSC JSON file")
    standardize_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    standardize_parser.add_argument("--output-file", required=True, help="Path to save the standardized JSON")
    standardize_parser.add_argument("--libraries-dir", default=default_libraries_dir, help="Path to the libraries directory")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a PSC JSON file")
    validate_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    validate_parser.add_argument("--output-file", help="Path to save the validation report (optional)")
    validate_parser.add_argument("--libraries-dir", default=default_libraries_dir, help="Path to the libraries directory")
    
    # Generate code command
    generate_parser = subparsers.add_parser("generate-code", help="Generate DreamBot Java code from a PSC JSON file")
    generate_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    generate_parser.add_argument("--output-file", required=True, help="Path to save the generated Java code")
    generate_parser.add_argument("--libraries-dir", default=default_libraries_dir, help="Path to the libraries directory")
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "analyze":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.analyze_psc_json(args.input_file, args.output_file)
    
    elif args.command == "standardize":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.standardize_psc_json(args.input_file, args.output_file)
    
    elif args.command == "validate":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.validate_psc_json(args.input_file, args.output_file)
    
    elif args.command == "generate-code":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.generate_dreambot_code(args.input_file, args.output_file)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()