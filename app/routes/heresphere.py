from flask import Blueprint, jsonify, request
import subprocess

heresphere_bp = Blueprint('heresphere', __name__)

@heresphere_bp.route('/launch_heresphere', methods=['POST'])
def launch_heresphere():
    data = request.json
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    # Command to start HereSphere with the video URL
    try:
        subprocess.Popen(["heresphere.exe", video_url])
        return jsonify({"message": "HereSphere launched successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
