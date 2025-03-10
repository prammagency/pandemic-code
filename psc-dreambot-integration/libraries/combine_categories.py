import os
import shutil

# Paths
non_auto_generated_path = r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\seperated auto generated entries\separated_non_auto_generated_entries\categories"
auto_generated_path = r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\seperated auto generated entries\separated_auto_generated_entries\categories"
combined_path = r"D:\RS_AI\pandemic-code\psc-dreambot-integration\libraries\combined_categories"

# Create combined folder path if it doesn't exist
os.makedirs(combined_path, exist_ok=True)

# Extract files
non_auto_files = {file.replace(".json", ""): file for file in os.listdir(non_auto_generated_path) if file.endswith(".json")}
auto_files = {file.replace(".json", ""): file for file in os.listdir(auto_generated_path) if file.endswith(".json")}

# Combine or Separate as Required
for category in set(non_auto_files.keys()).union(auto_files.keys()):
    category_folder = os.path.join(combined_path, category)
    os.makedirs(category_folder, exist_ok=True)
    
    # Copy Non Auto Generated Files
    if category in non_auto_files:
        shutil.copy(
            os.path.join(non_auto_generated_path, non_auto_files[category]),
            os.path.join(category_folder, f"{category} - Non Auto Generated.json")
        )
    
    # Copy Auto Generated Files
    if category in auto_files:
        shutil.copy(
            os.path.join(auto_generated_path, auto_files[category]),
            os.path.join(category_folder, f"{category} - Auto Generated.json")
        )

print("✅ Successfully combined and organized all categories!")
