#!/usr/bin/env python3
import os
import sys

# List of text file extensions
TEXT_EXTENSIONS = {'.py', '.md', '.html', '.js', '.css', '.json', '.txt', '.ipynb', '.yaml', '.yml'}

def is_text_file(file_path):
    _, ext = os.path.splitext(file_path)
    return ext.lower() in TEXT_EXTENSIONS

def print_file_contents(file_path, prefix, max_lines=None):
    """Print the contents of a text file with optional truncation."""
    # Ensure exact matching for static/css
    file_path_abs = os.path.abspath(file_path)
    if "static/css" in file_path_abs.replace("\\", "/"):
        print(f"{prefix}    └── [Contents hidden for {os.path.basename(file_path)}]")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines] + ["... (truncated)"]
        print(f"{prefix}    └── Contents of {os.path.basename(file_path)}:")
        for line in lines:
            print(f"{prefix}        {line.replace(chr(9), '    ')}")
    except Exception as e:
        print(f"{prefix}    └── [Error reading file: {e}]")

def print_tree(root_dir, prefix="", exclude_dir_names=None, max_lines=None):
    """Recursively print the directory tree, focusing only on the app folder."""
    if exclude_dir_names is None:
        exclude_dir_names = set()

    try:
        entries = sorted(os.listdir(root_dir))
    except PermissionError:
        print(f"{prefix}    [Permission Denied]")
        return

    entries_count = len(entries)

    for index, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        is_last = index == (entries_count - 1)
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{entry}")

        if os.path.isdir(path) and entry not in exclude_dir_names:
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(path, new_prefix, exclude_dir_names, max_lines)
        elif os.path.isfile(path) and is_text_file(path):
            print_file_contents(path, prefix, max_lines)

def main():
    root_directory = os.path.abspath("app")  # Focus on the 'app' folder
    if not os.path.exists(root_directory):
        print(f"Error: The directory '{root_directory}' does not exist.")
        sys.exit(1)

    exclude_dir_names = {
        ".ipynb_checkpoints",
        "__pycache__",
        "node_modules",
        ".git",
        ".pytest_cache",
        "logs"
    }

    MAX_LINES_PER_FILE = None  # Set to None for no truncation

    print(".")
    print_tree(
        root_directory,
        exclude_dir_names=exclude_dir_names,
        max_lines=MAX_LINES_PER_FILE
    )

if __name__ == "__main__":
    main()
