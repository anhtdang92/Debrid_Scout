# app/routes/heresphere.py

"""
HereSphere / DeoVR-compatible Web API.

Allows HereSphere's built-in browser to:
  1. Browse the user's Real-Debrid torrent library  (GET  /heresphere)
  2. Get video details with playable download links (POST /heresphere/<id>)
  3. Serve video thumbnails extracted via ffmpeg      (GET  /heresphere/thumb/<id>)

Usage:
  Open HereSphere → enter http://<your-ip>:5000/heresphere in the browser
"""

from flask import (
    Blueprint, jsonify, request, current_app, url_for,
    render_template, send_file,
)
import logging
import requests
from datetime import datetime, timedelta, timezone
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.file_helper import FileHelper
from app.services.vr_helper import (
    is_video, guess_projection, launch_heresphere_exe,
)
from app.services.thumbnail import ThumbnailService

heresphere_bp = Blueprint('heresphere', __name__)
logger = logging.getLogger(__name__)

# Lazily initialised singleton — created on first use
_thumb_service = None


def _get_thumb_service():
    """Return the shared ThumbnailService instance."""
    global _thumb_service
    if _thumb_service is None:
        _thumb_service = ThumbnailService()
    return _thumb_service


@heresphere_bp.before_request
def log_heresphere_request():
    """Log every request that hits the heresphere blueprint for debugging."""
    logger.info(f"[HS-DEBUG] {request.method} {request.url}")
    logger.info(f"[HS-DEBUG] Headers: {dict(request.headers)}")
    if request.data:
        logger.info(f"[HS-DEBUG] Body: {request.data[:500]}")


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
    """Parse an RD API date string into a timezone-aware datetime, or return None.

    Handles ISO 8601 formats from Real-Debrid: '2024-01-15T12:30:00.000Z',
    '2024-01-15T12:30:00+00:00', or naive '2024-01-15T12:30:00' (assumed UTC).
    """
    if not date_str:
        return None
    try:
        # Normalize trailing 'Z' to a proper UTC offset for fromisoformat()
        normalized = date_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
        # If the result is naive (no timezone), assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError, TypeError):
        logger.warning(f"Could not parse RD date string: {date_str!r}")
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
        return jsonify({"status": "error", "error": "Real-Debrid API key not configured"}), 500

    try:
        service = RealDebridService(api_key=api_key)
        torrents = service.get_all_torrents()
    except RealDebridError as e:
        logger.error(f"Failed to fetch torrents for HereSphere library: {e}")
        if _wants_html():
            return render_template('heresphere.html', error="Failed to fetch torrent library from Real-Debrid", videos=[])
        return jsonify({"status": "error", "error": "Failed to fetch torrent library from Real-Debrid"}), 500

    # ── Browser HTML view ──────────────────────────────────────
    if _wants_html():
        videos = []
        for t in torrents:
            if t.get('status') != 'downloaded':
                continue
            filename = t.get('filename', 'Unknown')
            projection, stereo, fov, _lens = guess_projection(filename)
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
        return jsonify({"status": "error", "error": "API key not configured"}), 500

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
        return jsonify({"status": "error", "error": "Failed to fetch torrent info"}), 500

    filename = torrent_data.get('filename', 'Unknown')
    files = torrent_data.get('files') or []
    links = torrent_data.get('links') or []
    selected_files = [f for f in files if f.get('selected') == 1]

    # Count video files and total size for metadata
    video_files = []
    for f in selected_files:
        fname = f.get('path', '').split('/')[-1]
        if is_video(fname):
            video_files.append(f)

    total_bytes = sum(f.get('bytes', 0) for f in video_files)

    # Guess projection from the largest video file name, fall back to torrent name
    projection, stereo, fov, lens = guess_projection(filename)
    if video_files:
        sorted_by_size = sorted(video_files, key=lambda f: f.get('bytes', 0), reverse=True)
        largest_name = sorted_by_size[0].get('path', '').split('/')[-1]
        projection, stereo, fov, lens = guess_projection(largest_name)

    title = FileHelper.simplify_filename(filename)
    date_added = (torrent_data.get('added') or '')[:10]
    description = f"{len(video_files)} file{'s' if len(video_files) != 1 else ''} — {FileHelper.format_file_size(total_bytes)}"
    tags = _build_tags(projection, stereo, fov, lens, len(video_files), total_bytes)

    # Thumbnail URL — points to our /heresphere/thumb/<id> endpoint
    thumb_url = url_for('heresphere.thumbnail', torrent_id=torrent_id, _external=True)

    # ── Build base response with ALL HereSphere fields ────────
    base_response = {
        "access": 1,
        "title": title,
        "description": description,
        "thumbnailImage": thumb_url,
        "thumbnailVideo": "",
        "dateReleased": date_added,
        "dateAdded": date_added,
        "duration": 0,
        "rating": 0,
        "isFavorite": False,
        "projection": projection,
        "stereo": stereo,
        "fov": fov,
        "lens": lens,
        "tags": tags,
        "subtitles": [],
        "scripts": [],
        # Write permissions — read-only for now
        "writeFavorite": False,
        "writeRating": False,
        "writeTags": False,
        "writeHSP": False,
    }

    # ── Metadata-only response (initial library scan) ─────────
    if not needs_media:
        base_response["media"] = []
        resp = jsonify(base_response)
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
                "resolution": 0,
                "height": 0,
                "width": 0,
                "size": f.get('bytes', 0),
                "url": link,
            }],
        })

    if not media_entries:
        return jsonify({"status": "error", "error": "No playable video files found in this torrent"}), 404

    base_response["media"] = media_entries

    logger.info(f"HereSphere detail: serving {len(media_entries)} sources for torrent {torrent_id}")
    resp = jsonify(base_response)
    resp.headers['HereSphere-JSON-Version'] = '1'
    return resp


# ── GET /heresphere/thumb/<torrent_id> — Thumbnail server ─────
@heresphere_bp.route('/thumb/<torrent_id>', methods=['GET'])
def thumbnail(torrent_id):
    """
    Serve a video thumbnail for a torrent.

    On first request, unrestricts the first video link and uses ffmpeg to
    extract a single frame.  The result is cached to disk so subsequent
    requests are instant.
    """
    svc = _get_thumb_service()

    # 1. Check disk cache first (instant)
    cached = svc.get_cached_path(torrent_id)
    if cached:
        return send_file(cached, mimetype='image/jpeg')

    # 2. ffmpeg not available — return 404 gracefully
    if not svc.available:
        logger.debug("ffmpeg not available — skipping thumbnail generation")
        return '', 404

    # 3. Generate thumbnail: fetch torrent info → unrestrict → ffmpeg
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return '', 404

    try:
        headers = {'Authorization': f'Bearer {api_key}'}
        resp = requests.get(
            f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
            headers=headers,
        )
        resp.raise_for_status()
        torrent_data = resp.json()
    except requests.exceptions.RequestException:
        return '', 404

    files = torrent_data.get('files') or []
    links = torrent_data.get('links') or []
    selected = [f for f in files if f.get('selected') == 1]

    # Find the largest video file and its corresponding link
    video_link = None
    sorted_files = sorted(selected, key=lambda f: f.get('bytes', 0), reverse=True)
    for i, f in enumerate(sorted_files):
        fname = f.get('path', '').split('/')[-1]
        if is_video(fname) and i < len(links):
            # The link at the same index in links[] corresponds to this
            # selected file (RD maintains the order)
            idx = selected.index(f)
            if idx < len(links):
                video_link = links[idx]
                break

    if not video_link:
        return '', 404

    # Unrestrict to get a direct URL that ffmpeg can read
    try:
        service = RealDebridService(api_key=api_key)
        direct_url = service.unrestrict_link(video_link)
    except RealDebridError:
        return '', 404

    # Run ffmpeg (seeks to 10s, grabs one frame, ~2-5s)
    path = svc.generate(torrent_id, direct_url)
    if path:
        return send_file(path, mimetype='image/jpeg')

    return '', 404


# ── POST /heresphere/launch_heresphere — PC app launcher ──────
@heresphere_bp.route('/launch_heresphere', methods=['POST'])
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
