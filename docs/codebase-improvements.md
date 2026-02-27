# Debrid Scout — Codebase Improvement Plan

Full-project audit across routes, services, frontend, tests, config, and infrastructure.
Items are grouped by priority tier (P0–P3) with specific file:line references.

---

## P0 — Critical / Security

### 1. Add Request Timeouts to All HTTP Calls ✅
All `requests.get()`/`requests.post()`/`requests.delete()` in the service and route layers lack a `timeout` parameter. A hung upstream API (Real-Debrid, Jackett) will block the Flask worker indefinitely.

**Files:**
- `app/services/real_debrid.py:44,77,95,115,132,155` — every RD API call
- `app/services/rd_cached_link.py:124` — RD instant-availability check
- `app/services/rd_download_link.py:241` — cleanup DELETE call
- `app/routes/torrent.py:67,97,116,186` — direct HTTP calls in routes

**Fix:** Add `timeout=(5, 15)` (connect, read) to every call. Expose via config:
```
RD_API_TIMEOUT=15
JACKETT_TIMEOUT=20
```

---

### 2. Fix Auth Bypass in HereSphere `before_request` ✅
`heresphere.py:87` — when `HERESPHERE_AUTH_TOKEN` is set, auth is skipped if `_wants_html()` returns True. A malicious client can send `Accept: text/html` to bypass auth and still receive JSON from POST endpoints.

**Fix:** Only exempt `GET` requests that actually render HTML (library_index with `_wants_html()`). All POST endpoints should always require auth when token is set.

---

### 3. Stop Logging Auth Tokens ✅
`heresphere.py:79` and `deovr.py:37` log all request headers at INFO level, including `Authorization: Bearer <token>`.

**Fix:** Redact sensitive headers before logging:
```python
safe_headers = {k: ('***' if k.lower() == 'authorization' else v)
                for k, v in request.headers}
```

---

### 4. Fix innerHTML XSS with File Names ✅
`app/static/js/scripts.js:835` — torrent file names from the API are injected via `innerHTML` with only `.replace(/[._]/g, " ")`, which doesn't escape HTML entities.

**Fix:** Use `textContent` or `document.createTextNode()` instead of `innerHTML`.

---

### 5. Docker: Don't Run as Root / Don't Copy .env ✅
- `Dockerfile` has no `USER` directive — container runs as root.
- `Dockerfile:15` — `COPY .env* ./` copies secrets into the image layer.

**Fix:**
```dockerfile
RUN useradd -m appuser
USER appuser
# Remove COPY .env* — inject env vars at runtime instead
```

---

### 6. Validate JACKETT_API_KEY at Startup ✅
`app/__init__.py:65-67` validates `REAL_DEBRID_API_KEY` but not `JACKETT_API_KEY`. Missing key causes silent failures on search.

**Fix:** Add validation in `create_app()` with at least a warning log.

---

### 7. Enforce SECRET_KEY in Production ✅
`app/__init__.py:72-80` — generates a random key if `SECRET_KEY` is not set, with only a warning. In production, sessions break on every restart.

**Fix:** Raise `RuntimeError` when `FLASK_ENV=production` and `SECRET_KEY` is missing.

---

## P1 — High Priority

### 8. Add GitHub Actions CI/CD ✅
No `.github/workflows/` directory exists. Tests, linting, and security scanning only run locally (if at all).

**Fix:** Add workflow with: `pytest`, `ruff` or `flake8`, `pip-audit`, and ESLint.

---

### 9. Add Missing Service Layer Tests
Zero test coverage for:
- `RDCachedLinkService` — cache-checking pipeline
- `RDDownloadLinkService` — full download orchestration
- `FileHelper` — `is_video_file()`, `format_file_size()`, `simplify_filename()`

**Fix:** Add unit tests with mocked HTTP responses for each service's happy path and error paths.

---

### 10. Add SSE Streaming Endpoint Tests
`tests/test_search.py` has no tests for `POST /stream` — the primary search endpoint.

**Fix:** Test SSE event format, cancellation, error responses, malformed JSON body.

---

### 11. Use `requests.Session()` for Connection Pooling ✅
`real_debrid.py` creates a new connection per API call. `jackett_search.py` creates a new `cloudscraper` session per query.

**Fix:** Create a single `requests.Session()` per `RealDebridService` instance. Reuse the cloudscraper session across searches.

---

### 12. Extract Duplicate Code Between Routes
File-to-link mapping, video file filtering, and projection detection are duplicated across `heresphere.py`, `deovr.py`, and `torrent.py`.

**Duplicated patterns:**
- Build `restricted_map` from files+links: `heresphere.py:486-490`, `deovr.py:171-175`, `torrent.py:131-134`
- Filter video files: `heresphere.py:407-411`, `deovr.py:182-185`
- Auth check: `heresphere.py:75-90`, `deovr.py:40-45`

**Fix:** Extract to shared helpers in `vr_helper.py` or a new `torrent_helper.py`.

---

### 13. Standardize Error Response Format ✅
Inconsistent error shapes across routes:
- `search.py` → `{"error": "..."}`
- `torrent.py` → `{"status": "error", "error": "..."}`
- `heresphere.py` → `{"status": "error", "error": "..."}`

**Fix:** Create a shared `error_response(message, status_code)` helper. Standardize on one shape.

---

### 14. Add Docker Health Check ✅
No `HEALTHCHECK` directive in the Dockerfile. Container orchestrators can't detect unhealthy instances.

**Fix:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:5000/about || exit 1
```

---

### 15. Refactor `search_and_get_links` / `search_and_get_links_stream` Duplication
`rd_download_link.py` has two 140+ line methods (`search_and_get_links` at line 48 and `search_and_get_links_stream` at line 253) that share ~95% of logic. Only difference is SSE yields vs. return dict.

**Fix:** Extract shared pipeline into `_process_pipeline()` that yields results; sync method collects into list, streaming method yields SSE events.

---

### 16. Add Rate-Limit Backoff for 429 Responses ✅
`real_debrid.py:35-37` uses a fixed 0.2s sleep for rate limiting. If RD returns HTTP 429, the service crashes instead of backing off.

**Fix:** Check response status; on 429, read `Retry-After` header and sleep accordingly.

---

### 17. Pin Dependency Upper Bounds ✅
`requirements.txt` uses `>=` with no upper bounds. A breaking major release could silently break the app.

**Fix:** Use `~=` (compatible release) or explicit upper bounds: `Flask~=3.1.0`, `requests~=2.32`.

---

## P2 — Medium Priority

### 18. Add Accessibility to Modal Dialogs ✅
`app/templates/rd_manager.html:110` — modal is a plain `<div>` without `role="dialog"`, `aria-modal="true"`, focus trap, or Escape key handler.

**Fix:** Add proper ARIA attributes and keyboard event handling:
```javascript
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeModal();
});
```

---

### 19. Add ARIA Live Regions for Dynamic Content ✅
- `app/templates/index.html:48` — `#search-error` needs `role="alert"` and `aria-live="assertive"`
- `#search-progress` needs `role="status"` and `aria-live="polite"`

---

### 20. Add Thread Safety to Shared Globals ✅
- `search.py:16` — `_active_searches` dict is mutable shared state with no lock
- `heresphere.py:48` — `_torrent_cache` dict is mutable shared state with no lock

**Fix:** Wrap with `threading.Lock()` or use `Flask-Caching` for in-process caching.

---

### 21. Add Cache-Control Headers for Thumbnails ✅
`heresphere.py` thumbnail endpoint returns images with no caching headers. Browsers re-fetch on every page load.

**Fix:** Add `Cache-Control: public, max-age=86400` for cached thumbnails.

---

### 22. Move Direct HTTP Calls in `torrent.py` to Service Layer ✅
`torrent.py:67-69,97-98,116-118,186-187` make direct `requests.*` calls to the RD API instead of using `RealDebridService`.

**Fix:** Add missing methods to `RealDebridService` (e.g., `delete_torrent()`, `unrestrict_link()` are already there; use them).

---

### 23. Add Input Validation ✅
- `search.py:41-44` — no upper bound on search limit (user can submit `limit=999999`)
- `torrent.py:61,68` — no format validation on `torrent_id` URL parameter
- `heresphere.py:372,598,629,660` — same missing ID validation

**Fix:** Validate torrent IDs match expected format (alphanumeric, max length). Cap search limit at 100 or 500.

---

### 24. Add Search Result Empty State ✅
`app/templates/index.html` — when search returns 0 results, shows "Complete! Found 0 torrents" with no guidance.

**Fix:** Add "No torrents found. Try different keywords or check indexer availability." message.

---

### 25. Add Resource Cleanup for Thumbnails ✅
Cached thumbnails and previews never expire. Disk usage grows unbounded.

**Fix:** Add a TTL-based cleanup (e.g., delete files older than 7 days) on app startup or via a periodic task.

---

### 26. Make Hardcoded Values Configurable ✅
| Value | Location | Suggested Env Var |
|-------|----------|-------------------|
| Cache TTL (300s) | `__init__.py:23` | `ACCOUNT_CACHE_TTL` |
| Rate limit (0.2s) | `real_debrid.py:33` | `RD_RATE_LIMIT_DELAY` |
| Log max size (10KB) | `__init__.py:102` | `LOG_MAX_BYTES` |
| Jackett retries (5) | `jackett_search.py:137` | `JACKETT_RETRY_COUNT` |

---

### 27. Improve ESLint Configuration
`eslint.config.mjs` only sets `globals.browser` — no rules, no error detection, no unused variable checks.

**Fix:** Add recommended ruleset and Prettier integration.

---

## P3 — Low Priority / Polish

### 28. Add Python Type Checking
No `mypy` or `pyright` configured. Type hints are partial (services have some, routes have none).

**Fix:** Add `mypy` to dev deps, create `pypy.ini`, gradually annotate.

---

### 29. Fill In CHANGELOG.md
`CHANGELOG.md:5-26` has version headers from `standard-version` but no actual change descriptions.

**Fix:** Populate with features/fixes from git history.

---

### 30. Add Color Contrast Fix ✅
`styles.css:26` — `--text-muted: #6b6d7b` against `--bg-base: #0f0f13` has ~4.3:1 contrast ratio, borderline for WCAG AA at small sizes.

**Fix:** Lighten muted text to `#8a8c9a` for 5:1 ratio.

---

### 31. Improve CSS Button Specificity
`styles.css:371-471` — `.button`, `.submit-button`, `.delete-button`, `.debrid-button` overlap. Could use BEM methodology or class composition.

---

### 32. Add Responsive Breakpoint for 600-768px
`styles.css` has breakpoints at 768px and 480px, but nothing for tablet portrait (600-768px).

---

### 33. Add Loading Skeletons for Library Pages
HereSphere and RD Manager pages show no visual feedback while API data loads. Add CSS skeleton placeholders.

---

### 34. Add `bencodepy` Alternative
`bencodepy` hasn't been updated since 2021. Consider `bencode.py` or `better-bencode` as alternatives.

---

### 35. Close Cloudscraper Sessions ✅
`jackett_search.py` creates a new `cloudscraper` session per query without closing it. Could leak connections in high-concurrency scenarios.

**Fix:** Use context manager or explicit `.close()` after use.

---

### 36. Add Account Route Smoke Test
`/account/account` has zero test coverage. Add a basic render test.

---

### 37. Improve Error Logging with Stack Traces ✅
`rd_download_link.py:175-176` and `thumbnail.py:111,178` log errors without stack traces.

**Fix:** Use `logger.exception()` instead of `logger.error()` in except blocks.

---

---

## Summary

| Priority | Count | Completed | Theme |
|----------|-------|-----------|-------|
| P0 Critical | 7 | 7 ✅ | Timeouts, auth bypass, XSS, Docker security |
| P1 High | 10 | 6 | CI/CD, connection pooling, rate limiting, error format |
| P2 Medium | 10 | 9 | Accessibility, validation, caching, config |
| P3 Polish | 10 | 3 | Color contrast, session cleanup, error logging |
| **Total** | **37** | **25** | |

**Remaining items (12):** #9 (service tests), #10 (SSE tests), #12 (extract duplicate code), #15 (refactor search duplication), #27 (ESLint config), #28 (type checking), #29 (changelog), #31 (CSS specificity), #32 (responsive breakpoint), #33 (loading skeletons), #34 (bencodepy alternative), #36 (account route test).
