# app/services/vr_helper.py

"""
Shared VR utilities for HereSphere and DeoVR routes.

Consolidates video detection, projection guessing, and HereSphere launcher
logic that was previously duplicated across heresphere.py and deovr.py.
"""

import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

# Video extensions we consider playable
VIDEO_EXTS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.mpeg', '.mpg', '.m4v', '.ts', '.vob', '.mts',
}

# Known install paths for HereSphere
HERESPHERE_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"C:\Program Files\Steam\steamapps\common\HereSphere\HereSphere.exe",
    r"D:\SteamLibrary\steamapps\common\HereSphere\HereSphere.exe",
]


def is_video(filename):
    """Return True if filename looks like a video."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in VIDEO_EXTS)


def guess_projection(filename):
    """
    Guess VR projection from filename conventions.

    Returns (projection, stereo, fov, lens) tuple.

    Common patterns:
      _180_SBS, _180x180_SBS  → equirectangular, sbs, 180, Linear
      _360_TB                 → equirectangular360, tb, 360, Linear
      _FISHEYE190_SBS         → fisheye, sbs, 190, Linear
      _MKX200_SBS             → fisheye, sbs, 200, MKX200
      _MKX220_SBS             → fisheye, sbs, 220, MKX220
      _RF52                   → fisheye, sbs, 190, Linear
      _FLAT / _2D             → perspective, mono, 90, Linear
      (default)               → equirectangular, sbs, 180, Linear
    """
    upper = filename.upper()

    # Stereo mode
    if '_TB' in upper or '_OU' in upper:
        stereo = 'tb'
    else:
        stereo = 'sbs'  # SBS is the most common default

    # FOV & Lens
    fov = 180.0
    lens = 'Linear'

    # Screen type / projection
    if '_FISHEYE190' in upper or '_RF52' in upper:
        projection = 'fisheye'
        fov = 190.0
    elif '_MKX200' in upper:
        projection = 'fisheye'
        fov = 200.0
        lens = 'MKX200'
    elif '_MKX220' in upper:
        projection = 'fisheye'
        fov = 220.0
        lens = 'MKX220'
    elif '_FISHEYE' in upper:
        projection = 'fisheye'
        fov = 180.0
    elif '_360' in upper:
        projection = 'equirectangular360'
        fov = 360.0
    elif '_FLAT' in upper or '_2D' in upper:
        projection = 'perspective'
        stereo = 'mono'
        fov = 90.0
    else:
        projection = 'equirectangular'  # 180° equirect is the most common VR format

    return projection, stereo, fov, lens


# DeoVR uses different field names for projection types.
# Map from the canonical projection names to DeoVR's screenType values.
_DEOVR_SCREEN_TYPE_MAP = {
    'equirectangular': 'dome',
    'equirectangular360': 'sphere',
    'fisheye': 'fisheye',
    'perspective': 'flat',
}

# Fisheye variants that DeoVR treats as distinct screen types
_DEOVR_FISHEYE_OVERRIDES = {'MKX200': 'mkx200', 'MKX220': 'mkx200'}


def guess_projection_deovr(filename):
    """
    Guess VR projection for DeoVR format.

    Returns (screenType, stereoMode) using DeoVR's naming conventions.
    """
    projection, stereo, _fov, lens = guess_projection(filename)
    screen = _DEOVR_SCREEN_TYPE_MAP.get(projection, 'dome')

    # DeoVR uses specific screen types for MKX lenses and RF52
    upper = filename.upper()
    if lens in _DEOVR_FISHEYE_OVERRIDES:
        screen = _DEOVR_FISHEYE_OVERRIDES[lens]
    elif '_RF52' in upper:
        screen = 'rf52'

    return screen, stereo


def find_heresphere_exe():
    """
    Find HereSphere.exe from known install paths or PATH.

    Returns the path string if found, or None.
    """
    for path in HERESPHERE_PATHS:
        if os.path.isfile(path):
            return path
    return shutil.which("HereSphere") or shutil.which("HereSphere.exe")


def launch_heresphere_exe(video_url):
    """
    Launch HereSphere.exe with the given video URL.

    Returns (success: bool, error_message: str or None).
    """
    exe_path = find_heresphere_exe()
    if not exe_path:
        logger.error("HereSphere.exe not found in any known location.")
        return False, "HereSphere.exe not found. Please ensure it is installed via Steam."

    try:
        subprocess.Popen([exe_path, video_url])
        return True, None
    except Exception as e:
        logger.error(f"Failed to launch HereSphere: {e}")
        return False, "Failed to launch HereSphere"
