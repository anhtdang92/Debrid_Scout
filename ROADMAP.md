# 🚀 Debrid Scout Project Roadmap

This roadmap outlines the planned features, improvements, and critical bug fixes for the Debrid Scout project. Our goal is to enhance functionality, performance, and user experience.

---

## 📌 Version 1.1.2 (Current Version)

### 🛠️ Refactoring and Performance Improvements

- **Refactor `Get_RD_Download_Link.py` into an Importable Module** ✅
  - **Objective:** Convert the script into a module that can be directly imported and called within the Flask application.
  - **Tasks:**
    - [x] Move `Get_RD_Download_Link.py` into the `services` package.
    - [x] Refactor the script to expose necessary functions or classes.
    - [x] Update `search.py` to import and use the new module.
    - [x] Remove subprocess calls and related error handling.
    - [x] Test to ensure functionality remains consistent.

### 🐞 High-Priority Bug Fixes and Issues

#### **1. Overwriting the Document with `document.write`** ✅

- **Issue:** The use of `document.write` in `static/js/scripts.js` overwrites the entire page, which is not the intended behavior and can cause unexpected issues.
- **Impact:** Affects user experience by disrupting the page's DOM, leading to potential loss of state and event listeners.
- **Tasks:**
  - [x] **Replace `document.write` with DOM Manipulation Methods**
    - Modify the JavaScript code to update specific parts of the page using DOM manipulation (e.g., `innerHTML`, `appendChild`).
    - Ensure that the updated code targets the correct DOM elements to display results.
  - [x] **Implement Progressive Enhancement**
    - Ensure the application functions correctly even if JavaScript is disabled.
    - Improve user experience by enhancing functionality for browsers that support JavaScript without breaking the core features.

#### **2. Client-Side Streaming Functionality** ✅

- **Issue:** The current implementation attempts to launch VLC on the server, which is not practical. Browsers have security restrictions that prevent directly launching external applications from client-side JavaScript.
- **Impact:** Users are unable to stream content directly in VLC from the web application, limiting functionality.
- **Tasks:**
  - [x] **Adjust JavaScript Functions for Client-Side Streaming**
    - Modify the `launchVLC` function to handle client-side streaming appropriately.
    - Explore using custom URL protocols (e.g., `vlc://`) or generating playlist files (`.m3u8`) that users can open in VLC.
    - Provide clear instructions to users on how to use these features, considering browser security policies.
  - [x] **Handle Browser Security Considerations**
    - Research and implement methods that comply with browser security restrictions.
    - Ensure that any new implementation does not introduce security vulnerabilities.

#### **3. Exposing Sensitive Data in Templates and Logs** 🔒

- **Issue:** Sensitive information like `REAL_DEBRID_API_KEY` is being injected into templates and potentially exposed in logs.
- **Impact:** This poses a significant security risk as API keys could be leaked, compromising user accounts and data.
- **Tasks:**
  - [x] **Remove `REAL_DEBRID_API_KEY` from Template Context**
    - Update `app/__init__.py` to exclude `REAL_DEBRID_API_KEY` from the `inject_static_resources` context processor.
  - [x] **Modify Configuration Debug Statements**
    - Update `config.py` to avoid printing sensitive information in debug statements.
    - Ensure that no sensitive data is output to the console or logs in any environment.

### 📈 Other Improvements

- **Enhance Error Handling and User Feedback** ✅
  - [x] Implement consistent error responses across all API endpoints.
  - [x] Provide clear and user-friendly error messages in the UI.

- **Update Documentation and Comments** ✅
  - [x] Add docstrings to functions and classes.
  - [x] Use inline comments to explain complex logic.

---

## 🛡️ Version 1.2

### 🔐 User Authentication and Profiles

- **Implement User Authentication** 🔑
  - **Tasks:**
    - [ ] Integrate Flask-Login or a similar authentication library.
    - [ ] Create user models and database tables.
    - [ ] Implement registration, login, and logout routes.
    - [ ] Secure sensitive routes and functions.

- **User Profiles and Preferences** ⚙️
  - **Tasks:**
    - [ ] Create profile pages where users can update their information.
    - [ ] Enable users to set preferences like default search limits.

---

## 🔄 Version 1.3

### ⚡ Asynchronous Processing and Performance Enhancements

- **Implement Asynchronous API Calls** ⏱️
  - **Objective:** Improve application responsiveness by making non-blocking API requests.
  - **Tasks:**
    - [ ] Integrate asynchronous programming using `asyncio` or similar.
    - [ ] Refactor API calls to be asynchronous.
    - [ ] Update front-end to handle asynchronous responses.

---

## 🔧 Version 1.1.3 — Code Quality & Bug Fixes

### 🐞 Critical Fixes

- **#1 — Consolidate duplicated VR code** ✅
  - [x] Extract shared logic from `heresphere.py` and `deovr.py` into `app/services/vr_helper.py`
  - [x] Deduplicate `_is_video()`, `_guess_projection()`, `_HERESPHERE_PATHS`, and `launch_heresphere()`

- **#2 — Missing JSON validation in torrent routes** ✅
  - [x] Add `request.is_json` checks before `request.get_json()` in `unrestrict_link()` and `delete_torrents()`
  - Files: `app/routes/torrent.py`

- **#3 — Uncaught ValueError in pagination** ✅
  - [x] Use `request.args.get('page', 1, type=int)` with fallback to prevent crash on `?page=abc`
  - Files: `app/routes/torrent.py`

- **#4 — Missing top-level `requests` import in rd_download_link.py** ✅
  - [x] Move `import requests` from inside `_try_delete_torrent()` to module-level imports
  - Files: `app/services/rd_download_link.py`

- **#5 — Streaming search returns restricted (unusable) links** ✅
  - [x] Add link unrestriction to `search_and_get_links_stream()` to match synchronous pipeline
  - Files: `app/services/rd_download_link.py`

### 🔐 Security Fixes

- **#9 — Debug print statements leak info in config.py** ✅
  - [x] Replace all `print()` calls with proper `logging` or remove them
  - [x] Use `app.debug` from config instead of hardcoded `debug=True` in `main.py`
  - Files: `app/config.py`, `app/main.py`

- **#10 — Random SECRET_KEY regenerated on every restart** ✅
  - [x] Add warning log when SECRET_KEY env var is not set (invalidates sessions/CSRF)
  - [x] Remove redundant `load_dotenv()` call from `__init__.py`
  - Files: `app/__init__.py`

### 🐛 Bug-Level Issues

- **#6 — Silent bencodepy decode errors in Jackett search**
  - [ ] Add specific exception handling for bencode decode failures
  - Files: `app/services/jackett_search.py`

- **#7 — Fragile date parsing in HereSphere**
  - [ ] Improve `_parse_rd_date()` robustness for edge-case date formats
  - Files: `app/routes/heresphere.py`

- **#8 — No input validation in `format_file_size()`** ✅
  - [x] Guard against negative/invalid size values
  - Files: `app/services/file_helper.py`

### 🧹 Code Quality

- **#13 — Inconsistent JSON error/success response formats**
  - [ ] Standardize all route responses to `{"status": "...", "message": "..."}`
  - Files: `app/routes/torrent.py`, `app/routes/heresphere.py`, `app/routes/deovr.py`

- **#18 — Hardcoded VLC paths (Windows-only)** ✅
  - [x] Add macOS/Linux paths and prefer `shutil.which()` first
  - Files: `app/routes/torrent.py`

### 🧪 Test Gaps

- **#15 — No test coverage for VR routes**
  - [ ] Add `tests/test_vr_routes.py` for heresphere and deovr endpoints
- **#16 — Test fixtures don't set required env vars**
  - [ ] Fix `tests/conftest.py` so tests don't depend on external `.env`
- **#17 — No test for `/cancel` endpoint**
  - [ ] Add cancel search test to `tests/test_search.py`

---

## 🚀 Future Versions

### 🤖 Version 1.4

- **Integrate Additional Indexers** 🔍
  - **Tasks:**
    - [ ] Research and select additional torrent indexers.
    - [ ] Update the search functionality to query multiple sources.
    - [ ] Handle data normalization and deduplication.

- **Implement Recommendation System** 🎯
  - **Tasks:**
    - [ ] Develop algorithms to suggest content based on user behavior.
    - [ ] Integrate recommendations into the user interface.

---

## 🤝 Contributions

Contributions and suggestions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/anhtdang92/Debrid_Scout).

For a complete list of known issues and to report new ones, please visit our [GitHub Issues page](https://github.com/anhtdang92/Debrid_Scout/issues).

---

*Note: This roadmap is a living document and may evolve over time based on project needs and user feedback.*

---

### **Next Steps**

- **Prioritize the High-Priority Issues in Version 1.1.2:**
  - Address the `document.write` issue and client-side streaming functionality as immediate tasks.
  - Ensure that sensitive data is not exposed in templates, logs, or error messages.

- **Update Issue Tracker:**
  - Create corresponding issues in your GitHub repository for these tasks.
  - Assign them to the Version 1.1.2 milestone and mark them as high priority.
