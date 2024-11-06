#!/usr/bin/env python3
import os
import sys

def is_text_file(file_path):
    text_extensions = {'.py', '.md', '.html', '.js', '.css', '.json', '.txt', '.ipynb', '.yaml', '.yml'}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in text_extensions

def print_file_contents(file_path, prefix, max_lines=None):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content_lines = content.splitlines()
        if max_lines is not None and len(content_lines) > max_lines:
            content_lines = content_lines[:max_lines] + ["... (truncated)"]
        if content_lines:
            print(f"{prefix}    └── Contents of {os.path.basename(file_path)}:")
            for line in content_lines:
                line = line.replace('\t', '    ')
                print(f"{prefix}        {line}")
        else:
            print(f"{prefix}    └── [Empty File]")
    except Exception as e:
        print(f"{prefix}    └── [Cannot display contents: {e}]")

def should_include_file(file_path, include_dirs, include_files, exclude_dirs, exclude_dir_names):
    abs_path = os.path.abspath(file_path)
    
    if abs_path in include_files:
        return True

    for include_dir in include_dirs:
        abs_include = os.path.abspath(include_dir)
        if abs_path.startswith(abs_include):
            for abs_exclude in exclude_dirs:
                if abs_path.startswith(abs_exclude):
                    return False
            dir_path = os.path.dirname(abs_path)
            while dir_path != os.path.dirname(dir_path):
                dir_name = os.path.basename(dir_path)
                if dir_name in exclude_dir_names:
                    return False
                dir_path = os.path.dirname(dir_path)
            return True
    return False

def print_tree(root_dir, prefix="", include_dirs=None, include_files=None, exclude_dirs=None, exclude_dir_names=None, max_lines=None):
    if include_dirs is None:
        include_dirs = set()
    if include_files is None:
        include_files = set()
    if exclude_dirs is None:
        exclude_dirs = set()
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

        if os.path.isdir(path):
            if entry in exclude_dir_names:
                continue

            abs_path = os.path.abspath(path)
            if abs_path in exclude_dirs:
                continue

            new_prefix = prefix + ("    " if is_last else "│   ")

            if abs_path in include_dirs:
                print_tree(path, new_prefix, include_dirs, include_files, exclude_dirs, exclude_dir_names, max_lines)
            else:
                print_tree_without_contents(path, new_prefix, exclude_dir_names)
                
        elif os.path.isfile(path):
            # Special condition to always include scripts.js
            if os.path.basename(path) == 'scripts.js':
                print_file_contents(path, prefix, max_lines)
            elif should_include_file(path, include_dirs, include_files, exclude_dirs, exclude_dir_names):
                if is_text_file(path):
                    print_file_contents(path, prefix, max_lines)
                else:
                    print(f"{prefix}    └── [Binary or Unsupported File]")

def print_tree_without_contents(root_dir, prefix="", exclude_dir_names=None):
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

        if os.path.isdir(path):
            if entry in exclude_dir_names:
                continue

            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree_without_contents(path, new_prefix, exclude_dir_names)

def main():
    if len(sys.argv) > 1:
        root_directory = sys.argv[1]
    else:
        root_directory = "."

    if not os.path.exists(root_directory):
        print(f"Error: The directory '{root_directory}' does not exist.")
        sys.exit(1)

    include_dirs = {
        os.path.abspath(os.path.join(root_directory, "app")),
        os.path.abspath(os.path.join(root_directory, "app", "routes")),
        os.path.abspath(os.path.join(root_directory, "app", "services")),
        os.path.abspath(os.path.join(root_directory, "app", "templates")),
        # Removed app/static/js from include_dirs
    }

    include_files = {
        os.path.abspath(os.path.join(root_directory, "config.py")),
        # Removed app/static/js/scripts.js from include_files
    }

    exclude_dirs = {
        os.path.abspath(os.path.join(root_directory, "app", "static"))  # Exclude app/static/
    }

    exclude_dir_names = {
        ".ipynb_checkpoints",
        "__pycache__",
        "node_modules",
        ".git",
        ".pytest_cache",
        "logs"
    }

    MAX_LINES_PER_FILE = None  # Set to None for no limit

    print(".")
    print_tree(
        root_directory,
        include_dirs=include_dirs,
        include_files=include_files,
        exclude_dirs=exclude_dirs,
        exclude_dir_names=exclude_dir_names,
        max_lines=MAX_LINES_PER_FILE
    )

if __name__ == "__main__":
    main()