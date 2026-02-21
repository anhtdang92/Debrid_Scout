from flask import Blueprint, render_template, request, current_app, jsonify
import logging
import os
import requests
import platform
import subprocess
from app.services.real_debrid import RealDebridService, RealDebridError

torrent_bp = Blueprint('torrent', __name__)
logger = logging.getLogger(__name__)

@torrent_bp.route('/rd_manager')
def rd_manager():
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    account_info = None
    real_debrid_api_error = None
    page = int(request.args.get('page', 1))
    torrents_per_page = 100
    torrents = []
    total_pages = 1

    if REAL_DEBRID_API_KEY:
        real_debrid_service = RealDebridService(api_key=REAL_DEBRID_API_KEY)
        account_info = real_debrid_service.get_account_info()

        if account_info:
            all_torrents = real_debrid_service.get_all_torrents()
            total_torrents = len(all_torrents)
            total_pages = (total_torrents + torrents_per_page - 1) // torrents_per_page
            torrents = all_torrents[(page - 1) * torrents_per_page: page * torrents_per_page]
        else:
            real_debrid_api_error = "Could not retrieve account information from Real-Debrid."
    else:
        real_debrid_api_error = "API key is missing."

    return render_template(
        'rd_manager.html',
        account_info=account_info,
        real_debrid_api_error=real_debrid_api_error,
        torrents=torrents,
        current_page=page,
        total_pages=total_pages
    )

@torrent_bp.route('/delete_torrent/<torrent_id>', methods=['DELETE'])
def delete_torrent(torrent_id):
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    headers = {'Authorization': f'Bearer {REAL_DEBRID_API_KEY}'}

    try:
        response = requests.delete(
            f'https://api.real-debrid.com/rest/1.0/torrents/delete/{torrent_id}', headers=headers
        )
        response.raise_for_status()
        logger.info(f"Torrent with ID {torrent_id} deleted successfully.")
        return jsonify({'status': 'success', 'message': 'Torrent deleted successfully'})

    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting torrent from Real-Debrid API: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete torrent'}), 500

@torrent_bp.route('/stream_vlc', methods=['POST'])
def stream_vlc():
    logger.debug("Received request at /stream_vlc")
    data = request.get_json()
    logger.debug(f"Request data: {data}")

    # Check if data is None
    if data is None:
        logger.warning("No JSON data received.")
        return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400

    link = data.get('link')
    if not link:
        logger.warning("No link provided in /stream_vlc request.")
        return jsonify({'status': 'error', 'message': 'No link provided'}), 400

    try:
        # Determine VLC path based on the operating system
        if platform.system() == 'Windows':
            vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
        elif platform.system() == 'Darwin':
            vlc_path = "/Applications/VLC.app/Contents/MacOS/VLC"
        else:
            vlc_path = "/usr/bin/vlc"

        # Validate VLC path
        if not os.path.exists(vlc_path):
            logger.error("VLC executable not found at specified path.")
            return jsonify({'status': 'error', 'message': 'VLC executable not found'}), 500

        # Launch VLC
        subprocess.Popen([vlc_path, link])
        logger.info(f"VLC launched successfully with link: {link}")
        return jsonify({'status': 'success', 'message': 'VLC launched successfully.'})

    except Exception as e:
        logger.error(f"Error launching VLC: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@torrent_bp.route('/unrestrict_link', methods=['POST'])
def unrestrict_link():
    data = request.get_json()
    logger.debug(f"Received data: {data}")

    original_link = data.get('link')
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')

    logger.debug(f"Original Link: {original_link}")
    logger.debug(f"API Key: {api_key is not None}")  # Log if API key is present

    if not original_link or not api_key:
        logger.warning("Missing link or API key in unrestrict_link")
        return jsonify({'error': 'Missing link or API key'}), 400

    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {'link': original_link}

    try:
        logger.debug("Sending request to Real-Debrid")
        response = requests.post('https://api.real-debrid.com/rest/1.0/unrestrict/link', headers=headers, data=payload)
        response.raise_for_status()  # This will raise an error for HTTP errors
        unrestricted_data = response.json()
        logger.debug(f"Response from Real-Debrid: {unrestricted_data}")
        return jsonify({'unrestricted_link': unrestricted_data.get('download', 'Link not found')})
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in unrestrict_link: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@torrent_bp.route('/torrents/<torrent_id>', methods=['GET'])
def get_torrent_details(torrent_id):
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    headers = {'Authorization': f'Bearer {REAL_DEBRID_API_KEY}'}

    try:
        response = requests.get(f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}', headers=headers)
        response.raise_for_status()
        torrent_data = response.json()

        logger.debug(f"Raw torrent data for ID {torrent_id}: {torrent_data}")

        files = torrent_data.get('files', [])
        links = torrent_data.get('links', [])

        logger.debug(f"Total files received: {len(files)}")
        logger.debug(f"Total links received: {len(links)}")

        selected_files = [file for file in files if file.get('selected') == 1]
        logger.debug(f"Selected files (before sorting): {selected_files}")

        # Initialize RealDebridService
        real_debrid_service = RealDebridService(api_key=REAL_DEBRID_API_KEY)

        # Unrestrict links
        unrestricted_links = []
        for link in links:
            try:
                unrestricted_link = real_debrid_service.unrestrict_link(link)
                unrestricted_links.append(unrestricted_link)
            except RealDebridError as e:
                logger.error(f"Error unrestricting link '{link}': {e}")
                unrestricted_links.append(link)  # Fallback to the original link

        link_mapping = {file['id']: link for file, link in zip(selected_files, unrestricted_links)}

        sorted_files = sorted(selected_files, key=lambda f: f.get('bytes', 0), reverse=True)
        logger.debug(f"Sorted files by size: {sorted_files}")

        processed_files = []
        for file in sorted_files:
            file_id = file.get('id')
            file_name = file.get('path', 'Unknown').split('/')[-1]
            file_size = f"{file.get('bytes', 0) / (1024 * 1024 * 1024):.2f} GB"
            file_link = link_mapping.get(file_id, None)

            processed_files.append({
                "id": file_id,
                "name": file_name,
                "size": file_size,
                "link": file_link
            })
            logger.debug(f"Processed file '{file_name}' with link: {file_link}")

        response_data = {
            "filename": torrent_data.get("filename", "Unknown Filename"),
            "files": processed_files,
            "status": torrent_data.get("status", "Unknown Status"),
            "progress": torrent_data.get("progress", 0),
            "added": torrent_data.get("added"),
            "ended": torrent_data.get("ended")
        }

        logger.debug(f"Response data for torrent {torrent_id}: {response_data}")

        return jsonify(response_data)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching torrent info from Real-Debrid API: {e}")
        return jsonify({'error': 'Failed to retrieve file information from Real-Debrid'}), 500


@torrent_bp.route('/delete_torrents', methods=['POST'])
def delete_torrents():
    data = request.get_json()
    torrent_ids = data.get('torrentIds', [])
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    headers = {'Authorization': f'Bearer {REAL_DEBRID_API_KEY}'}

    if not torrent_ids:
        return jsonify({'status': 'error', 'message': 'No torrent IDs provided'}), 400

    results = {'deleted': [], 'failed': []}

    for torrent_id in torrent_ids:
        try:
            response = requests.delete(
                f'https://api.real-debrid.com/rest/1.0/torrents/delete/{torrent_id}',
                headers=headers
            )
            response.raise_for_status()
            results['deleted'].append(torrent_id)
            logger.info(f"Deleted torrent ID: {torrent_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete torrent ID {torrent_id}: {e}")
            results['failed'].append(torrent_id)

    if results['failed']:
        return jsonify({'status': 'partial_success', 'results': results}), 207  # Multi-status code
    return jsonify({'status': 'success', 'results': results}), 200
