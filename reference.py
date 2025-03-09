import os
import json
import re

# Paths to directories and main JSON
base_dir = r"D:\RS_AI\pandemic-code"
paths = [
    os.path.join(base_dir, "enriched_code - Pandemics code"),
    os.path.join(base_dir, "Pandemic coding docs - original - Not Cleaned"),
    os.path.join(base_dir, "cleaned_docs - pandemic URL docs"),
    os.path.join(base_dir, "Dreambot Api Docs- Classes_Enums"),
]
primary_map_path = os.path.join(base_dir, "upodated librbaries", "action ids", "ActionID_CategoryMap.json")

# Load and clean JSON
def load_clean_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error in file: {file_path}")
        print(f"Error Details: {e}")
        return {}

# Extract potential action IDs from text files
def extract_action_ids_from_text(text):
    pattern = re.compile(r'"([A-Z_]+)"')
    return set(pattern.findall(text))

# Load primary action map
primary_action_map = load_clean_json(primary_map_path)

# Collect existing actions from the main map
existing_actions = set(primary_action_map.keys())

# Search for missing actions
missing_actions = set()

# Cross-reference with all source files
for path in paths:
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".json") or file.endswith(".txt") or file.endswith(".psc"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        detected_actions = extract_action_ids_from_text(content)
                        for action in detected_actions:
                            if action not in existing_actions:
                                missing_actions.add(action)
                except Exception as e:
                    print(f"⚠️ Error reading file {file_path}: {e}")

# Generate Missing Actions Report
missing_actions_path = os.path.join(base_dir, "missing_actions_report.json")
with open(missing_actions_path, 'w', encoding='utf-8') as f:
    json.dump(list(missing_actions), f, indent=4)

print(f"✅ Process Complete! {len(missing_actions)} missing actions found.")
print(f"📝 Missing actions report saved at: {missing_actions_path}")


