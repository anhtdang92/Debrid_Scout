# Debrid Scout - Torrent Search Application using Jackett

![Logo](https://github.com/anhtdang92/Debrid_Scout/blob/main/app/static/logo.png)

---

Debrid Scout is a **Python** application that empowers users to effortlessly search for torrents using **Jackett** across all configured indexers. With its sleek interface and powerful backend, it retrieves essential torrent information such as titles, seeders, leeches, categories, and infohashes. This README serves as a comprehensive guide for setting up, running, and maximizing your experience with Debrid Scout.

## 🚀 Features
- **Advanced Torrent Search**: Quickly search for torrents based on your input across multiple indexers.
- **Detailed Information Display**: View comprehensive torrent data including seeders, leeches, categories, and infohash.
- **Infohash Extraction**: Supports extraction of infohash from both magnet links and `.torrent` files.
- **Real-time Progress Tracking**: Monitors and displays the progress of Jackett searches and parsing results.

## 🛠 Future Updates
- **CloudFlare Bypass**: Implement FlareSolverr to enhance access to certain indexers like 1337x.

## 📋 Prerequisites
- **Python 3.x**: Ensure Python is installed on your machine.
- **Jackett Instance**: A running and accessible Jackett instance.
- **Environment Variables**: Set `JACKETT_URL` and `JACKETT_API_KEY` in a `.env` file.

## 🛠 Installation
1. Clone the repository or download the script to your local machine.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙ Environment Setup
Create a `.env` file in the root of your project directory and add the following variables:
```
JACKETT_URL=<your_jackett_url>
JACKETT_API_KEY=<your_jackett_api_key>
REAL_DEBRID_API_KEY=<your_real_debrid_api_key>
```
Make sure the URL starts with `http://` or `https://`. 

## 🖥 Usage
To run the application, execute the script:
```bash
python debrid_scout.py
```
When prompted, enter your search query and the desired number of results to fetch. Pressing Enter without inputting anything will use default values.

## 💡 Example Workflow
1. **Run the Script**: Execute `python debrid_scout.py`.
2. **Enter Query**: Input your desired search term, e.g., `alien romulus 2160p`.
3. **Receive Results**: The script will display detailed torrent information, including seeders, leeches, categories, and more.

## 🔍 Functions Overview
- **`load_environment()`**: Loads environment variables from the `.env` file.
- **`extract_infohash_from_magnet(magnet_link)`**: Extracts infohash from a given magnet link.
- **`get_infohash_from_torrent_url(torrent_urls)`**: Retrieves the infohash from a list of `.torrent` file URLs concurrently.
- **`search_jackett(api_key, base_url, query, limit)`**: Searches Jackett for torrents based on the provided query.
- **`parse_results(xml_data)`**: Parses XML data returned by Jackett and extracts relevant information.

## ⚠ Potential Errors
- **Environment Variables Not Set**: Ensure `JACKETT_URL` and `JACKETT_API_KEY` are correctly configured in the `.env` file.
- **Network Issues**: Verify that your Jackett instance is running and accessible.
- **XML Parsing Errors**: If data parsing fails, check the Jackett configuration and query parameters.

## 📄 Example `.env` File
```
JACKETT_URL=https://my-jackett-instance.com
JACKETT_API_KEY=my-secret-api-key
```

## 🤝 Contributing
Feel free to fork the repository, make modifications, and create pull requests. Contributions are welcome, especially regarding additional features or performance improvements.

## 📜 License
This project is licensed under the MIT License. See the LICENSE file for details.

## ✉ Contact
For questions or support, please open an issue on the GitHub repository.