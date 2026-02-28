# app/services/file_helper.py

import os
import json
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class FileHelper:
    """Helper class for handling file-related tasks, such as loading video extensions and formatting file sizes."""

    _video_extensions = None
    _category_mapping = None

    @classmethod
    def load_video_extensions(cls):
        """Load video extensions from a JSON file (cached after first load)."""
        if cls._video_extensions is not None:
            return cls._video_extensions
        try:
            static_folder_path = os.path.join(current_app.root_path, 'static')
            video_extensions_path = os.path.join(static_folder_path, 'video_extensions.json')
            with open(video_extensions_path, 'r') as f:
                cls._video_extensions = json.load(f).get("video_extensions", [])
            return cls._video_extensions
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading video extensions from video_extensions.json: {e}")
            return []

    @classmethod
    def load_category_mapping(cls):
        """Load category mapping from a JSON file (cached after first load)."""
        if cls._category_mapping is not None:
            return cls._category_mapping
        try:
            static_folder_path = os.path.join(current_app.root_path, 'static')
            category_mapping_path = os.path.join(static_folder_path, 'category_mapping.json')
            with open(category_mapping_path, 'r') as f:
                cls._category_mapping = {int(k): v for k, v in json.load(f).items()}
            return cls._category_mapping
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading category mapping from category_mapping.json: {e}")
            return {}

    @staticmethod
    def is_video_file(file_name):
        """Check if the given file is a video based on its extension."""
        video_extensions = FileHelper.load_video_extensions()
        return any(file_name.lower().endswith(ext) for ext in video_extensions)

    @staticmethod
    def format_file_size(size_in_bytes):
        """Convert bytes to a human-readable string."""
        if not isinstance(size_in_bytes, (int, float)) or size_in_bytes < 0:
            return "0.00 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"

    @staticmethod
    def simplify_filename(file_name):
        """Replace dots with spaces in a filename, preserving the file extension."""
        parts = file_name.rsplit('.', 1)
        if len(parts) > 1:
            simplified = parts[0].replace('.', ' ')
            simplified += f".{parts[1]}"
        else:
            simplified = file_name.replace('.', ' ')
        return simplified
