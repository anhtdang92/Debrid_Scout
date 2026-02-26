# app/routes/deovr.py

"""
DeoVR-compatible Web API.

Allows DeoVR's built-in browser to:
  1. Browse the user's Real-Debrid torrent library  (GET  /deovr)
  2. Get video details with playable download links (POST /deovr/<id>)
  3. Write back favorites and ratings               (POST /deovr/<id>)
  4. Receive playback events for tracking            (POST /deovr/event/<id>)

Usage:
  Open DeoVR → enter http://<your-ip>:5000/deovr in the browser
"""

from flask import Blueprint, jsonify, request, current_app, url_for
import logging
import requests
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.file_helper import FileHelper
from app.services.vr_helper import (
    is_video, guess_projection_deovr, launch_heresphere_exe,
)
from app.services.user_data import UserDataStore

deovr_bp = Blueprint('deovr', __name__)
logger = logging.getLogger(__name__)

_user_data = None


def _get_user_data():
    """Return the shared UserDataStore instance."""
    global _user_data
    if _user_data is None:
        _user_data = UserDataStore()
    return _user_data


@deovr_bp.before_request
def log_deovr_request():
    """Log every request that hits the deovr blueprint for debugging."""
    logger.info(f"[DEOVR-DEBUG] {request.method} {request.url}")
    logger.info(f"[DEOVR-DEBUG] Headers: {dict(request.headers)}")
    if request.data:
        logger.info(f"[DEOVR-DEBUG] Body: {request.data[:500]}")


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
        logger.debug(f"DeoVR body: {request.data[:500]}")

    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"status": "error", "error": "Real-Debrid API key not configured"}), 500

    try:
        service = RealDebridService(api_key=api_key)
        torrents = service.get_all_torrents()
    except RealDebridError as e:
        logger.error(f"Failed to fetch torrents for DeoVR library: {e}")
        return jsonify({"status": "error", "error": "Failed to fetch torrent library from Real-Debrid"}), 500

    # Build the video list in DeoVR shortened format
    video_list = []
    for torrent in torrents:
        if torrent.get('status') != 'downloaded':
            continue

        torrent_id = torrent.get('id', '')
        filename = torrent.get('filename', 'Unknown')

        # Use the HereSphere thumbnail endpoint — works for DeoVR too
        thumb_url = url_for(
            'heresphere.thumbnail',
            torrent_id=torrent_id,
            _external=True,
        )

        video_list.append({
            "title": FileHelper.simplify_filename(filename),
            "videoLength": 0,
            "thumbnailUrl": thumb_url,
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

    Write-back: when the client POSTs isFavorite or rating in the
    request body, we persist them locally before returning the response.

    When the client sends needsMediaSource=true, we unrestrict the
    download links and return them as playable video sources.
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"status": "error", "error": "API key not configured"}), 500

    # ── Process write-back ────────────────────────────────────
    needs_media = True
    body = {}
    if request.is_json and request.json:
        body = request.json
        needs_media = body.get('needsMediaSource', True)
        _get_user_data().process_heresphere_update(torrent_id, body)

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
        logger.error(f"DeoVR: failed to fetch torrent {torrent_id}: {e}")
        return jsonify({"status": "error", "error": "Failed to fetch torrent info"}), 500

    filename = torrent_data.get('filename', 'Unknown')
    screen_type, stereo_mode = guess_projection_deovr(filename)

    # Thumbnail URL — reuses the HereSphere thumbnail endpoint
    thumb_url = url_for('heresphere.thumbnail', torrent_id=torrent_id, _external=True)

    # Load persisted user data
    user_data = _get_user_data()

    # If the client just needs metadata (not playing yet), return minimal info
    if not needs_media:
        return jsonify({
            "title": filename,
            "videoLength": 0,
            "thumbnailUrl": thumb_url,
            "screenType": screen_type,
            "stereoMode": stereo_mode,
            "isFavorite": user_data.is_favorite(torrent_id),
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
        if not is_video(fname):
            continue

        link = link_map.get(f.get('id'))
        if not link:
            continue

        video_sources.append({
            "resolution": 0,  # Unknown; DeoVR handles this
            "url": link,
        })

    if not video_sources:
        return jsonify({"status": "error", "error": "No playable video files found in this torrent"}), 404

    # Use the largest file's name to guess projection if the torrent name
    # doesn't have VR indicators
    if sorted_files:
        largest_name = sorted_files[0].get('path', '').split('/')[-1]
        screen_type, stereo_mode = guess_projection_deovr(largest_name)

    # Resume position (DeoVR uses seconds)
    playback_seconds = user_data.get_playback_time(torrent_id)

    # Event server URL for playback tracking
    event_url = url_for('deovr.event', torrent_id=torrent_id, _external=True)

    response = {
        "title": FileHelper.simplify_filename(filename),
        "videoLength": 0,
        "thumbnailUrl": thumb_url,
        "screenType": screen_type,
        "stereoMode": stereo_mode,
        "is3d": stereo_mode != 'off',
        "isFavorite": user_data.is_favorite(torrent_id),
        "rating": user_data.get_rating(torrent_id),
        "currentTime": playback_seconds,
        "eventServer": event_url,
        "encodings": [{
            "name": "original",
            "videoSources": video_sources,
        }],
    }

    logger.info(f"DeoVR: serving {len(video_sources)} sources for torrent {torrent_id}")
    return jsonify(response)


# ── POST /deovr/event/<torrent_id> — Playback event server ────
@deovr_bp.route('/event/<torrent_id>', methods=['POST'])
def event(torrent_id):
    """
    Receive playback events from DeoVR.

    DeoVR sends JSON with playerState (0=play, 1=pause, 2=close)
    and currentTime (seconds).  We persist the position for resume
    and increment the play count on close (playerState 2).
    """
    if not request.is_json:
        return '', 204

    body = request.json or {}
    logger.debug(f"DeoVR event for {torrent_id}: {body}")

    # DeoVR uses playerState: 0=play, 1=pause, 2=close
    current_time = body.get('currentTime', body.get('time'))
    player_state = body.get('playerState', body.get('event'))

    if current_time is not None:
        _get_user_data().update_playback_time(torrent_id, current_time)

    # playerState 2 = close (DeoVR)
    if player_state == 2:
        _get_user_data().increment_play_count(torrent_id)

    return '', 204


# ── POST /deovr/launch_heresphere — PC app launcher ──────
@deovr_bp.route('/launch_heresphere', methods=['POST'])
def launch_heresphere():
    """
    Launch HereSphere.exe locally on the PC using the provided video URL.
    This restores the original 'Open in HereSphere' button functionality.
    """
    if not request.is_json:
        return jsonify({"status": "error", "error": "Content-Type must be application/json"}), 400

    video_url = request.json.get("video_url")
    if not video_url:
        return jsonify({"status": "error", "error": "No video URL provided"}), 400

    success, error_msg = launch_heresphere_exe(video_url)
    if success:
        return jsonify({"status": "success", "message": "HereSphere launched"})
    if "not found" in (error_msg or ""):
        return jsonify({"status": "error", "error": error_msg}), 404
    return jsonify({"status": "error", "error": error_msg}), 500
