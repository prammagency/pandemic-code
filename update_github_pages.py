import os
import shutil
import subprocess
import urllib.parse

# Define the root repository path
repo_path = r"D:\RS_AI\pandemic-code"

def clean_old_indexes(directory):
    """ Deletes old index.html files in all directories. """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower() == "index.html":
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"🗑️ Deleted old index: {file_path}")

def generate_index(directory):
    """ Generates a new index.html listing all files and subdirectories. """
    items = sorted(os.listdir(directory))

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Directory Listing</title>
</head>
<body>
  <h1>Available Files & Folders</h1>
  <ul>
"""

    for item in items:
        item_path = os.path.join(directory, item)
        encoded_name = urllib.parse.quote(item)  # Encode spaces for URLs

        if os.path.isdir(item_path):
            html_content += f'    <li><a href="{encoded_name}/">{item}/</a></li>\n'
        elif os.path.isfile(item_path):
            html_content += f'    <li><a href="{encoded_name}">{item}</a></li>\n'

    html_content += """  </ul>
</body>
</html>"""

    # Save index.html in the directory
    index_path = os.path.join(directory, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Generated new index.html in {directory}")

def create_new_indexes(root_dir):
    """ Generates index.html in every folder and the root directory for GitHub Pages. """
    for root, dirs, _ in os.walk(root_dir):
        for directory in dirs:
            generate_index(os.path.join(root, directory))
    generate_index(root_dir)  # Generate the root index.html

def push_to_github():
    """ Commits and pushes the updated index.html files to GitHub. """
    os.chdir(repo_path)
    
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "Updated index.html for GitHub Pages"])
    subprocess.run(["git", "push", "origin", "main"])
    
    print(f"🚀 Successfully pushed updates to GitHub!")

if __name__ == "__main__":
    print("🗑️ Cleaning old index files...")
    clean_old_indexes(repo_path)

    print("📂 Scanning repository and generating new index files...")
    create_new_indexes(repo_path)

    print("🚀 Pushing updates to GitHub...")
    push_to_github()

    print(f"🎉 Done! Visit: https://prammagency.github.io/pandemic-code/")
