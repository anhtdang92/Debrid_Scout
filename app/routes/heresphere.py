# app/routes/heresphere.py

"""
HereSphere / DeoVR-compatible Web API.

Allows HereSphere's built-in browser to:
  1. Browse the user's Real-Debrid torrent library  (GET  /heresphere)
  2. Get video details with playable download links (POST /heresphere/<id>)
  3. Write back favorites and ratings               (POST /heresphere/<id>)
  4. Serve video thumbnails extracted via ffmpeg      (GET  /heresphere/thumb/<id>)

Write-back pattern modelled after XBVR: HereSphere POSTs isFavorite and
rating in the same JSON body as needsMediaSource, and we persist them to
a local JSON file (data/user_data.json).

Usage:
  Open HereSphere → enter http://<your-ip>:5000/heresphere in the browser
"""

from flask import (
    Blueprint, jsonify, request, current_app, url_for,
    render_template, send_file,
)
import logging
import time
from datetime import datetime, timedelta, timezone
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.file_helper import FileHelper
from app.services.vr_helper import (
    is_video, guess_projection, launch_heresphere_exe,
)
from app.services.thumbnail import ThumbnailService
from app.services.user_data import UserDataStore

heresphere_bp = Blueprint('heresphere', __name__)
logger = logging.getLogger(__name__)

# Lazily initialised singletons — created on first use
_thumb_service = None
_user_data = None


def _get_thumb_service():
    """Return the shared ThumbnailService instance."""
    global _thumb_service
    if _thumb_service is None:
        _thumb_service = ThumbnailService()
    return _thumb_service


def _get_user_data():
    """Return the shared UserDataStore instance."""
    global _user_data
    if _user_data is None:
        _user_data = UserDataStore()
    return _user_data


# ── Torrent info cache (TTL = 5 minutes) ────────────────────
_torrent_cache = {}
_TORRENT_CACHE_TTL = 300


def _get_torrent_info_cached(service, torrent_id):
    """Fetch torrent info via RealDebridService with a short TTL cache."""
    now = time.time()
    cached = _torrent_cache.get(torrent_id)
    if cached and (now - cached['ts']) < _TORRENT_CACHE_TTL:
        return cached['data']
    data = service.get_torrent_info(torrent_id)
    _torrent_cache[torrent_id] = {'data': data, 'ts': now}
    return data


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


def _build_tags(projection, stereo, fov, lens,
                video_file_count=0, total_bytes=0, date_added=''):
    """
    Build HereSphere-style structured tags for filtering in the native UI.

    Tag naming follows XBVR conventions:
      - "Feature:<name>" for video properties and metadata
      - Colon-delimited prefix enables HereSphere's category grouping
    """
    tags = []

    # ── Projection / FOV tags (XBVR style) ────────────────────
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

    # ── File / size tags ──────────────────────────────────────
    if video_file_count > 1:
        tags.append({"name": "Feature:Multiple video files"})

    gb = total_bytes / (1024 ** 3) if total_bytes else 0
    if gb >= 15:
        tags.append({"name": "Feature:Size: 15 GB+"})
    elif gb >= 5:
        tags.append({"name": "Feature:Size: 5-15 GB"})
    elif gb >= 1:
        tags.append({"name": "Feature:Size: 1-5 GB"})

    # ── Date tags (XBVR style: Year and Month) ────────────────
    if date_added and len(date_added) >= 7:
        tags.append({"name": f"Feature:Year: {date_added[:4]}"})
        tags.append({"name": f"Feature:Month: {date_added[:7]}"})

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


def _build_scan_entry(torrent, user_data):
    """
    Build a lightweight HereSphere scan entry from torrent list data.

    Returns the minimal fields HereSphere needs to populate its search,
    sort, and filter UI (title, dates, tags, rating, link) — without
    playback data (media, projection, thumbnails, etc.).

    The torrent dict comes from RealDebridService.get_all_torrents()
    (id, filename, status, bytes, added, links).
    """
    torrent_id = torrent.get('id', '')
    filename = torrent.get('filename', 'Unknown')
    total_bytes = torrent.get('bytes', 0) or 0
    date_added = (torrent.get('added') or '')[:10]
    links_count = len(torrent.get('links') or [])

    projection, stereo, fov, lens = guess_projection(filename)
    title = FileHelper.simplify_filename(filename)
    tags = _build_tags(
        projection, stereo, fov, lens,
        links_count, total_bytes, date_added,
    )
    if user_data.is_watched(torrent_id):
        tags.append({"name": "Feature:Watched"})
    else:
        tags.append({"name": "Feature:Unwatched"})

    detail_url = url_for(
        'heresphere.video_detail', torrent_id=torrent_id, _external=True,
    )

    entry = {
        "link": detail_url,
        "title": title,
        "dateReleased": date_added,
        "dateAdded": date_added,
        "duration": 0,
        "isFavorite": user_data.is_favorite(torrent_id),
        "tags": tags,
    }
    rating = user_data.get_rating(torrent_id)
    if rating:
        entry["rating"] = rating
    return entry


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
        user_data = _get_user_data()
        videos = []
        for t in torrents:
            if t.get('status') != 'downloaded':
                continue
            filename = t.get('filename', 'Unknown')
            torrent_id = t.get('id', '')
            projection, stereo, fov, _lens = guess_projection(filename)
            total_bytes = t.get('bytes', 0) or 0
            videos.append({
                'id': torrent_id,
                'name': FileHelper.simplify_filename(filename),
                'raw_name': filename,
                'projection_label': _projection_label(projection, stereo, fov),
                'size': FileHelper.format_file_size(total_bytes),
                'byte_size': total_bytes,
                'added': (t.get('added') or '')[:10],
                'links_count': len(t.get('links') or []),
                'thumb_url': url_for('heresphere.thumbnail', torrent_id=torrent_id, _external=True),
                'preview_url': url_for('heresphere.preview', torrent_id=torrent_id, _external=True),
                'is_favorite': user_data.is_favorite(torrent_id),
                'rating': user_data.get_rating(torrent_id),
                'is_watched': user_data.is_watched(torrent_id),
            })

        hs_url = url_for('heresphere.library_index', _external=True)
        return render_template('heresphere.html', videos=videos, hs_url=hs_url, error=None)

    # ── HereSphere / API JSON view ─────────────────────────────
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    user_data = _get_user_data()
    favorites, recent, this_month, older = [], [], [], []

    for torrent in torrents:
        if torrent.get('status') != 'downloaded':
            continue

        torrent_id = torrent.get('id', '')
        detail_url = url_for(
            'heresphere.video_detail',
            torrent_id=torrent_id,
            _external=True
        )

        if user_data.is_favorite(torrent_id):
            favorites.append(detail_url)

        added = _parse_rd_date(torrent.get('added'))
        if added and added >= week_ago:
            recent.append(detail_url)
        elif added and added >= month_ago:
            this_month.append(detail_url)
        else:
            older.append(detail_url)

    library = []
    if favorites:
        library.append({"name": "Favorites", "list": favorites})
    if recent:
        library.append({"name": "Recently Added", "list": recent})
    if this_month:
        library.append({"name": "This Month", "list": this_month})
    if older:
        library.append({"name": "Older", "list": older})
    if not library:
        library.append({"name": "Real-Debrid Library", "list": []})

    total = len(recent) + len(this_month) + len(older)
    scan_url = url_for('heresphere.scan', _external=True)
    response = {"access": 1, "library": library, "scan": scan_url}

    logger.info(f"HereSphere library: returning {total} videos in {len(library)} sections")
    resp = jsonify(response)
    resp.headers['HereSphere-JSON-Version'] = '1'
    return resp


# ── POST /heresphere/scan — Bulk metadata for library scan ────
@heresphere_bp.route('/scan', methods=['POST'])
def scan():
    """
    Return metadata for every video in one response.

    HereSphere uses this to populate tags, titles, dates, etc. for the
    entire library without making individual requests per video.  The
    response is an array of the same objects that video_detail returns
    when needsMediaSource is false (i.e. metadata only, media=[]).
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify([]), 500

    try:
        service = RealDebridService(api_key=api_key)
        torrents = service.get_all_torrents()
    except RealDebridError as e:
        logger.error(f"HereSphere scan: failed to fetch torrents: {e}")
        return jsonify([]), 500

    user_data = _get_user_data()
    scan_data = []
    for torrent in torrents:
        if torrent.get('status') != 'downloaded':
            continue
        scan_data.append(_build_scan_entry(torrent, user_data))

    logger.info(f"HereSphere scan: returning metadata for {len(scan_data)} videos")
    resp = jsonify({"scanData": scan_data})
    resp.headers['HereSphere-JSON-Version'] = '1'
    return resp


# ── POST /heresphere/<torrent_id> — Video detail + write-back ─
@heresphere_bp.route('/<torrent_id>', methods=['POST', 'GET'])
def video_detail(torrent_id):
    """
    Return video detail JSON for a specific torrent.

    Write-back (XBVR pattern): when HereSphere POSTs isFavorite or rating
    in the request body, we persist them locally before returning the
    response. This makes favorites/ratings survive across sessions.
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"status": "error", "error": "API key not configured"}), 500

    # ── Process write-back from HereSphere ────────────────────
    needs_media = True
    body = {}
    if request.is_json and request.json:
        body = request.json
        needs_media = body.get('needsMediaSource', True)
        # Persist any favorite/rating changes
        _get_user_data().process_heresphere_update(torrent_id, body)

    service = RealDebridService(api_key=api_key)

    try:
        torrent_data = _get_torrent_info_cached(service, torrent_id)
    except RealDebridError as e:
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
    tags = _build_tags(projection, stereo, fov, lens,
                       len(video_files), total_bytes, date_added)

    # Thumbnail / preview / event URLs
    thumb_url = url_for('heresphere.thumbnail', torrent_id=torrent_id, _external=True)
    preview_url = url_for('heresphere.preview', torrent_id=torrent_id, _external=True)
    event_url = url_for('heresphere.event', torrent_id=torrent_id, _external=True)

    # Load persisted user data (favorites, ratings, playback)
    user_data = _get_user_data()

    # Add Watched/Unwatched tag
    if user_data.is_watched(torrent_id):
        tags.append({"name": "Feature:Watched"})
    else:
        tags.append({"name": "Feature:Unwatched"})

    # Resume position — HereSphere uses currentTime (milliseconds)
    playback_seconds = user_data.get_playback_time(torrent_id)

    # ── Build base response with ALL HereSphere fields ────────
    base_response = {
        "access": 1,
        "title": title,
        "description": description,
        "thumbnailImage": thumb_url,
        "thumbnailVideo": preview_url,
        "dateReleased": date_added,
        "dateAdded": date_added,
        "duration": 0,
        "currentTime": playback_seconds * 1000.0,
        "rating": user_data.get_rating(torrent_id),
        "isFavorite": user_data.is_favorite(torrent_id),
        "projection": projection,
        "stereo": stereo,
        "fov": fov,
        "lens": lens,
        "eventServer": event_url,
        "tags": tags,
        "subtitles": [],
        "scripts": [],
        # Write permissions — favorites and ratings are writable
        "writeFavorite": True,
        "writeRating": True,
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
    # Build file-ID → restricted-link mapping using positional correspondence
    # (RD returns links[] in the same order as selected files)
    restricted_map = {}
    for i, f in enumerate(selected_files):
        fid = f.get('id')
        if fid is not None and i < len(links):
            restricted_map[fid] = links[i]

    # Only unrestrict links for video files (skip non-video to avoid
    # wasting API calls and 0.2s rate-limit delays per link)
    video_file_ids = {f.get('id') for f in video_files}
    link_map = {}
    for fid, restricted_link in restricted_map.items():
        if fid not in video_file_ids:
            continue
        try:
            link_map[fid] = service.unrestrict_link(restricted_link)
        except RealDebridError:
            link_map[fid] = restricted_link

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


def _get_direct_video_url(torrent_id):
    """Fetch torrent info, find the largest video file, and unrestrict its link.

    Returns the direct URL string, or None on any failure.
    Shared by the thumbnail and preview endpoints.
    """
    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return None

    try:
        service = RealDebridService(api_key=api_key)
        torrent_data = _get_torrent_info_cached(service, torrent_id)
    except RealDebridError:
        return None

    files = torrent_data.get('files') or []
    links = torrent_data.get('links') or []
    selected = [f for f in files if f.get('selected') == 1]

    # Build file-ID → restricted-link mapping by position
    restricted_map = {}
    for i, f in enumerate(selected):
        fid = f.get('id')
        if fid is not None and i < len(links):
            restricted_map[fid] = links[i]

    # Find the largest video file that has a link
    sorted_files = sorted(selected, key=lambda f: f.get('bytes', 0), reverse=True)
    for f in sorted_files:
        fname = f.get('path', '').split('/')[-1]
        fid = f.get('id')
        if is_video(fname) and fid in restricted_map:
            try:
                return service.unrestrict_link(restricted_map[fid])
            except RealDebridError:
                return None

    return None


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

    cached = svc.get_cached_path(torrent_id)
    if cached:
        return send_file(cached, mimetype='image/jpeg')

    if not svc.available:
        logger.debug("ffmpeg not available — skipping thumbnail generation")
        return '', 404

    direct_url = _get_direct_video_url(torrent_id)
    if not direct_url:
        return '', 404

    path = svc.generate(torrent_id, direct_url)
    if path:
        return send_file(path, mimetype='image/jpeg')

    return '', 404


# ── GET /heresphere/preview/<torrent_id> — Animated preview ───
@heresphere_bp.route('/preview/<torrent_id>', methods=['GET'])
def preview(torrent_id):
    """
    Serve a short (~5 s) muted MP4 preview clip for a torrent.

    HereSphere displays this as an animated thumbnail on hover in the
    library grid.  Generated via ffmpeg and cached to disk.
    """
    svc = _get_thumb_service()

    cached = svc.get_cached_preview_path(torrent_id)
    if cached:
        return send_file(cached, mimetype='video/mp4')

    if not svc.available:
        logger.debug("ffmpeg not available — skipping preview generation")
        return '', 404

    direct_url = _get_direct_video_url(torrent_id)
    if not direct_url:
        return '', 404

    path = svc.generate_preview(torrent_id, direct_url)
    if path:
        return send_file(path, mimetype='video/mp4')

    return '', 404


# ── POST /heresphere/event/<torrent_id> — Playback event server ─
@heresphere_bp.route('/event/<torrent_id>', methods=['POST'])
def event(torrent_id):
    """
    Receive playback events from HereSphere.

    HereSphere sends JSON with playerState (0=play, 1=pause, 2=close),
    currentTime (seconds), and playbackSpeed.  We persist the position
    for resume and increment the play count on close.
    """
    if not request.is_json:
        return '', 204

    body = request.json or {}
    logger.debug(f"HereSphere event for {torrent_id}: {body}")

    _get_user_data().process_heresphere_event(torrent_id, body)
    return '', 204


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
