# app/routes/heresphere.py

"""
HereSphere / DeoVR-compatible Web API.

Allows HereSphere's built-in browser to:
  1. Browse the user's Real-Debrid torrent library  (GET  /heresphere)
  2. Get video details with playable download links (POST /heresphere/<id>)

Usage:
  Open HereSphere → enter http://<your-ip>:5000/heresphere in the browser
"""

from flask import Blueprint, jsonify, request, current_app, url_for, render_template
import logging
import os
import shutil
import requests
import subprocess
from datetime import datetime, timedelta, timezone
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.file_helper import FileHelper

# Known install paths for HereSphere (searched via PowerShell)
_HERESPHERE_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"C:\Program Files\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"D:\SteamLibrary\steamapps\common\HereSphere\HereSphere.exe",
]

heresphere_bp = Blueprint('heresphere', __name__)
logger = logging.getLogger(__name__)


@heresphere_bp.before_request
def log_heresphere_request():
    """Log every request that hits the heresphere blueprint for debugging."""
    logger.info(f"[HS-DEBUG] {request.method} {request.url}")
    logger.info(f"[HS-DEBUG] Headers: {dict(request.headers)}")
    if request.data:
        logger.info(f"[HS-DEBUG] Body: {request.data[:500]}")

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
    Returns (projection, stereo, fov, lens) tuple for HereSphere native API.
    """
    upper = filename.upper()

    # Stereo mode
    if '_TB' in upper or '_OU' in upper:
        stereo = 'tb'
    else:
        stereo = 'sbs'  # SBS is the most common default

    # FOV & Lens
    fov = 180.0
    lens = 'Linear'

    # Screen type / projection
    if '_FISHEYE190' in upper or '_RF52' in upper:
        projection = 'fisheye'
        fov = 190.0
    elif '_MKX200' in upper:
        projection = 'fisheye'
        fov = 200.0
        lens = 'MKX200'
    elif '_MKX220' in upper:
        projection = 'fisheye'
        fov = 220.0
        lens = 'MKX220'
    elif '_FISHEYE' in upper:
        projection = 'fisheye'
        fov = 180.0
    elif '_360' in upper:
        projection = 'equirectangular360'
        fov = 360.0
    elif '_FLAT' in upper or '_2D' in upper:
        projection = 'perspective'
        stereo = 'mono'
        fov = 90.0
    else:
        projection = 'equirectangular'  # 180° equirect is the most common VR format

    return projection, stereo, fov, lens


def _projection_label(projection, stereo, fov):
    """Return a short human-readable label like '180° SBS' or 'Fisheye 200°'."""
    proj_map = {
        'equirectangular': '180°',
        'equirectangular360': '360°',
        'fisheye': f'Fisheye {int(fov)}°',
        'perspective': 'Flat 2D',
    }
    label = proj_map.get(projection, projection)
    if projection != 'perspective':
        label += ' ' + stereo.upper()
    return label


def _wants_html():
    """Return True when the caller is a normal browser (not HereSphere / API)."""
    if request.method == 'POST':
        return False
    accept = request.headers.get('Accept', '')
    return 'text/html' in accept


def _build_tags(projection, stereo, fov, lens, video_file_count=0, total_bytes=0):
    """Build HereSphere-style structured tags for filtering in the native UI."""
    tags = []

    # Projection / FOV tags
    fov_labels = {
        'equirectangular': 'FOV: 180°',
        'equirectangular360': 'FOV: 360°',
        'perspective': 'Flat video',
    }
    if projection == 'fisheye':
        tags.append({"name": f"Feature:FOV: {int(fov)}° Fisheye"})
    elif projection in fov_labels:
        tags.append({"name": f"Feature:{fov_labels[projection]}"})

    # Stereo mode
    stereo_labels = {'sbs': 'SBS', 'tb': 'Top-Bottom', 'mono': 'Mono'}
    if stereo in stereo_labels:
        tags.append({"name": f"Feature:{stereo_labels[stereo]}"})

    # Lens
    if lens and lens not in ('Linear',):
        tags.append({"name": f"Feature:Lens: {lens}"})

    # File count
    if video_file_count > 1:
        tags.append({"name": "Feature:Multiple video files"})

    # Size tier
    gb = total_bytes / (1024 ** 3) if total_bytes else 0
    if gb >= 15:
        tags.append({"name": "Feature:Size: 15 GB+"})
    elif gb >= 5:
        tags.append({"name": "Feature:Size: 5-15 GB"})
    elif gb >= 1:
        tags.append({"name": "Feature:Size: 1-5 GB"})

    return tags


def _parse_rd_date(date_str):
    """Parse an RD API date string into a datetime, or return None."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


# ── GET/POST /heresphere — Library listing ─────────────────────
@heresphere_bp.route('', methods=['GET', 'POST'])
@heresphere_bp.route('/', methods=['GET', 'POST'])
def library_index():
    """
    Return the user's RD torrent library.

    Browsers get a rendered HTML page; HereSphere / API clients get JSON.
    """
    logger.info(f"HereSphere library request: {request.method} {request.url}")
    logger.debug(f"HereSphere headers: {dict(request.headers)}")
    if request.data:
        logger.debug(f"HereSphere body: {request.data[:500]}")

    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        if _wants_html():
            return render_template('heresphere.html', error="Real-Debrid API key not configured", videos=[])
        return jsonify({"error": "Real-Debrid API key not configured"}), 500

    try:
        service = RealDebridService(api_key=api_key)
        torrents = service.get_all_torrents()
    except RealDebridError as e:
        logger.error(f"Failed to fetch torrents for HereSphere library: {e}")
        if _wants_html():
            return render_template('heresphere.html', error=str(e), videos=[])
        return jsonify({"error": str(e)}), 500

    # ── Browser HTML view ──────────────────────────────────────
    if _wants_html():
        videos = []
        for t in torrents:
            if t.get('status') != 'downloaded':
                continue
            filename = t.get('filename', 'Unknown')
            projection, stereo, fov, _lens = _guess_projection(filename)
            total_bytes = t.get('bytes', 0) or 0
            videos.append({
                'id': t.get('id', ''),
                'name': FileHelper.simplify_filename(filename),
                'raw_name': filename,
                'projection_label': _projection_label(projection, stereo, fov),
                'size': FileHelper.format_file_size(total_bytes),
                'added': (t.get('added') or '')[:10],
                'links_count': len(t.get('links') or []),
            })

        hs_url = url_for('heresphere.library_index', _external=True)
        return render_template('heresphere.html', videos=videos, hs_url=hs_url, error=None)

    # ── HereSphere / API JSON view ─────────────────────────────
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    recent, this_month, older = [], [], []

    for torrent in torrents:
        if torrent.get('status') != 'downloaded':
            continue

        torrent_id = torrent.get('id', '')
        detail_url = url_for(
            'heresphere.video_detail',
            torrent_id=torrent_id,
            _external=True
        )

        added = _parse_rd_date(torrent.get('added'))
        if added and added >= week_ago:
            recent.append(detail_url)
        elif added and added >= month_ago:
            this_month.append(detail_url)
        else:
            older.append(detail_url)

    library = []
    if recent:
        library.append({"name": "Recently Added", "list": recent})
    if this_month:
        library.append({"name": "This Month", "list": this_month})
    if older:
        library.append({"name": "Older", "list": older})
    if not library:
        library.append({"name": "Real-Debrid Library", "list": []})

    total = len(recent) + len(this_month) + len(older)
    response = {"access": 1, "library": library}

    logger.info(f"HereSphere library: returning {total} videos in {len(library)} sections")
    resp = jsonify(response)
    resp.headers['HereSphere-JSON-Version'] = '1'
    return resp


# ── POST /heresphere/<torrent_id> — Video detail ──────────────
@heresphere_bp.route('/<torrent_id>', methods=['POST', 'GET'])
def video_detail(torrent_id):
    """
    Return video detail JSON for a specific torrent.

    When HereSphere sends needsMediaSource=true, we unrestrict the
    download links and return them as playable video sources.
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    needs_media = True
    if request.is_json and request.json:
        needs_media = request.json.get('needsMediaSource', True)

    headers = {'Authorization': f'Bearer {api_key}'}

    try:
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
    files = torrent_data.get('files') or []
    links = torrent_data.get('links') or []
    selected_files = [f for f in files if f.get('selected') == 1]

    # Count video files and total size for metadata
    video_files = []
    for f in selected_files:
        fname = f.get('path', '').split('/')[-1]
        if _is_video(fname):
            video_files.append(f)

    total_bytes = sum(f.get('bytes', 0) for f in video_files)

    # Guess projection from the largest video file name, fall back to torrent name
    projection, stereo, fov, lens = _guess_projection(filename)
    if video_files:
        sorted_by_size = sorted(video_files, key=lambda f: f.get('bytes', 0), reverse=True)
        largest_name = sorted_by_size[0].get('path', '').split('/')[-1]
        projection, stereo, fov, lens = _guess_projection(largest_name)

    title = FileHelper.simplify_filename(filename)
    date_added = (torrent_data.get('added') or '')[:10]
    description = f"{len(video_files)} file{'s' if len(video_files) != 1 else ''} — {FileHelper.format_file_size(total_bytes)}"
    tags = _build_tags(projection, stereo, fov, lens, len(video_files), total_bytes)

    # ── Metadata-only response (initial library scan) ─────────
    if not needs_media:
        resp = jsonify({
            "access": 1,
            "title": title,
            "description": description,
            "dateReleased": date_added,
            "dateAdded": date_added,
            "duration": 0,
            "projection": projection,
            "stereo": stereo,
            "fov": fov,
            "lens": lens,
            "tags": tags,
            "media": [],
        })
        resp.headers['HereSphere-JSON-Version'] = '1'
        return resp

    # ── Full response with playable sources ───────────────────
    service = RealDebridService(api_key=api_key)
    unrestricted_links = []
    for link in links:
        try:
            unrestricted_links.append(service.unrestrict_link(link))
        except RealDebridError:
            unrestricted_links.append(link)

    link_map = {}
    for f, link in zip(selected_files, unrestricted_links):
        fid = f.get('id')
        if fid is not None and link:
            link_map[fid] = link

    # Build one media entry per video file (XBVR style: "File 1/N - size")
    media_entries = []
    video_idx = 0
    for f in sorted(video_files, key=lambda f: f.get('bytes', 0), reverse=True):
        link = link_map.get(f.get('id'))
        if not link:
            continue
        video_idx += 1
        size_label = FileHelper.format_file_size(f.get('bytes', 0))
        media_entries.append({
            "name": f"File {video_idx}/{len(video_files)} — {size_label}",
            "sources": [{
                "resolution": "Original",
                "height": 0,
                "width": 0,
                "size": f.get('bytes', 0),
                "url": link,
            }],
        })

    if not media_entries:
        return jsonify({"error": "No playable video files found in this torrent"}), 404

    response = {
        "access": 1,
        "title": title,
        "description": description,
        "dateReleased": date_added,
        "dateAdded": date_added,
        "duration": 0,
        "projection": projection,
        "stereo": stereo,
        "fov": fov,
        "lens": lens,
        "tags": tags,
        "media": media_entries,
    }

    logger.info(f"HereSphere detail: serving {len(media_entries)} sources for torrent {torrent_id}")
    resp = jsonify(response)
    resp.headers['HereSphere-JSON-Version'] = '1'
    return resp


# ── POST /heresphere/launch_heresphere — PC app launcher ──────
@heresphere_bp.route('/launch_heresphere', methods=['POST'])
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
