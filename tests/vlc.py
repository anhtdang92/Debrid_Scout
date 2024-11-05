import subprocess
import platform

def launch_vlc(link):
    try:
        if platform.system() == 'Darwin':  # macOS
            vlc_path = "/Applications/VLC.app/Contents/MacOS/VLC"
        else:
            raise Exception("Unsupported operating system")

        # Launch VLC
        process = subprocess.Popen([vlc_path, link], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"Failed to launch VLC: {stderr.decode('utf-8')}")
        else:
            print(f"VLC launched successfully with link: {link}")

    except Exception as e:
        print(f"Error: {e}")

# Replace with an actual video link
launch_vlc("https://example.com/path/to/video.mp4")
