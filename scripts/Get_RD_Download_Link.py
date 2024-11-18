#!/usr/bin/env python
# coding: utf-8

import sys
import os
import subprocess
import json
import requests
import argparse
import time
import tempfile
import traceback

# Add project root to Python path before importing from app.config
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.append(project_root)

from app.config import Config  # Import Config to access API key and other settings

# Define the path to the 'video_extensions.json' file relative to the project root
video_extensions_path = os.path.join(project_root, 'app', 'static', 'video_extensions.json')

# Load video extensions from JSON file
try:
    with open(video_extensions_path, 'r') as f:
        video_extensions = json.load(f)["video_extensions"]
except FileNotFoundError:
    print(f"Error: {video_extensions_path} not found.", file=sys.stderr)
    sys.exit(1)

# Function to call the Get_RD_Cached_Link script
def get_rd_cached_links(query, limit):
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to Get_RD_Cached_Link.py within the same directory
    cached_link_script = os.path.join(script_dir, 'Get_RD_Cached_Link.py')

    # Ensure the path to the script is correct before running
    if not os.path.exists(cached_link_script):
        print(f"Error: Script {cached_link_script} not found.", file=sys.stderr)
        return [], None

    # Create a temporary file to store execution time
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_timefile:
        temp_timefile_path = temp_timefile.name

    # Prepare environment variables
    env = os.environ.copy()

    # Run the subprocess with the correct path and Python interpreter
    try:
        result = subprocess.run(
            [sys.executable, cached_link_script, query, str(limit), '--timefile', temp_timefile_path],
            capture_output=True,
            text=True,
            cwd=script_dir,  # Set the working directory to script_dir
            env=env
        )

        # Capture and print any stderr output
        if result.stderr.strip():
            print(f"Subprocess stderr: {result.stderr}", file=sys.stderr)

        # Read execution time from temp file
        try:
            with open(temp_timefile_path, 'r') as f:
                execution_time = float(f.read())
        except Exception as e:
            print(f"Error: Failed to read execution time from temp file: {e}", file=sys.stderr)
            execution_time = None
    except Exception as e:
        print(f"Error: An error occurred while running {cached_link_script}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        execution_time = None
    finally:
        if os.path.exists(temp_timefile_path):
            os.unlink(temp_timefile_path)

    if result.returncode != 0:
        print(f"Subprocess error: {result.stderr}", file=sys.stderr)
        return [], execution_time

    try:
        output = result.stdout.strip()
        if not output:
            print("No results found.", file=sys.stderr)
            return [], execution_time
        else:
            results = json.loads(output)
            return results, execution_time  # Return the results and execution time
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from subprocess: {e}", file=sys.stderr)
        print(f"Subprocess stdout: {result.stdout}", file=sys.stderr)
        return [], execution_time

# Function to add the magnet link to Real-Debrid
def add_magnet(magnet_link):
    headers = {'Authorization': f'Bearer {Config.REAL_DEBRID_API_KEY}'}
    response = requests.post(
        'https://api.real-debrid.com/rest/1.0/torrents/addMagnet',
        headers=headers,
        data={'magnet': magnet_link}
    )
    if response.status_code == 201:
        return response.json().get('id')
    else:
        print(f"Failed to add magnet link: {response.text}", file=sys.stderr)
    return None

# Function to select all files from the added torrent
def select_files(torrent_id):
    headers = {'Authorization': f'Bearer {Config.REAL_DEBRID_API_KEY}'}
    response = requests.post(
        f'https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}',
        headers=headers,
        data={'files': 'all'}
    )
    if response.status_code == 204:
        return True
    else:
        print(f"Failed to select files for torrent {torrent_id}: {response.text}", file=sys.stderr)
    return False

# Function to retrieve download links from Real-Debrid
def get_torrent_info(torrent_id):
    headers = {'Authorization': f'Bearer {Config.REAL_DEBRID_API_KEY}'}
    response = requests.get(
        f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
        headers=headers
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve torrent info for {torrent_id}: {response.text}", file=sys.stderr)
    return {}

# Function to unrestrict the download links
def unrestrict_links(links):
    headers = {'Authorization': f'Bearer {Config.REAL_DEBRID_API_KEY}'}
    unrestricted_links = []
    for link in links:
        response = requests.post(
            'https://api.real-debrid.com/rest/1.0/unrestrict/link',
            headers=headers,
            data={'link': link}
        )
        if response.status_code == 200:
            unrestricted_links.append(response.json().get('download'))
        else:
            print(f"Failed to unrestrict link: {link}", file=sys.stderr)
    return unrestricted_links

# Function to check if a file is a video based on its extension
def is_video_file(file_name):
    return any(file_name.lower().endswith(ext) for ext in video_extensions)

# Function to format file size from bytes to human-readable format
def format_file_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"

# Main function
def main():
    parser = argparse.ArgumentParser(description="Search Real-Debrid cached torrents and retrieve download links.")
    parser.add_argument('search_query', help="Search query for Real-Debrid cached torrents")
    parser.add_argument('--limit', type=int, default=10, help="Number of results to return (default: 10)")
    parser.add_argument('--timefile', type=str, help="Path to the temp file to write execution time")
    args = parser.parse_args()

    # Print the Python interpreter being used to stderr
    print(f"Main script is using Python interpreter: {sys.executable}", file=sys.stderr)

    start_time = time.perf_counter()

    try:
        # Retrieve cached links
        cached_links, get_rd_cached_links_time = get_rd_cached_links(args.search_query, args.limit)
        if cached_links is None:
            cached_links = []  # Default to empty list if None is returned

        # Prepare the output as JSON
        final_output = []
        processed_torrents = set()  # To avoid duplicate torrents

        for cached_link in cached_links:
            torrent_name = cached_link.get('title', 'Unknown Title')
            categories = cached_link.get('categories', [])
            magnet_link = cached_link.get('magnet_link')
            infohash = cached_link.get('infohash')

            if not magnet_link or infohash in processed_torrents:
                continue  # Skip if no magnet link or duplicate torrent

            processed_torrents.add(infohash)

            # Add magnet to Real-Debrid and select files
            torrent_id = add_magnet(magnet_link)
            if torrent_id and select_files(torrent_id):
                torrent_info = get_torrent_info(torrent_id)
                unrestricted_download_links = unrestrict_links(torrent_info.get('links', []))

                # Group files with video files only
                torrent_files = []
                for file_info, unrestricted_link in zip(torrent_info.get('files', []), unrestricted_download_links):
                    file_name = file_info['path'].lstrip('/')
                    file_size = format_file_size(file_info['bytes'])
                    if is_video_file(file_name):
                        torrent_files.append({
                            'File Name': file_name,
                            'File Size': file_size,
                            'Download Link': unrestricted_link
                        })
                if torrent_files:
                    final_output.append({
                        'Torrent Name': torrent_name,
                        'Categories': categories,
                        'Files': torrent_files
                    })
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        final_output = []  # Output empty list in case of error
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        if args.timefile:
            try:
                with open(args.timefile, 'w') as f:
                    f.write(f"{duration}")
            except Exception as e:
                print(f"Error: Failed to write execution time to {args.timefile}: {e}", file=sys.stderr)

        if get_rd_cached_links_time is not None:
            print(f"Get_RD_Cached_Link.py ran in {get_rd_cached_links_time:.2f} seconds", file=sys.stderr)

    # Print final output as JSON to stdout
    print(json.dumps(final_output, indent=4))

if __name__ == "__main__":
    main()
