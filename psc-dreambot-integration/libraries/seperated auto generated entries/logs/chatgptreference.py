import json
import os

# Function to load JSON data with error handling
def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error in file: {file_path}\nError Details: {e}")
        return {}
    except FileNotFoundError:
        print(f"❌ File Not Found: {file_path}")
        return {}

# File paths
hierarchy_path = r'D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\action_hierarchy_library.json'
actions_list_path = r'D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\comprehensive_actions.json'
missing_actions_log_path = r'D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\missing_actions_log.json'

# Load data
hierarchy_library = load_json(hierarchy_path)
comprehensive_list = load_json(actions_list_path)

# Flatten comprehensive actions list
comprehensive_actions = set()
for category, actions in comprehensive_list.get('actions', {}).items():
    if isinstance(actions, dict):
        for sub_actions in actions.values():
            comprehensive_actions.update(sub_actions)
    elif isinstance(actions, list):
        comprehensive_actions.update(actions)

# Extract existing actions from the hierarchy library
existing_actions = set(hierarchy_library.get('actions', {}).keys())

# Identify missing actions
missing_actions = comprehensive_actions - existing_actions

# Log missing actions
if missing_actions:
    with open(missing_actions_log_path, 'w', encoding='utf-8') as log_file:
        json.dump({"missing_actions": sorted(list(missing_actions))}, log_file, indent=4)
    print(f"✅ Missing actions logged successfully: {len(missing_actions)} actions found missing.")
else:
    print("✅ All actions are present. No missing actions found.")

