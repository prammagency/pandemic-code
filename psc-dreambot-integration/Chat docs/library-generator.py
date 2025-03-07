import json
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

class PSCLibraryGenerator:
    """
    Tool to generate standardized libraries for PSC actions, filters, and logic.
    """
    
    def __init__(self, output_dir: str = "libraries"):
        """
        Initialize the library generator.
        
        Args:
            output_dir: Directory to save generated libraries
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_action_hierarchy_library(self, github_actions_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate the Action Hierarchy & Structure Library.
        
        Args:
            github_actions_data: Optional list of actions from GitHub repo to analyze
            
        Returns:
            Generated library as dictionary
        """
        # Initialize library structure
        action_library = {
            "action_categories": [
                "banking", "combat", "entities", "ground_items", "inventory", 
                "logic", "movement", "sleep", "variables", "widget"
            ],
            "actions": {}
        }
        
        # Add standard actions with complete documentation
        action_library["actions"].update(self._get_banking_actions())
        action_library["actions"].update(self._get_inventory_actions())
        action_library["actions"].update(self._get_logic_actions())
        action_library["actions"].update(self._get_movement_actions())
        
        # If GitHub data is provided, analyze and incorporate it
        if github_actions_data:
            for action_data in github_actions_data:
                action_id = action_data.get("id")
                if action_id and action_id not in action_library["actions"]:
                    # Create a standardized entry for this action
                    category = self._guess_action_category(action_id)
                    std_action = {
                        "category": category,
                        "description": f"Action: {action_id}",
                        "can_be_root": True,
                        "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "properties": {
                            "required": [],
                            "optional": []
                        }
                    }
                    
                    # Extract properties from the GitHub data
                    if "properties" in action_data:
                        for prop_name in action_data["properties"]:
                            std_action["properties"]["required"].append(prop_name)
                    
                    # Check for children to determine if it's a container
                    if "children" in action_data:
                        std_action["valid_children"] = ["*"]
                    
                    # Add to library
                    action_library["actions"][action_id] = std_action
        
        # Save to file
        self._save_library(action_library, "action_hierarchy_library.json")
        
        return action_library
    
    def generate_filter_types_library(self) -> Dict[str, Any]:
        """
        Generate the Filter Types & Operators Library.
        
        Returns:
            Generated library as dictionary
        """
        filter_library = {
            "filter_classes": {
                "Item": {
                    "description": "Filters for items in inventory, bank, etc.",
                    "filter_types": {
                        "NAME": {
                            "description": "Filter items by name",
                            "data_type": "string",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "CONTAINS", "STARTS_WITH", 
                                "ENDS_WITH", "MATCHES_REGEX", "IS_IN_LIST"
                            ],
                            "example_values": ["Bones", "Dragon bones", "Coins", "Rune essence"]
                        },
                        "ID": {
                            "description": "Filter items by item ID",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN", "IS_IN_LIST"
                            ],
                            "example_values": [526, 532, 995, 1436]
                        },
                        "STACKABLE": {
                            "description": "Filter items by stackability",
                            "data_type": "boolean",
                            "valid_operators": ["EQUALS"],
                            "example_values": [True, False]
                        },
                        "NOTED": {
                            "description": "Filter items by noted status",
                            "data_type": "boolean",
                            "valid_operators": ["EQUALS"],
                            "example_values": [True, False]
                        },
                        "VALUE": {
                            "description": "Filter items by GE value",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [100, 1000, 10000]
                        }
                    }
                },
                "NPC": {
                    "description": "Filters for NPCs in the game world",
                    "filter_types": {
                        "NAME": {
                            "description": "Filter NPCs by name",
                            "data_type": "string",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "CONTAINS", "STARTS_WITH", 
                                "ENDS_WITH", "MATCHES_REGEX", "IS_IN_LIST"
                            ],
                            "example_values": ["Man", "Goblin", "Elder Chaos druid", "Banker"]
                        },
                        "ID": {
                            "description": "Filter NPCs by ID",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN", "IS_IN_LIST"
                            ],
                            "example_values": [3080, 655, 7995]
                        },
                        "LEVEL": {
                            "description": "Filter NPCs by combat level",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [2, 20, 80, 126]
                        },
                        "INTERACTING_WITH_ME": {
                            "description": "Filter NPCs by whether they're interacting with player",
                            "data_type": "boolean",
                            "valid_operators": ["EQUALS"],
                            "example_values": [True, False]
                        },
                        "DISTANCE": {
                            "description": "Filter NPCs by distance from player",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [1, 5, 10, 20]
                        }
                    }
                },
                "GameObject": {
                    "description": "Filters for game objects in the world",
                    "filter_types": {
                        "NAME": {
                            "description": "Filter game objects by name",
                            "data_type": "string",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "CONTAINS", "STARTS_WITH", 
                                "ENDS_WITH", "MATCHES_REGEX", "IS_IN_LIST"
                            ],
                            "example_values": ["Grand Exchange booth", "Bank booth", "Door", "Tree"]
                        },
                        "ID": {
                            "description": "Filter game objects by ID",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN", "IS_IN_LIST"
                            ],
                            "example_values": [1317, 24101, 10355]
                        },
                        "DISTANCE": {
                            "description": "Filter game objects by distance from player",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [1, 5, 10, 20]
                        },
                        "ACTION": {
                            "description": "Filter game objects by available action",
                            "data_type": "string",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "CONTAINS", "STARTS_WITH", 
                                "ENDS_WITH", "MATCHES_REGEX", "IS_IN_LIST"
                            ],
                            "example_values": ["Open", "Close", "Use", "Search", "Climb"]
                        }
                    }
                },
                "GroundItem": {
                    "description": "Filters for items on the ground",
                    "filter_types": {
                        "NAME": {
                            "description": "Filter ground items by name",
                            "data_type": "string",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "CONTAINS", "STARTS_WITH", 
                                "ENDS_WITH", "MATCHES_REGEX", "IS_IN_LIST"
                            ],
                            "example_values": ["Bones", "Dragon bones", "Coins", "Rune essence"]
                        },
                        "ID": {
                            "description": "Filter ground items by ID",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN", "IS_IN_LIST"
                            ],
                            "example_values": [526, 532, 995, 1436]
                        },
                        "DISTANCE": {
                            "description": "Filter ground items by distance from player",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [1, 5, 10, 20]
                        },
                        "STACKSIZE": {
                            "description": "Filter ground items by stack size",
                            "data_type": "integer",
                            "valid_operators": [
                                "EQUALS", "NOT_EQUALS", "GREATER_THAN", "LESS_THAN", 
                                "GREATER_THAN_EQUALS", "LESS_THAN_EQUALS", "BETWEEN"
                            ],
                            "example_values": [1, 10, 100, 1000]
                        }
                    }
                }
            },
            "logical_operators": {
                "AND": {
                    "description": "Logical AND - all conditions must be true",
                    "usage": "Use when multiple filter conditions must ALL be satisfied",
                    "example": {
                        "class": "Item",
                        "logic": "AND",
                        "conditions": [
                            {"type": "NAME", "operator": "CONTAINS", "value": "rune"},
                            {"type": "VALUE", "operator": "GREATER_THAN", "value": "1000"}
                        ]
                    }
                },
                "OR": {
                    "description": "Logical OR - at least one condition must be true",
                    "usage": "Use when ANY of multiple filter conditions can be satisfied",
                    "example": {
                        "class": "NPC",
                        "logic": "OR",
                        "conditions": [
                            {"type": "NAME", "operator": "EQUALS", "value": "Goblin"},
                            {"type": "NAME", "operator": "EQUALS", "value": "Rat"}
                        ]
                    }
                },
                "NONE": {
                    "description": "No logical operator - single condition",
                    "usage": "Use when only one filter condition is needed",
                    "example": {
                        "class": "Item",
                        "logic": "NONE",
                        "type": "NAME",
                        "operator": "EQUALS",
                        "value": "Bones"
                    }
                }
            }
        }
        
        # Save to file
        self._save_library(filter_library, "filter_types_library.json")
        
        return filter_library
    
    def generate_control_flow_library(self) -> Dict[str, Any]:
        """
        Generate the Control Flow & Logic Structure Library.
        
        Returns:
            Generated library as dictionary
        """
        control_flow_library = {
            "control_structures": {
                "AND_BRANCH": {
                    "description": "Logical AND branch - executes child actions only if all conditions are true",
                    "usage_pattern": "Use for checking multiple conditions that must ALL be satisfied",
                    "nesting_rules": {
                        "can_be_nested_in": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "can_contain": ["*"]
                    },
                    "example": {
                        "id": "AND_BRANCH",
                        "children": [
                            {
                                "id": "IF_INVENTORY_CONTAINS",
                                "properties": {
                                    "Filter Item By": {
                                        "class": "Item",
                                        "logic": "NONE",
                                        "type": "NAME",
                                        "operator": "EQUALS",
                                        "value": "Coins"
                                    }
                                }
                            },
                            {
                                "id": "IF_BANK_IS_OPEN"
                            }
                        ]
                    },
                    "dreambot_translation": "Implemented as multiple conditional checks with && operator"
                },
                "OR_BRANCH": {
                    "description": "Logical OR branch - executes child actions if any condition is true",
                    "usage_pattern": "Use for checking multiple conditions where ANY can be satisfied",
                    "nesting_rules": {
                        "can_be_nested_in": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "can_contain": ["*"]
                    },
                    "example": {
                        "id": "OR_BRANCH",
                        "children": [
                            {
                                "id": "IF_INVENTORY_CONTAINS",
                                "properties": {
                                    "Filter Item By": {
                                        "class": "Item",
                                        "logic": "NONE",
                                        "type": "NAME",
                                        "operator": "EQUALS",
                                        "value": "Bones"
                                    }
                                }
                            },
                            {
                                "id": "IF_INVENTORY_CONTAINS",
                                "properties": {
                                    "Filter Item By": {
                                        "class": "Item",
                                        "logic": "NONE",
                                        "type": "NAME",
                                        "operator": "EQUALS",
                                        "value": "Dragon bones"
                                    }
                                }
                            }
                        ]
                    },
                    "dreambot_translation": "Implemented as multiple conditional checks with || operator"
                },
                "IF_STATEMENT": {
                    "description": "Conditional execution based on specific condition",
                    "usage_pattern": "Use any IF_* action to check a condition and execute children only if true",
                    "nesting_rules": {
                        "can_be_nested_in": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "can_contain": ["*"]
                    },
                    "example": {
                        "id": "IF_INVENTORY_IS_FULL",
                        "children": [
                            {
                                "id": "BANK_DEPOSIT_ALL"
                            }
                        ]
                    },
                    "dreambot_translation": "Implemented as standard if statement in Java"
                },
                "WHILE_LOOP": {
                    "description": "Repeatedly executes child actions while condition is true",
                    "usage_pattern": "Use any WHILE_* action for repetitive execution based on a condition",
                    "nesting_rules": {
                        "can_be_nested_in": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "can_contain": ["*"]
                    },
                    "example": {
                        "id": "WHILE_INVENTORY_IS_NOT_FULL",
                        "children": [
                            {
                                "id": "GROUND_ITEM_INTERACT",
                                "properties": {
                                    "Filter Item By": {
                                        "class": "GroundItem",
                                        "logic": "NONE",
                                        "type": "NAME",
                                        "operator": "EQUALS",
                                        "value": "Bones"
                                    }
                                }
                            }
                        ]
                    },
                    "dreambot_translation": "Implemented as standard while loop in Java"
                },
                "SEQUENCE": {
                    "description": "Sequential execution of actions (implicit in root or within other structures)",
                    "usage_pattern": "Default behavior when adding multiple actions to root or within a structure",
                    "nesting_rules": {
                        "can_be_nested_in": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                        "can_contain": ["*"]
                    },
                    "example": {
                        "actions": [
                            {
                                "id": "WALK_TO_BANK"
                            },
                            {
                                "id": "OPEN_BANK"
                            },
                            {
                                "id": "BANK_DEPOSIT_ALL"
                            }
                        ]
                    },
                    "dreambot_translation": "Implemented as sequential statements in Java"
                }
            },
            "complex_structures": {
                "nested_conditionals": {
                    "description": "Nesting conditionals for complex decision trees",
                    "example": {
                        "id": "IF_BANK_IS_OPEN",
                        "children": [
                            {
                                "id": "IF_INVENTORY_CONTAINS",
                                "properties": {
                                    "Filter Item By": {
                                        "class": "Item",
                                        "logic": "NONE",
                                        "type": "NAME",
                                        "operator": "EQUALS",
                                        "value": "Bones"
                                    }
                                },
                                "children": [
                                    {
                                        "id": "BANK_DEPOSIT_ITEM",
                                        "properties": {
                                            "Filter Item By": {
                                                "class": "Item",
                                                "logic": "NONE",
                                                "type": "NAME",
                                                "operator": "EQUALS",
                                                "value": "Bones"
                                            },
                                            "Amount": "All"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                },
                "loop_with_conditionals": {
                    "description": "Combining loops with conditional checks",
                    "example": {
                        "id": "WHILE_BANK_IS_OPEN",
                        "children": [
                            {
                                "id": "IF_INVENTORY_IS_FULL",
                                "children": [
                                    {
                                        "id": "BANK_DEPOSIT_ALL"
                                    }
                                ]
                            },
                            {
                                "id": "IF_INVENTORY_IS_NOT_FULL",
                                "children": [
                                    {
                                        "id": "IF_BANK_CONTAINS",
                                        "properties": {
                                            "Filter Item By": {
                                                "class": "Item",
                                                "logic": "NONE",
                                                "type": "NAME",
                                                "operator": "EQUALS",
                                                "value": "Bones"
                                            }
                                        },
                                        "children": [
                                            {
                                                "id": "BANK_WITHDRAW_ITEM",
                                                "properties": {
                                                    "Filter Item By": {
                                                        "class": "Item",
                                                        "logic": "NONE",
                                                        "type": "NAME",
                                                        "operator": "EQUALS",
                                                        "value": "Bones"
                                                    },
                                                    "Amount": "28"
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
        
        # Save to file
        self._save_library(control_flow_library, "control_flow_library.json")
        
        return control_flow_library
    
    def generate_property_values_library(self) -> Dict[str, Any]:
        """
        Generate the Property Values & Types Library.
        
        Returns:
            Generated library as dictionary
        """
        property_library = {
            "property_types": {
                "numeric": {
                    "description": "Numeric values (integers or floating point)",
                    "subtypes": {
                        "integer": {
                            "description": "Whole number values",
                            "examples": [1, 10, 100, 1000],
                            "special_values": {
                                "All": "Used when referring to all items/quantities"
                            }
                        },
                        "float": {
                            "description": "Decimal number values",
                            "examples": [0.5, 1.5, 10.75],
                            "format_notes": "May require decimal point even for whole numbers in some contexts"
                        }
                    }
                },
                "string": {
                    "description": "Text values",
                    "formats": {
                        "simple": {
                            "description": "Basic text string",
                            "examples": ["Bones", "Coins", "Dragon bones"]
                        },
                        "regex": {
                            "description": "Regular expression pattern",
                            "examples": ["Rune.*", "Dragon .*", "[A-Z].*"],
                            "usage_notes": "Used with MATCHES_REGEX operator"
                        }
                    }
                },
                "boolean": {
                    "description": "True/false values",
                    "valid_values": [True, False],
                    "format_notes": "Usually represented as checkboxes in PSC UI"
                },
                "coordinate": {
                    "description": "X, Y, Z map coordinates",
                    "format": {
                        "x": "Integer X coordinate on the map",
                        "y": "Integer Y coordinate on the map",
                        "z": "Integer Z coordinate (plane/level)",
                        "examples": [
                            {"x": 3221, "y": 3218, "z": 0},
                            {"x": 3165, "y": 3489, "z": 0}
                        ]
                    }
                },
                "variable_reference": {
                    "description": "Reference to a variable in PSC",
                    "format": "${variable_name}",
                    "examples": ["${coin_count}", "${target_npc}", "${last_position}"],
                    "usage_notes": "Can be used in most property values to reference variables"
                },
                "list_reference": {
                    "description": "Reference to a list in PSC",
                    "format": "list_name",
                    "examples": ["loot_items", "target_npcs", "bank_locations"],
                    "usage_notes": "Used with IS_IN_LIST operator"
                }
            },
            "common_properties": {
                "Amount": {
                    "description": "Quantity of items to withdraw/deposit/drop",
                    "type": "numeric.integer or string",
                    "valid_values": ["Any positive integer", "All"],
                    "examples": [1, 5, 10, 28, "All"]
                },
                "Minimum": {
                    "description": "Minimum value for ranges (sleep, random number, etc.)",
                    "type": "numeric",
                    "valid_values": ["Any non-negative number"],
                    "examples": [500, 1000, 2000]
                },
                "Maximum": {
                    "description": "Maximum value for ranges (sleep, random number, etc.)",
                    "type": "numeric",
                    "valid_values": ["Any number greater than Minimum"],
                    "examples": [1000, 2000, 5000]
                },
                "Timer name": {
                    "description": "Name identifier for timers",
                    "type": "string",
                    "valid_values": ["Any text without spaces"],
                    "examples": ["bank_timer", "combat_timer", "antiban_timer"]
                },
                "Variable name": {
                    "description": "Name identifier for variables",
                    "type": "string",
                    "valid_values": ["Any text without spaces"],
                    "examples": ["coin_count", "target_npc", "last_position"]
                }
            }
        }
        
        # Save to file
        self._save_library(property_library, "property_values_library.json")
        
        return property_library
    
    def generate_all_libraries(self, github_actions_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Generate all standardized libraries.
        
        Args:
            github_actions_data: Optional list of actions from GitHub repo to analyze
            
        Returns:
            Dictionary with all generated libraries
        """
        libraries = {}
        
        print("Generating Action Hierarchy Library...")
        libraries["actions"] = self.generate_action_hierarchy_library(github_actions_data)
        
        print("Generating Filter Types Library...")
        libraries["filters"] = self.generate_filter_types_library()
        
        print("Generating Control Flow Library...")
        libraries["control_flow"] = self.generate_control_flow_library()
        
        print("Generating Property Values Library...")
        libraries["properties"] = self.generate_property_values_library()
        
        return libraries
    
    def _save_library(self, library: Dict[str, Any], filename: str) -> None:
        """
        Save a library to a JSON file.
        
        Args:
            library: The library to save
            filename: Filename in the output directory
        """
        file_path = self.output_dir / filename
        with open(file_path, 'w') as f:
            json.dump(library, f, indent=2)
        print(f"Generated library saved to {file_path}")
    
    def _guess_action_category(self, action_id: str) -> str:
        """
        Guess the category of an action based on its ID.
        
        Args:
            action_id: The action ID
            
        Returns:
            Guessed category name
        """
        action_id_lower = action_id.lower()
        
        if any(x in action_id_lower for x in ["bank", "deposit", "withdraw"]):
            return "banking"
        elif any(x in action_id_lower for x in ["attack", "combat", "fight", "kill"]):
            return "combat"
        elif any(x in action_id_lower for x in ["npc", "player", "entity"]):
            return "entities"
        elif any(x in action_id_lower for x in ["ground_item", "pickup"]):
            return "ground_items"
        elif any(x in action_id_lower for x in ["inventory", "item", "equip"]):
            return "inventory"
        elif any(x in action_id_lower for x in ["if", "while", "and", "or", "branch"]):
            return "logic"
        elif any(x in action_id_lower for x in ["walk", "move", "tile", "path"]):
            return "movement"
        elif any(x in action_id_lower for x in ["sleep", "wait", "delay"]):
            return "sleep"
        elif any(x in action_id_lower for x in ["var", "variable", "set", "get"]):
            return "variables"
        elif any(x in action_id_lower for x in ["widget", "interface", "dialog"]):
            return "widget"
        else:
            return "unknown"
    
    def _get_banking_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get pre-defined banking actions with complete documentation.
        
        Returns:
            Dictionary of banking actions
        """
        return {
            "BANK_DEPOSIT_ALL": {
                "category": "banking",
                "description": "Deposits all items in the inventory into the bank",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "depositAll",
                    "parameters": []
                }
            },
            "BANK_DEPOSIT_ALL_EXCEPT": {
                "category": "banking",
                "description": "Deposits all items in the inventory except those matching the filter",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "depositAllExcept",
                    "parameters": ["itemFilter"]
                }
            },
            "BANK_DEPOSIT_ITEM": {
                "category": "banking",
                "description": "Deposits a specific item from inventory into the bank",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": ["Filter Item By", "Amount"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "deposit",
                    "parameters": ["item", "amount"]
                }
            },
            "BANK_WITHDRAW_ITEM": {
                "category": "banking",
                "description": "Withdraws a specific item from the bank into inventory",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": ["Filter Item By", "Amount"],
                    "optional": ["Noted"]
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "withdraw",
                    "parameters": ["item", "amount"]
                }
            },
            "BANK_WITHDRAW_ALL": {
                "category": "banking",
                "description": "Withdraws all items matching the filter from bank",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": ["Noted"]
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "withdrawAll",
                    "parameters": ["item"]
                }
            },
            "OPEN_BANK": {
                "category": "banking",
                "description": "Opens the bank by interacting with a bank object",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_NOT_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": [],
                    "optional": ["Bank Type"]
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "open",
                    "parameters": []
                }
            },
            "CLOSE_BANK": {
                "category": "banking",
                "description": "Closes the bank if it's open",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "close",
                    "parameters": []
                }
            },
            "IF_BANK_IS_OPEN": {
                "category": "banking",
                "description": "Conditional that checks if the bank is open",
                "can_be_root": True,
                "valid_parents": ["root", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "isOpen",
                    "parameters": []
                }
            },
            "IF_BANK_IS_NOT_OPEN": {
                "category": "banking",
                "description": "Conditional that checks if the bank is not open",
                "can_be_root": True,
                "valid_parents": ["root", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "isOpen",
                    "parameters": [],
                    "logic_inversion": True
                }
            },
            "IF_BANK_CONTAINS": {
                "category": "banking",
                "description": "Conditional that checks if the bank contains an item",
                "can_be_root": True,
                "valid_parents": ["root", "IF_BANK_IS_OPEN", "AND_BRANCH", "OR_BRANCH", "WHILE_LOOP"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Bank",
                    "method": "contains",
                    "parameters": ["Filter Item By.value"]
                }
            }
        }
    
    def _get_inventory_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get pre-defined inventory actions with complete documentation.
        
        Returns:
            Dictionary of inventory actions
        """
        return {
            "IF_INVENTORY_CONTAINS": {
                "category": "inventory",
                "description": "Conditional that checks if the inventory contains an item",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "contains",
                    "parameters": ["Filter Item By.value"]
                }
            },
            "IF_INVENTORY_IS_FULL": {
                "category": "inventory",
                "description": "Conditional that checks if the inventory is full",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "isFull",
                    "parameters": []
                }
            },
            "IF_INVENTORY_IS_NOT_FULL": {
                "category": "inventory",
                "description": "Conditional that checks if the inventory is not full",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "isFull",
                    "parameters": [],
                    "logic_inversion": True
                }
            },
            "INVENTORY_DROP_ITEM": {
                "category": "inventory",
                "description": "Drops an item from the inventory",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": ["Amount"]
                },
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "drop",
                    "parameters": ["Filter Item By.value"]
                }
            },
            "INVENTORY_DROP_ALL": {
                "category": "inventory",
                "description": "Drops all items in the inventory",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "dropAll",
                    "parameters": []
                }
            },
            "INVENTORY_DROP_ALL_EXCEPT": {
                "category": "inventory",
                "description": "Drops all items except those matching the filter",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "dropAllExcept",
                    "parameters": ["Filter Item By.value"]
                }
            },
            "INVENTORY_USE_ITEM": {
                "category": "inventory",
                "description": "Uses an item in the inventory",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Filter Item By"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "interact",
                    "parameters": ["Filter Item By.value", "\"Use\""]
                }
            },
            "INVENTORY_COUNT_ITEM": {
                "category": "inventory",
                "description": "Counts items in inventory matching the filter",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Filter Item By", "Variable name"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Inventory",
                    "method": "count",
                    "parameters": ["Filter Item By.value"],
                    "result_variable": "Variable name"
                }
            }
        }
    
    def _get_logic_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get pre-defined logic actions with complete documentation.
        
        Returns:
            Dictionary of logic actions
        """
        return {
            "AND_BRANCH": {
                "category": "logic",
                "description": "Logical AND operation that executes child actions only if all conditions are true",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "min_children": 2,
                "dreambot_api_mapping": {
                    "type": "logical_construct",
                    "construct": "multiple_conditions_and"
                }
            },
            "OR_BRANCH": {
                "category": "logic",
                "description": "Logical OR operation that executes child actions if any condition is true",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "min_children": 2,
                "dreambot_api_mapping": {
                    "type": "logical_construct",
                    "construct": "multiple_conditions_or"
                }
            },
            "SET_VARIABLE": {
                "category": "variables",
                "description": "Sets a variable to a specified value",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Variable name", "Value"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "type": "variable_assignment",
                    "variable": "Variable name",
                    "value": "Value"
                }
            },
            "RANDOM_SLEEP": {
                "category": "sleep",
                "description": "Pauses script execution for a random duration between min and max milliseconds",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["Minimum", "Maximum"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Calculations",
                    "method": "random",
                    "parameters": ["Minimum", "Maximum"],
                    "wrapper": "sleep"
                }
            }
        }
    
    def _get_movement_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get pre-defined movement actions with complete documentation.
        
        Returns:
            Dictionary of movement actions
        """
        return {
            "WALK_TO_TILE": {
                "category": "movement",
                "description": "Walks to a specific tile on the map",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": ["x", "y", "z"],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Walking",
                    "method": "walk",
                    "parameters": ["new Tile(x, y, z)"]
                }
            },
            "WALK_TO_BANK": {
                "category": "movement",
                "description": "Walks to the nearest bank",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Walking",
                    "method": "walkToBank",
                    "parameters": []
                }
            },
            "WALK_TO_GRAND_EXCHANGE": {
                "category": "movement",
                "description": "Walks to the Grand Exchange",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "dreambot_api_mapping": {
                    "class": "Walking",
                    "method": "walkToGrandExchange",
                    "parameters": []
                }
            },
            "IF_PLAYER_IS_MOVING": {
                "category": "movement",
                "description": "Conditional that checks if the player is moving",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Players.getLocal()",
                    "method": "isMoving",
                    "parameters": []
                }
            },
            "IF_PLAYER_IS_NOT_MOVING": {
                "category": "movement",
                "description": "Conditional that checks if the player is not moving",
                "can_be_root": True,
                "valid_parents": ["root", "IF_*", "WHILE_*", "AND_BRANCH", "OR_BRANCH"],
                "properties": {
                    "required": [],
                    "optional": []
                },
                "valid_children": ["*"],
                "dreambot_api_mapping": {
                    "class": "Players.getLocal()",
                    "method": "isMoving",
                    "parameters": [],
                    "logic_inversion": True
                }
            }
        }

def fetch_psc_actions_from_github(github_url: str) -> List[Dict[str, Any]]:
    """
    Fetch PSC actions from GitHub repository.
    
    Args:
        github_url: URL to GitHub repository with PSC actions
    
    Returns:
        List of action dictionaries
    """
    # This is a placeholder that would need to be implemented with requests
    # to fetch real data from the GitHub repository
    print(f"This function would fetch PSC actions from {github_url}")
    print("For now, returning placeholder data")
    
    # Return placeholder data
    return [
        {
            "id": "BANK_DEPOSIT_ALL",
            "properties": {}
        },
        {
            "id": "IF_INVENTORY_CONTAINS",
            "properties": {
                "Filter Item By": {
                    "class": "Item",
                    "type": "NAME",
                    "operator": "EQUALS",
                    "value": "Bones"
                }
            },
            "children": [
                {
                    "id": "BANK_DEPOSIT_ITEM",
                    "properties": {
                        "Filter Item By": {
                            "class": "Item",
                            "type": "NAME",
                            "operator": "EQUALS",
                            "value": "Bones"
                        },
                        "Amount": "All"
                    }
                }
            ]
        }
    ]

def main():
    """Main entry point for the library generator."""
    parser = argparse.ArgumentParser(description="Generate standardized PSC libraries")
    parser.add_argument("--output-dir", default="libraries", help="Directory to save generated libraries")
    parser.add_argument("--github-url", help="URL to GitHub repository with PSC actions")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = PSCLibraryGenerator(args.output_dir)
    
    # Fetch GitHub data if URL is provided
    github_data = None
    if args.github_url:
        github_data = fetch_psc_actions_from_github(args.github_url)
    
    # Generate all libraries
    libraries = generator.generate_all_libraries(github_data)
    
    print(f"All libraries generated in {args.output_dir}")

if __name__ == "__main__":
    main()
