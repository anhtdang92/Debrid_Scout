# Debrid Scout Project Index

This file provides a comprehensive index of the Debrid Scout project files. The project is a Python Flask web application that integrates Jackett and Real-Debrid for searching, caching, resolving, and downloading torrents directly from the browser or VR headsets (HereSphere).

## Root Configuration Files
- `.env` / `.env.template` - Environment variables (API keys, URLs).
- `.gitignore`, `.gitattributes` - Git configuration.
- `package.json`, `eslint.config.mjs` - Node configuration for linting HTML/JS text.
- `requirements.txt` - Python backend dependencies.
- `README.md` - High-level project documentation and setup.
- `ROADMAP.md` - Legacy tracking of project features and plans.
- `CHANGELOG.md` - Version history.
- `LICENSE` - Open-source license file.

## Flask Application `app/`

### Core App Setup
- `app/__init__.py` - Flask app factory, blueprint registration, CSRF protection, and environment variable initialization. 
- `app/config.py` - Contains environment validation rules and app configuration constants.
- `app/main.py` - Main entry point to run the Flask application server.

### Routes `app/routes/`
- `__init__.py` - Blueprint index.
- `search.py` - The core search view. Handles user queries, interfaces with Jackett and RD services, and returns torrent results.
- `account.py` - Handles account information and cached requests to the RD API to display user stats in the navbar.
- `info.py` - Static pages like the "About" and "Contact" views.
- `torrent.py` - Handles downloading and un-restricting links from RD, as well as Deleting Torrents from the RD cache manager.
- `heresphere.py` - Web API to allow HereSphere (VR Video Player) to natively browse torrents and play media directly. Support for `180_SBS` vr projection detection.

### Services `app/services/`
The service layer replaced legacy shell scripts to improve reliability and speed.
- `__init__.py` - Service index.
- `real_debrid.py` - Handles direct HTTP communication with the Real-Debrid API (authentication, torrent lists, file restriction).
- `jackett_search.py` - Issues Torznab API queries to Jackett, parses XML results into JSON-friendly dicts, filters categories.
- `rd_cached_link.py` - Verifies torrent info-hashes against Real-Debrid cache.
- `rd_download_link.py` - Manages adding magnets to RD, selecting valid video files, and un-restricting download links.
- `file_helper.py` - Statics and standard generic file formatting (video extensions, sizes, etc).

### Static Assets `app/static/`
- `css/styles.css` - Custom styles and CSS variables.
- `js/scripts.js` - Client-side interaction handled with native vanilla JS (event listeners, modals, UI overlay).
- `apple-touch-icon.png`, `favicon-32x32.png` - Browser tab icons.
- `logo.png`, `logo-bg.png`, `logo-1.png` - Application branding.
- `category_icons.json`, `category_mapping.json` - Jackett Torznab ID mapping to font-awesome icons.
- `video_extensions.json` - Video file extension filters loaded on the client side.

### Templates `app/templates/`
- `base.html` - Master HTML structure included on all pages. Includes global tags and assets.
- `index.html` - Search page landing layout and UI rendering for torrent entries.
- `rd_manager.html` - Dedicated UI logic for viewing downloaded and active Torrents on your remote Real-Debrid cache.
- `account_info.html` - User stats UI element (top right corner).
- `navbar.html` - Main header UI navigation.
- `about.html`, `contact.html` - Static text pages.
- `partials/search_results.html` - Client side search fragments.

## Auxiliary Directories

### Tests `tests/`
- `test_main.py` - Placeholder / skeleton unit test scripts.
- `vlc.py` - Placeholder / testing utilities for VLC player integration.

### Scripts `scripts/` (Legacy Subprocess Scripts)
- `Get_RD_Cached_Link.py` - *Deprecated*. Old script for checking cached links.
- `Get_RD_Download_Link.py` - *Deprecated*. Old script for downloading links.
- `Jackett_Search_v2.py` - *Deprecated*. Old wrapper for finding items on Jackett.
- `custom_tree_with_contents.py` - Testing utility script.

### Logs `logs/`
- `app.log`, `app.log.10` - Standard rotating log files used for backend trace execution and component errors.
