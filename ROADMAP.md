# 🚀 Debrid Scout Project Roadmap

This roadmap outlines the planned features and improvements for the Debrid Scout project. Our goal is to enhance functionality, performance, and user experience.

---

## 📌 Version 1.1

### 🛠️ Refactoring and Performance Improvements

- **Refactor `Get_RD_Download_Link.py` into an Importable Module** 🔄
  - **Objective:** Convert the script into a module that can be directly imported and called within the Flask application.
  - **Benefits:**
    - Eliminates the need for subprocess calls.
    - Improves performance and reduces overhead.
    - Simplifies error handling and debugging.
  - **Tasks:**
    - [ ] Move `Get_RD_Download_Link.py` into the `services` package.
    - [ ] Refactor the script to expose necessary functions or classes.
    - [ ] Update `search.py` to import and use the new module.
    - [ ] Remove subprocess calls and related error handling.
    - [ ] Test to ensure functionality remains consistent.

- **Improve Error Messages and Logging** 📝
  - **Objective:** Provide more informative error messages to users and improve logging for easier debugging.
  - **Tasks:**
    - [ ] Review all routes and services for error handling.
    - [ ] Standardize error responses across the application.
    - [ ] Enhance logging with appropriate log levels and messages.

---

## 🔐 Version 1.2

### 👤 User Authentication and Profiles

- **Implement User Authentication** 🔑
  - **Objective:** Add user login and registration functionality to allow personalized settings and preferences.
  - **Benefits:**
    - Secure access to user-specific features.
    - Enable future features like saved searches and favorites.
  - **Tasks:**
    - [ ] Integrate Flask-Login or a similar authentication library.
    - [ ] Create user models and database tables.
    - [ ] Implement registration, login, and logout routes.
    - [ ] Secure sensitive routes and functions.

- **User Profiles and Preferences** ⚙️
  - **Objective:** Allow users to customize their experience.
  - **Tasks:**
    - [ ] Create profile pages where users can update their information.
    - [ ] Enable users to set preferences like default search limits.

---

## ⚙️ Version 1.3

### ⏱️ Asynchronous Task Handling

- **Introduce Asynchronous Processing with Celery** 🧵
  - **Objective:** Handle long-running tasks asynchronously to improve application responsiveness.
  - **Benefits:**
    - Prevents blocking of the main thread during intensive operations.
    - Enhances user experience with background processing.
  - **Tasks:**
    - [ ] Set up Celery with a message broker like Redis or RabbitMQ.
    - [ ] Refactor long-running tasks to be executed asynchronously.
    - [ ] Provide users with progress indicators or notifications.

---

## 🌟 Version 1.4

### 🔄 Additional Features and Integrations

- **Support for Additional Torrent Indexers** 🗂️
  - **Objective:** Expand the range of torrent sources for searches.
  - **Tasks:**
    - [ ] Integrate with more indexers via Jackett or other APIs.
    - [ ] Allow users to select preferred indexers.

- **Content Recommendation System** 🤖
  - **Objective:** Implement a system to recommend content based on user history.
  - **Tasks:**
    - [ ] Analyze user search and download history.
    - [ ] Provide personalized recommendations on the dashboard.

---

## 📝 Future Considerations

- **Mobile-Friendly Interface** 📱
  - Optimize the UI for better usability on mobile devices.

- **Multi-Language Support** 🌐
  - Localize the application to support multiple languages.

- **Dockerization** 🐳
  - Provide Docker configurations for easier deployment.

---

## 🤝 Contributions

Contributions and suggestions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/anhtdang92/Debrid_Scout).

---

*Note: This roadmap is a living document and may evolve over time based on project needs and user feedback.*
