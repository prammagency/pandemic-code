import json

# Path to the action hierarchy library file
action_library_path = r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\action_hierarchy_library.json"
output_log_path = r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\auto_generated_log.json"

def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error in file: {file_path}\nError Details: {e}")
        exit()

def log_auto_generated_entries():
    data = load_json(action_library_path)

    auto_generated_entries = {}

    for action, details in data.get("actions", {}).items():
        if "[AUTO-GENERATED]" in details.get("description", ""):
            auto_generated_entries[action] = details

    with open(output_log_path, 'w', encoding='utf-8') as log_file:
        json.dump(auto_generated_entries, log_file, indent=4)

    print(f"✅ Auto-generated entries logged: {len(auto_generated_entries)} entries found.")

if __name__ == "__main__":
    log_auto_generated_entries()
