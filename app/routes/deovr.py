# app/routes/heresphere.py

"""
HereSphere / DeoVR-compatible Web API.

Allows HereSphere's built-in browser to:
  1. Browse the user's Real-Debrid torrent library  (GET  /heresphere)
  2. Get video details with playable download links (POST /heresphere/<id>)

Usage:
  Open HereSphere → enter http://<your-ip>:5000/heresphere in the browser
"""

from flask import Blueprint, jsonify, request, current_app, url_for
import logging
import os
import shutil
import requests
import subprocess
from app.services.real_debrid import RealDebridService, RealDebridError

# Known install paths for HereSphere (searched via PowerShell)
_HERESPHERE_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"C:\Program Files\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"D:\SteamLibrary\steamapps\common\HereSphere\HereSphere.exe",
]

deovr_bp = Blueprint('deovr', __name__)
logger = logging.getLogger(__name__)


@deovr_bp.before_request
def log_deovr_request():
    """Log every request that hits the deovr blueprint for debugging."""
    logger.info(f"[DEOVR-DEBUG] {request.method} {request.url}")
    logger.info(f"[DEOVR-DEBUG] Headers: {dict(request.headers)}")
    if request.data:
        logger.info(f"[DEOVR-DEBUG] Body: {request.data[:500]}")

# Video extensions we consider playable
_VIDEO_EXTS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.mpeg', '.mpg', '.m4v', '.ts', '.vob', '.mts',
}


def _is_video(filename):
    """Return True if filename looks like a video."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in _VIDEO_EXTS)


def _guess_projection(filename):
    """
    Guess VR projection from filename conventions.
    Returns (screenType, stereoMode) tuple.

    Common patterns:
      _180_SBS, _180x180_SBS  → dome, sbs
      _360_TB                 → sphere, tb
      _FISHEYE190_SBS         → fisheye, sbs
      _MKX200_SBS             → mkx200, sbs
      _RF52                   → rf52, sbs
      (default)               → dome, sbs
    """
    upper = filename.upper()

    # Stereo mode
    if '_TB' in upper or '_OU' in upper:
        stereo = 'tb'
    else:
        stereo = 'sbs'  # SBS is the most common default

    # Screen type / projection
    if '_FISHEYE' in upper:
        screen = 'fisheye'
    elif '_MKX200' in upper or '_MKX220' in upper:
        screen = 'mkx200'
    elif '_RF52' in upper:
        screen = 'rf52'
    elif '_360' in upper:
        screen = 'sphere'
    elif '_FLAT' in upper or '_2D' in upper:
        screen = 'flat'
    else:
        screen = 'dome'  # 180° equirect is the most common VR format

    return screen, stereo


# ── GET/POST /deovr — Library listing ─────────────────────
@deovr_bp.route('', methods=['GET', 'POST'])
@deovr_bp.route('/', methods=['GET', 'POST'])
def library_index():
    """
    Return the user's RD torrent library in DeoVR JSON format.

    We handle both GET and POST so it works across different clients.
    """
    # Log everything about the incoming request for debugging
    logger.info(f"DeoVR library request: {request.method} {request.url}")
    logger.debug(f"DeoVR headers: {dict(request.headers)}")
    if request.data:
        logger.debug(f"HereSphere body: {request.data[:500]}")

    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"error": "Real-Debrid API key not configured"}), 500

    try:
        service = RealDebridService(api_key=api_key)
        torrents = service.get_all_torrents()
    except RealDebridError as e:
        logger.error(f"Failed to fetch torrents for HereSphere library: {e}")
        return jsonify({"error": str(e)}), 500

    # Build the video list in DeoVR shortened format
    video_list = []
    for torrent in torrents:
        if torrent.get('status') != 'downloaded':
            continue

        torrent_id = torrent.get('id', '')
        filename = torrent.get('filename', 'Unknown')

        video_list.append({
            "title": filename,
            "videoLength": 0,
            "thumbnailUrl": "",
            "video_url": url_for(
                'deovr.video_detail',
                torrent_id=torrent_id,
                _external=True
            ),
        })

    response = {
        "authorized": "1",
        "scenes": [{
            "name": "Real-Debrid Library",
            "list": video_list,
        }],
    }

    logger.info(f"DeoVR library: returning {len(video_list)} videos")
    return jsonify(response)


# ── POST /deovr/<torrent_id> — Video detail ──────────────
@deovr_bp.route('/<torrent_id>', methods=['POST', 'GET'])
def video_detail(torrent_id):
    """
    Return video detail JSON for a specific torrent in DeoVR format.

    When HereSphere sends needsMediaSource=true, we unrestrict the
    download links and return them as playable video sources.
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    # Check if HereSphere needs the actual media source
    needs_media = True
    if request.is_json and request.json:
        needs_media = request.json.get('needsMediaSource', True)

    headers = {'Authorization': f'Bearer {api_key}'}

    try:
        # Fetch torrent info from RD
        resp = requests.get(
            f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
            headers=headers
        )
        resp.raise_for_status()
        torrent_data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"HereSphere: failed to fetch torrent {torrent_id}: {e}")
        return jsonify({"error": "Failed to fetch torrent info"}), 500

    filename = torrent_data.get('filename', 'Unknown')
    screen_type, stereo_mode = _guess_projection(filename)

    # If HereSphere just needs metadata (not playing yet), return minimal info
    if not needs_media:
        return jsonify({
            "title": filename,
            "videoLength": 0,
            "screenType": screen_type,
            "stereoMode": stereo_mode,
        })

    # ── Build video sources from the torrent's files ──────────
    files = torrent_data.get('files', [])
    links = torrent_data.get('links', [])
    selected_files = [f for f in files if f.get('selected') == 1]

    # Unrestrict all links
    service = RealDebridService(api_key=api_key)
    unrestricted_links = []
    for link in links:
        try:
            unrestricted_links.append(service.unrestrict_link(link))
        except RealDebridError:
            unrestricted_links.append(link)

    # Map file IDs to unrestricted links
    link_map = {f['id']: link for f, link in zip(selected_files, unrestricted_links)}

    # Sort by size descending, filter to video files only
    sorted_files = sorted(selected_files, key=lambda f: f.get('bytes', 0), reverse=True)

    video_sources = []
    for f in sorted_files:
        fname = f.get('path', '').split('/')[-1]
        if not _is_video(fname):
            continue

        link = link_map.get(f.get('id'))
        if not link:
            continue

        video_sources.append({
            "resolution": 0,  # Unknown; HereSphere handles this
            "url": link,
        })

    if not video_sources:
        return jsonify({"error": "No playable video files found in this torrent"}), 404

    # Use the largest file's name to guess projection if the torrent name
    # doesn't have VR indicators
    if sorted_files:
        largest_name = sorted_files[0].get('path', '').split('/')[-1]
        screen_type, stereo_mode = _guess_projection(largest_name)

    response = {
        "title": filename,
        "videoLength": 0,
        "screenType": screen_type,
        "stereoMode": stereo_mode,
        "is3d": stereo_mode != 'off',
        "encodings": [{
            "name": "original",
            "videoSources": video_sources,
        }],
    }

    logger.info(f"HereSphere: serving {len(video_sources)} sources for torrent {torrent_id}")
    return jsonify(response)


# ── POST /heresphere/launch_heresphere — PC app launcher ──────
@deovr_bp.route('/launch_heresphere', methods=['POST'])
def launch_heresphere():
    """
    Launch HereSphere.exe locally on the PC using the provided video URL.
    This restores the original 'Open in HereSphere' button functionality.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    video_url = request.json.get("video_url")
    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    try:
        # Find HereSphere.exe from known install paths
        exe_path = None
        for path in _HERESPHERE_PATHS:
            if os.path.isfile(path):
                exe_path = path
                break
        # Fallback: check if it's on PATH
        if not exe_path:
            exe_path = shutil.which("HereSphere") or shutil.which("HereSphere.exe")
        if not exe_path:
            logger.error("HereSphere.exe not found in any known location.")
            return jsonify({"error": "HereSphere.exe not found. Please ensure it is installed via Steam."}), 404

        subprocess.Popen([exe_path, video_url])
        return jsonify({"status": "success", "message": "HereSphere launched"})
    except Exception as e:
        logger.error(f"Failed to launch HereSphere: {e}")
        return jsonify({"error": str(e)}), 500
