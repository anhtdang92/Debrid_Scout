# HereSphere UI & API Integration — Improvement Plan

## UI (Browser View)

### 1. Thumbnails in Cards
**Priority: High | Effort: Low**

The card grid is text-only. The `/heresphere/thumb/<id>` endpoint already exists and generates cached JPEG thumbnails via ffmpeg. Adding `<img>` elements to the card layout would transform the browsing experience from a wall of text into a visual library.

**Changes:**
- Add thumbnail `<img>` to each `.hs-card` in `heresphere.html`
- Add CSS for thumbnail sizing, aspect ratio, and loading placeholder
- Lazy-load images (`loading="lazy"`) to avoid blocking page render
- Show a fallback icon when no thumbnail is available

---

### 2. Favorites, Ratings, and Watched Status in Browser View
**Priority: High | Effort: Low**

`UserDataStore` already tracks favorites, ratings, and play counts, but the browser view in `library_index()` (lines 241-255) never queries it. Cards should display:
- Heart icon for favorites
- Star rating (0-5)
- "Watched" badge based on play count

**Changes:**
- Query `UserDataStore` in the HTML branch of `library_index()`
- Pass favorite/rating/watched data to the template
- Add badge/icon elements to `.hs-card`

---

### 3. Sort Controls
**Priority: Medium | Effort: Low**

Only a text filter exists. Users cannot sort by date added, file size, or name. This is painful with large libraries.

**Changes:**
- Add a sort dropdown to `.hs-toolbar` (Name, Date Added, Size)
- Implement client-side sorting via JS (data already in the DOM via `data-*` attributes)
- Persist sort preference in `localStorage`

---

### 4. Preview on Hover
**Priority: Medium | Effort: Medium**

Preview clips are generated and served at `/heresphere/preview/<id>`, but the browser view doesn't use them. A hover-to-preview on the card thumbnails would be a natural addition.

**Changes:**
- Add a `<video>` overlay element that loads the preview MP4 on hover
- Trigger on mouseenter with a short delay to avoid accidental loads
- Muted autoplay, loop, and hide on mouseleave

---

### 5. Pagination or Virtual Scrolling
**Priority: Low | Effort: Medium**

All cards render at once. With 100+ torrents this will become sluggish.

**Changes:**
- Add client-side pagination (e.g., 24 cards per page) or infinite scroll
- Alternatively, use `IntersectionObserver` for lazy rendering

---

## API Integration

### 6. Use `RealDebridService` Instead of Raw Requests
**Priority: High | Effort: Low**

`video_detail()` (lines 371-381) makes a direct `requests.get()` to the RD API instead of using `RealDebridService.get_torrent_info()`. This bypasses rate limiting and error handling.

**Changes:**
- Replace raw HTTP call with `service.get_torrent_info(torrent_id)`
- Remove duplicate `headers` construction

---

### 7. Cache Torrent Info
**Priority: Medium | Effort: Medium**

Every `video_detail` POST hits the RD API. Since torrent metadata rarely changes, a short TTL cache would cut latency significantly during rapid HereSphere browsing.

**Changes:**
- Add a module-level TTL cache (similar to `_account_cache`) keyed by torrent ID
- Invalidate on write-back or after 5 minutes

---

### 8. Optimize Link Unrestriction
**Priority: Medium | Effort: Medium**

`video_detail()` unrestricts every link serially with a 0.2s rate-limit delay. For a torrent with 10 links, that's 2+ seconds of blocking.

**Changes:**
- Only unrestrict video file links (skip non-video)
- Consider unrestricting lazily (only when the user clicks play)

---

### 9. Fix File-Link Mapping
**Priority: High | Effort: Low**

Line 472 uses `zip(selected_files, unrestricted_links)`, which assumes 1:1 positional correspondence. If RD returns fewer links than selected files, the mapping shifts.

**Changes:**
- Build the link map using file indices or IDs from the RD API response
- Handle missing links gracefully

---

### 10. Populate `duration` Field
**Priority: Low | Effort: Medium**

The API returns `"duration": 0` everywhere. HereSphere uses this for progress bars and sorting.

**Changes:**
- Extract duration via `ffprobe` during thumbnail generation
- Cache alongside the thumbnail file (e.g., `{id}.json` metadata sidecar)

---

### 11. Detect and Serve Subtitles
**Priority: Low | Effort: Medium**

If a torrent contains `.srt`/`.ass` files alongside the video, they could be detected and served. HereSphere supports the `subtitles` array natively.

**Changes:**
- Check selected files for subtitle extensions
- Unrestrict subtitle links and include in the `subtitles` response array

---

### 12. Add Authentication
**Priority: Medium | Effort: Low**

Anyone on the local network can browse and download the entire library. HereSphere supports sending auth headers.

**Changes:**
- Add optional token-based auth (env var `HERESPHERE_AUTH_TOKEN`)
- Check `Authorization` header on all heresphere blueprint routes
- Skip auth for browser view if desired (or protect both)

---

## Architecture

### 13. Singleton Pattern Improvement
**Priority: Low | Effort: Medium**

`_thumb_service` and `_user_data` are module-level globals. With multiple gunicorn workers, each gets its own instance. `UserDataStore` writes to disk but has race conditions between workers.

**Changes:**
- Move to Flask app context extensions (`app.extensions['user_data']`)
- Or use file locking (`fcntl.flock`) for cross-process safety

---

### 14. Non-Blocking Thumbnail Generation
**Priority: Low | Effort: High**

The first request to `/heresphere/thumb/<id>` blocks while ffmpeg runs (up to 30s).

**Changes:**
- Return a placeholder image immediately
- Queue thumbnail generation in a background thread
- Serve the real thumbnail once available (client polls or uses cache-busting)
