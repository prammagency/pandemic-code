import json
import os

json_files = [
    r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\ActionID_CategoryMap- chatgpt (1).json",
    r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\libraries\action_hierarchy_library.json",
    r"D:\RS_AI\pandemic-code\Dreambot Api Docs- Classes_Enums\structured_entities.json"
]

def validate_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            json.load(file)
            print(f"✅ JSON valid: {filepath}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error ({filepath}): {e}")
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")

def main():
    for file_path in json_files:
        validate_json(file_path)

if __name__ == "__main__":
    main()
