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
