#!/usr/bin/env python
# coding: utf-8

import os
import re
import hashlib
import cloudscraper
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import bencodepy  # Required for torrent file decoding
import math  # For bytes_to_human_readable
import json  # For category mapping
import argparse
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import configuration class
try:
    from app.config import Config
except ImportError as e:
    print(f"ERROR: Could not import configuration: {e}", file=sys.stderr)
    sys.exit(1)

# Access configuration values from the class
JACKETT_URL = Config.JACKETT_URL
JACKETT_API_KEY = Config.JACKETT_API_KEY

if not JACKETT_URL or not JACKETT_API_KEY:
    print("ERROR: JACKETT_URL and JACKETT_API_KEY must be set in configuration or environment variables.", file=sys.stderr)
    sys.exit(1)

# Namespace for torznab XML parsing
TORZNAB_NS = {'torznab': 'http://torznab.com/schemas/2015/feed'}

def load_environment() -> (str, str):
    """Load configuration variables from app/config.py."""
    if not JACKETT_URL or not JACKETT_API_KEY:
        print("ERROR: Both JACKETT_URL and JACKETT_API_KEY must be defined in app/config.py.", file=sys.stderr)
        sys.exit(1)

    if not JACKETT_URL.startswith(("http://", "https://")):
        print("ERROR: JACKETT_URL must start with http:// or https://", file=sys.stderr)
        sys.exit(1)

    return JACKETT_API_KEY, JACKETT_URL

def create_session():
    session = cloudscraper.create_scraper()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return session

def extract_infohash_from_magnet(magnet_link: str) -> Optional[str]:
    """Extract the infohash from a magnet link."""
    match = re.search(r'urn:btih:([A-Fa-f0-9]{32,40})', magnet_link)
    return match.group(1).lower() if match else None

def load_category_mapping(file_path: str) -> Dict[int, str]:
    """Load category mapping from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        print(f"ERROR: Failed to load category mapping from {file_path}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

def get_infohash_from_torrent_url(torrent_urls: List[str]) -> Dict[str, Optional[str]]:
    """Retrieve infohashes from a list of .torrent URLs concurrently."""
    max_retries = 5
    delay_between_retries = 5  # seconds
    results = {}

    session = create_session()

    def fetch_infohash(torrent_url: str):
        for attempt in range(1, max_retries + 1):
            try:
                response = session.get(torrent_url, allow_redirects=False, timeout=20)
                if response.status_code == 404:
                    return None
                if response.status_code in (301, 302):
                    redirect_url = response.headers.get('Location', '')
                    if redirect_url.startswith('magnet:?'):
                        return extract_infohash_from_magnet(redirect_url)
                elif response.status_code == 200:
                    torrent_content = response.content
                    torrent_data = bencodepy.decode(torrent_content)
                    info_dict = torrent_data.get(b'info')
                    if info_dict:
                        encoded_info = bencodepy.encode(info_dict)
                        return hashlib.sha1(encoded_info).hexdigest()
            except Exception:
                time.sleep(delay_between_retries)

        return None

    # Fetch infohashes concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_infohash, url): url for url in torrent_urls}
        for future in futures:
            results[futures[future]] = future.result()

    return results

def search_jackett(
    api_key: str,
    base_url: str,
    query: str,
    limit: int = 10
) -> Optional[bytes]:
    """Search Jackett for the given query across all configured indexers."""
    url = f"{base_url}/api/v2.0/indexers/all/results/torznab/api"
    params = {
        'apikey': api_key,
        't': 'search',
        'q': query,
        'limit': limit
    }

    max_retries = 5
    delay_between_retries = 2  # seconds

    session = create_session()

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params)
            response.raise_for_status()
            return response.content
        except cloudscraper.exceptions.CloudflareChallengeError:
            if attempt < max_retries:
                time.sleep(delay_between_retries)
            else:
                print("ERROR: Cloudflare challenge could not be bypassed after multiple attempts.", file=sys.stderr)
                return None
        except Exception as e:
            if attempt < max_retries:
                time.sleep(delay_between_retries)
            else:
                print(f"ERROR: Failed to perform search after {max_retries} attempts: {e}", file=sys.stderr)
                return None

    return None

def parse_results(xml_data: bytes) -> List[Dict]:
    """Parse XML data and extract relevant information."""
    results = []
    try:
        root = ET.fromstring(xml_data)
        items = root.findall('./channel/item')

        for idx, item in enumerate(items):
            title_elem = item.find('title')
            title = title_elem.text if title_elem is not None else "Unknown Title"

            seeders_elem = item.find('./torznab:attr[@name="seeders"]', TORZNAB_NS)
            seeders = seeders_elem.attrib['value'] if seeders_elem is not None else "0"

            leechers_elem = item.find('./torznab:attr[@name="peers"]', TORZNAB_NS)
            leechers = leechers_elem.attrib['value'] if leechers_elem is not None else "0"

            categories_elems = item.findall('./torznab:attr[@name="category"]', TORZNAB_NS)
            categories = [cat.attrib['value'] for cat in categories_elems]

            link_elem = item.find('link')
            link = link_elem.text if link_elem is not None else "Unknown Link"

            size_elem = item.find('size')
            size = str(size_elem.text) if size_elem is not None else "0"

            # Ignore links from 1337x
            if "1337x" in link:
                continue

            infohash_elem = item.find('./torznab:attr[@name="infohash"]', TORZNAB_NS)
            infohash = None

            if link.startswith("magnet:"):
                infohash = extract_infohash_from_magnet(link)
            elif infohash_elem is not None:
                infohash = infohash_elem.attrib['value']
            elif not link.startswith("magnet:"):
                for retry_attempt in range(2):
                    infohash = get_infohash_from_torrent_url([link])[link]
                    if infohash:
                        break
                    time.sleep(2)

            if not infohash:
                continue

            torznab_attrs = {attr.attrib.get('name'): attr.attrib.get('value') for attr in item.findall('./torznab:attr', TORZNAB_NS)}

            results.append({
                'title': title,
                'seeders': seeders,
                'leechers': leechers,  # Use 'leechers' here
                'categories': categories,
                'infohash': infohash,
                'size': size,
                'torznab_attrs': torznab_attrs
            })

        return results
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML data: {e}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while parsing results: {e}", file=sys.stderr)

    return []

def bytes_to_human_readable(size_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def main():
    """Main function to execute the search."""
    parser = argparse.ArgumentParser(description='Search Jackett for torrent information.')
    parser.add_argument('--query', type=str, default='alien romulus 2160p', help='Search query')
    parser.add_argument('--limit', type=int, default=10, help='Limit of results')
    parser.add_argument('--timefile', type=str, help='Path to the temp file to write execution time')
    args = parser.parse_args()

    query = args.query
    limit = args.limit

    start_time = time.perf_counter()

    try:
        api_key, base_url = load_environment()

        # Load category mapping
        static_folder_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
        category_mapping_path = os.path.join(static_folder_path, 'category_mapping.json')

        category_mapping = load_category_mapping(category_mapping_path)

        xml_data = search_jackett(api_key, base_url, query, limit)
        if xml_data:
            results = parse_results(xml_data)
            if results:
                output_data = []
                for result in results:
                    category_names = []
                    for cat in result['categories']:
                        try:
                            category_id = int(cat)
                            category_name = category_mapping.get(category_id)
                            if category_name:
                                category_names.append(category_name)
                        except ValueError:
                            print(f"WARNING: Unable to convert category '{cat}' to integer.", file=sys.stderr)

                    result_data = {
                        "title": result.get('title', 'Unknown Title'),
                        "seeders": result.get('seeders', '0'),
                        "leechers": result.get('leechers', '0'),  # Use .get() with default value
                        "categories": category_names,
                        "infohash": result.get('infohash'),
                        "size": bytes_to_human_readable(int(result.get('size', '0'))),
                        "byte_size": result.get('size', '0'),
                        "torznab_attributes": result.get('torznab_attrs', {})
                    }
                    output_data.append(result_data)

                # Output results as JSON
                print(json.dumps(output_data, indent=4))
            else:
                # No results found
                print("No results found.", file=sys.stderr)
                print("[]")  # Print empty JSON array to stdout
        else:
            # Failed to perform the search
            print("Failed to perform the search.", file=sys.stderr)
            print("[]")  # Print empty JSON array to stdout
    except Exception as e:
        print(f"ERROR: An error occurred during the execution: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("[]")  # Print empty JSON array to stdout
        sys.exit(1)  # Exit with a non-zero code to indicate failure
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        if args.timefile:
            try:
                with open(args.timefile, 'w') as f:
                    f.write(f"{duration}")
            except Exception as e:
                print(f"ERROR: Failed to write execution time to {args.timefile}: {e}", file=sys.stderr)
                # Optionally, you can choose to exit with an error code here
                # sys.exit(1)

        # Log the execution time
        print(f"jackett_search_v2.py ran in {duration:.2f} seconds", file=sys.stderr)


if __name__ == "__main__":
    main()
