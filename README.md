
# Debrid Scout - Comprehensive Torrent Search & Real-Debrid Integration

![Debrid Scout Logo](https://github.com/anhtdang92/Debrid_Scout/blob/main/app/static/logo.png)  

Debrid Scout is a **Python** application combining **Jackett**'s powerful multi-indexer torrent search with **Real-Debrid** caching and unrestriction. Designed with a user-friendly interface and modular backend, Debrid Scout offers streamlined torrent access and download capabilities, making it the ideal tool for torrent enthusiasts.

---

## 🚀 Key Features

- 🔍 **Unified Torrent Search**: Uses Jackett to search multiple torrent indexers, retrieving detailed metadata for each result.
- 🚀 **Real-Debrid Caching and Unrestriction**: Instantly check if torrents are cached on Real-Debrid and obtain unrestricted download links.
- 📊 **Detailed Metadata Display**: Extracts torrent details, including title, seeders, leeches, categories, and file sizes.
- 📐 **Modular API Structure**: Built with extensibility in mind, Debrid Scout is structured for easy expansion or customization.
- ⚠️ **Enhanced Error Handling**: Robust logging and error messages for easy troubleshooting.
- ☁️ **Cloudflare Bypass Support**: Uses `cloudscraper` to overcome Cloudflare challenges on protected indexers.
  
---

## 📋 Prerequisites

- 🐍 **Python 3.x**: Install Python 3 if not already present on your system.
- 🖥️ **Jackett Instance**: Set up a Jackett instance with configured torrent indexers.
- 🌐 **Real-Debrid Account**: A premium Real-Debrid account for caching and unrestriction features.
- 🔐 **Environment Variables**: Set `JACKETT_URL`, `JACKETT_API_KEY`, and `REAL_DEBRID_API_KEY` in a `.env` file.

---

## 🛠 Installation

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/anhtdang92/Debrid_Scout.git
   ```
   ![Clone Repo](https://img.icons8.com/fluent/48/000000/clone.png)

2. **Navigate to Project Directory**  
   ```bash
   cd Debrid_Scout
   ```
   ![Navigate Directory](https://img.icons8.com/ios-filled/50/000000/opened-folder.png)

3. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
   ![Install Dependencies](https://img.icons8.com/color/48/000000/python.png)

---

## ⚙ Environment Setup

📄 A template `.env` file is included to simplify setup for new installations. To get started:

1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Fill in the required values in the `.env` file:
   ```plaintext
   DEBUG_MODE=True
   FLASK_ENV=development
   JACKETT_API_KEY=your-jackett_api_key
   REAL_DEBRID_API_KEY=your-real_debrid_api_key
   JACKETT_URL=http://localhost:9117
   ```

Ensure `JACKETT_URL` begins with `http://` or `https://`.

---

## 🖥 Usage Guide

### Basic Workflow

1. **Run the Application**  
   ```bash
   python debrid_scout.py
   ```
   ![Start Application](https://img.icons8.com/color/48/000000/play.png)

2. **Enter Search Details**  
   - Provide a search query and specify the number of results.
   - Example: `alien romulus 2160p` with a limit of 10 results.

3. **View Results**  
   - Debrid Scout displays detailed torrent info, Real-Debrid caching status, and direct links if cached.

📷 **Sample Search Result**:  
![Sample Search Result](https://github.com/anhtdang92/Debrid_Scout/blob/main/app/static/sample_search_result.png)  

### Example Workflow

- **Search Query**: `alien romulus 2160p`
- **Output**: Torrent data with title, seeders, leeches, categories, caching status, and downloadable links.

---

## 🔍 Code Structure Overview

### Core Modules and Scripts

#### 1. `Get_RD_Download_Link.py`
*Manages interactions with Real-Debrid, including torrent addition, file selection, and download link retrieval.*

- **Functions**:
  - `add_magnet(magnet_link)`: Adds a magnet link to Real-Debrid.
  - `select_files(torrent_id)`: Selects files in the torrent for unrestricted download.
  - `unrestrict_links(links)`: Unrestricts links for direct download URLs.

#### 2. `Jackett_Search.py`
*Conducts Jackett searches and extracts metadata from the XML results.*

- **Functions**:
  - `search_jackett(api_key, base_url, query, limit)`: Executes Jackett search and returns XML data.
  - `parse_results(xml_data)`: Extracts title, seeders, leeches, and categories from XML results.
  - `get_infohash_from_torrent_url`: Retrieves infohashes from `.torrent` files.

#### 3. `Get_RD_Cached_Link.py`
*Checks Real-Debrid for caching status and returns cached links.*

- **Functions**:
  - `call_jackett_vid_search(query, limit)`: Searches Jackett for video torrents.
  - `check_if_cached_on_real_debrid(infohash, expected_size)`: Confirms if a torrent is fully cached.

### Functionality Breakdown

1. **Configuration Loading**:  
   *Securely loads environment variables using `.env` files.*

2. **Metadata Extraction and Parsing**:  
   *Efficiently retrieves and parses torrent metadata, such as infohash and categories.*

3. **Real-Debrid API Interactions**:  
   *Checks Real-Debrid caching status and fetches unrestricted download links.*

4. **Error Handling**:  
   *Comprehensive logging and error messages for easier debugging.*

---

## ⚠ Potential Issues & Troubleshooting

### Common Issues

- **Missing Environment Variables**: Ensure `JACKETT_URL`, `JACKETT_API_KEY`, and `REAL_DEBRID_API_KEY` are set in `.env`.
- **Network Connectivity**: Verify your Jackett instance is accessible.
- **Cloudflare Challenges**: If `cloudscraper` fails to bypass, consider using FlareSolverr for more challenging sites.

### Error Messages & Resolutions

1. **`Environment Variable Not Found`**  
   *Check your `.env` file for missing keys.*

2. **`Cloudflare Challenge Failed`**  
   *Re-run the script or try adding FlareSolverr.*

3. **`XML Parsing Error`**  
   *Ensure Jackett is returning valid XML data.*

---

## Advanced Configuration

For power users, the following options can be customized:
- **Command-Line Arguments**: Specify search query and result limit directly via CLI.
- **Parallel Processing**: Enable multithreading in `Get_RD_Cached_Link.py` for faster Real-Debrid checks.
- **Rate Limiting**: Adjust API call rate limits if using a high number of indexers or Real-Debrid requests.

---

## 🛠 Planned Enhancements

1. **UI/Frontend Development**  
   *Integrate a web interface using Flask for enhanced usability.*

2. **Logging and Error Notifications**  
   *Add structured logging for better debugging and monitoring.*

3. **Cloudflare Bypass Options**  
   *Integrate FlareSolverr for improved handling of Cloudflare challenges.*

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork, modify, and submit a pull request. Areas of focus include:
- **Feature Additions**: Expand Jackett or Real-Debrid functionality.
- **Performance Enhancements**: Optimize caching checks and search logic.
- **Error Handling Improvements**: Additional logging and error tracking.

---

## 📜 License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## ✉ Contact

For questions, suggestions, or support, please open an issue on [GitHub](https://github.com/anhtdang92/Debrid_Scout) or contact via email.

---
