from flask import Blueprint, render_template, request, current_app, jsonify
import logging
import os
import shutil
import subprocess
import requests
from app.services.real_debrid import RealDebridService, RealDebridError

# Known install paths for VLC
_VLC_PATHS = [
    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
]

torrent_bp = Blueprint('torrent', __name__)
logger = logging.getLogger(__name__)


@torrent_bp.route('/rd_manager')
def rd_manager():
    # account_info is injected automatically via context processor.
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    real_debrid_api_error = None
    page = int(request.args.get('page', 1))
    torrents_per_page = 100
    torrents = []
    total_pages = 1

    if REAL_DEBRID_API_KEY:
        real_debrid_service = RealDebridService(api_key=REAL_DEBRID_API_KEY)
        all_torrents = real_debrid_service.get_all_torrents()
        total_torrents = len(all_torrents)
        total_pages = (total_torrents + torrents_per_page - 1) // torrents_per_page
        torrents = all_torrents[(page - 1) * torrents_per_page: page * torrents_per_page]
    else:
        real_debrid_api_error = "API key is missing."

    return render_template(
        'rd_manager.html',
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


@torrent_bp.route('/unrestrict_link', methods=['POST'])
def unrestrict_link():
    data = request.get_json()
    original_link = data.get('link')
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')

    if not original_link or not api_key:
        return jsonify({'error': 'Missing link or API key'}), 400

    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {'link': original_link}

    try:
        response = requests.post(
            'https://api.real-debrid.com/rest/1.0/unrestrict/link',
            headers=headers, data=payload
        )
        response.raise_for_status()
        unrestricted_data = response.json()
        return jsonify({'unrestricted_link': unrestricted_data.get('download', 'Link not found')})
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in unrestrict_link: {e}")
        return jsonify({'error': str(e)}), 500


@torrent_bp.route('/torrents/<torrent_id>', methods=['GET'])
def get_torrent_details(torrent_id):
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')
    headers = {'Authorization': f'Bearer {REAL_DEBRID_API_KEY}'}

    try:
        response = requests.get(
            f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
            headers=headers
        )
        response.raise_for_status()
        torrent_data = response.json()

        files = torrent_data.get('files') or []
        links = torrent_data.get('links') or []
        selected_files = [f for f in files if f.get('selected') == 1]

        # Map selected files to their restricted links (do NOT unrestrict here —
        # that's slow and blocks the browser).  The frontend will call
        # /torrent/unrestrict_link on-demand when the user clicks Download.
        link_mapping = {}
        for f, link in zip(selected_files, links):
            fid = f.get('id')
            if fid is not None and link:
                link_mapping[fid] = link

        sorted_files = sorted(selected_files, key=lambda f: f.get('bytes', 0), reverse=True)

        processed_files = []
        for file in sorted_files:
            file_id = file.get('id')
            file_name = file.get('path', 'Unknown').split('/')[-1]
            file_size = f"{file.get('bytes', 0) / (1024 * 1024 * 1024):.2f} GB"
            processed_files.append({
                "id": file_id,
                "name": file_name,
                "size": file_size,
                "link": link_mapping.get(file_id, "")
            })

        return jsonify({
            "filename": torrent_data.get("filename", "Unknown Filename"),
            "files": processed_files,
            "status": torrent_data.get("status", "Unknown Status"),
            "progress": torrent_data.get("progress", 0),
            "added": torrent_data.get("added"),
            "ended": torrent_data.get("ended")
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching torrent info from Real-Debrid API: {e}")
        return jsonify({'error': 'Failed to retrieve file information'}), 500
    except Exception as e:
        logger.error(f"Unexpected error processing torrent {torrent_id}: {e}")
        return jsonify({'error': 'Failed to process torrent data'}), 500


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
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete torrent ID {torrent_id}: {e}")
            results['failed'].append(torrent_id)

    if results['failed']:
        return jsonify({'status': 'partial_success', 'results': results}), 207
    return jsonify({'status': 'success', 'results': results}), 200


# ── POST /torrent/launch_vlc — PC VLC launcher ───────────────
@torrent_bp.route('/launch_vlc', methods=['POST'])
def launch_vlc():
    """Launch VLC.exe locally on the PC using the provided video URL."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    video_url = request.json.get("video_url")
    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    try:
        exe_path = None
        for path in _VLC_PATHS:
            if os.path.isfile(path):
                exe_path = path
                break
        if not exe_path:
            exe_path = shutil.which("vlc") or shutil.which("vlc.exe")
        if not exe_path:
            logger.error("vlc.exe not found in any known location.")
            return jsonify({"error": "VLC not found. Please ensure it is installed."}), 404

        subprocess.Popen([exe_path, video_url])
        return jsonify({"status": "success", "message": "VLC launched"})
    except Exception as e:
        logger.error(f"Failed to launch VLC: {e}")
        return jsonify({"error": str(e)}), 500
