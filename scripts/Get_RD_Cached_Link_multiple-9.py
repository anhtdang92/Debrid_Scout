#!/usr/bin/env python
# coding: utf-8

import subprocess
import os
import json
import requests
import argparse
from dotenv import load_dotenv
import sys  # For handling stderr outputs

# Load environment variables from .env file
load_dotenv()

# Get Real-Debrid API key from environment variables
REAL_DEBRID_API_KEY = os.getenv("REAL_DEBRID_API_KEY")
if not REAL_DEBRID_API_KEY:
    print("ERROR: REAL_DEBRID_API_KEY not found. Make sure it's set correctly in the .env file.", file=sys.stderr)
    sys.exit(1)  # Exit the script if API key is missing

# Function to call Jackett Search script
def call_jackett_vid_search(query: str, limit: int) -> list:
    try:
        # Resolve paths
        script_path = os.path.abspath("scripts/Jackett_Search_v2.py")
        python_path = os.path.join(os.environ['VIRTUAL_ENV'], "Scripts", "python")

        # Construct the command
        command = [
            python_path,
            script_path, "--query", query, "--limit", str(limit)
        ]

        # Include virtual environment variables
        env = os.environ.copy()
        env["PATH"] = os.path.join(os.environ['VIRTUAL_ENV'], "Scripts") + os.pathsep + env["PATH"]

        # Run the command and capture the output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            encoding='utf-8'
        )

        # Check if the command was successful
        if result.returncode == 0:
            output = result.stdout.strip()
            stderr_output = result.stderr.strip()

            if output == "[]" and "No results found." in stderr_output:
                return []
            elif not output:
                return []
            else:
                try:
                    results = json.loads(output)  # Parse JSON output
                    return results
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in Jackett_Search_v2.py output: {e}", file=sys.stderr)
                    return []
        else:
            print("ERROR: Jackett_Search_v2.py encountered an error.", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return []
    except Exception as e:
        print(f"ERROR: An error occurred while calling Jackett_Search_v2.py: {e}", file=sys.stderr)
        return []

# Function to check if a torrent is fully cached on Real-Debrid
def check_if_cached_on_real_debrid(infohash: str, expected_size: str) -> dict:
    result = {
        "infohash": infohash,
        "is_fully_cached": False,
        "magnet_link": f"magnet:?xt=urn:btih:{infohash}"
    }
    try:
        # Convert expected_size to an integer (bytes)
        expected_size = int(expected_size)

        # Construct the URL to query the Real-Debrid API
        url = f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{infohash}"
        headers = {
            "Authorization": f"Bearer {REAL_DEBRID_API_KEY}"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        # Check if the torrent is cached in Real-Debrid
        if data and infohash in data and "rd" in data[infohash]:
            # Calculate the total cached size
            total_cached_size = 0
            for instance in data[infohash]["rd"]:
                for file_key, file_info in instance.items():
                    filesize_str = file_info.get("filesize", "0")
                    try:
                        filesize = int(filesize_str)
                    except ValueError:
                        filesize = 0
                    total_cached_size += filesize

            # Determine if the total cached size meets or exceeds the expected size
            if total_cached_size >= expected_size:
                result["is_fully_cached"] = True

        return result

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request exception while checking cache for {infohash}: {e}", file=sys.stderr)
        return result
    except ValueError as e:
        print(f"ERROR: Value error: {e}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while checking cache for {infohash}: {e}", file=sys.stderr)
        return result

# Main function to search for torrents and check Real-Debrid caching status
def main():
    parser = argparse.ArgumentParser(
        description="Search for torrents using Jackett, check Real-Debrid caching status, and get download links."
    )
    parser.add_argument("search_query", type=str, help="The search query for Jackett.")
    parser.add_argument("result_limit", type=int, help="The limit on the number of search results.")
    args = parser.parse_args()

    search_query = args.search_query
    result_limit = args.result_limit

    # Get the search results from Jackett Search
    search_results = call_jackett_vid_search(search_query, result_limit)

    output_results = []
    processed_infohashes = set()  # To track processed infohashes

    if search_results:
        for result in search_results:
            infohash = result.get("infohash")
            if not infohash:
                continue  # Skip if no infohash

            if infohash in processed_infohashes:
                continue  # Skip duplicate based on infohash

            processed_infohashes.add(infohash)

            byte_size = result.get("byte_size")
            if not byte_size:
                continue  # Skip if byte_size is missing

            categories = result.get("categories", [])
            title = result.get("title", "No Title")

            # Check if the torrent is fully cached on Real-Debrid
            cached_result = check_if_cached_on_real_debrid(infohash, byte_size)
            cached_result["title"] = title
            cached_result["categories"] = categories

            # Optionally include additional fields from the search result
            # For example, seeders, leechers, etc.
            cached_result["seeders"] = result.get("seeders", "0")
            cached_result["leechers"] = result.get("leechers", "0")
            cached_result["size"] = result.get("size", "Unknown")

            # Optionally include torznab_attributes if needed
            torznab_attributes = result.get("torznab_attributes", {})
            if torznab_attributes:
                cached_result["torznab_attributes"] = torznab_attributes

            output_results.append(cached_result)

    # Output results as a single JSON
    print(json.dumps(output_results, indent=4))

if __name__ == "__main__":
    main()
