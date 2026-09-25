"""视频/图片元数据（Adapter 模式）。"""
import json
import subprocess
from pathlib import Path

from .config import IMAGE_EXT, VIDEO_EXT


def _run(cmd: list, timeout: int = 5) -> str:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        ).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _video_metadata(path: Path) -> dict[str, str]:
    out = _run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    if not out:
        return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

    r: dict[str, str] = {}
    duration = float(fmt.get("duration") or 0)
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        r["时长"] = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    if video.get("width"):
        r["分辨率"] = f"{video['width']}x{video['height']}"
    if video.get("r_frame_rate"):
        num, _, den = video["r_frame_rate"].partition("/")
        try:
            r["帧率"] = f"{float(num) / float(den or 1):.2f}"
        except (ValueError, ZeroDivisionError):
            pass
    if video.get("codec_name"):
        r["视频编码"] = video["codec_name"]
    if audio.get("codec_name"):
        r["音频编码"] = audio["codec_name"]
    size = int(fmt.get("size") or 0)
    if size:
        r["大小"] = _human_size(size)
    return r


def _image_metadata(path: Path) -> dict[str, str]:
    out = _run([
        "exiftool", "-j", "-DateTimeOriginal", "-Model", "-Make",
        "-LensModel", "-ExposureTime", "-FNumber", "-ISO", str(path),
    ])
    if not out:
        return {}
    try:
        data = json.loads(out)[0]
    except (json.JSONDecodeError, IndexError):
        return {}

    mapping = {
        "DateTimeOriginal": "拍摄时间",
        "Make": "品牌", "Model": "相机", "LensModel": "镜头",
        "ExposureTime": "快门", "FNumber": "光圈", "ISO": "ISO",
    }
    return {v: str(data[k]) for k, v in mapping.items() if data.get(k)}


def get_metadata(path: Path | str) -> dict[str, str]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in VIDEO_EXT:
        return _video_metadata(p)
    if ext in IMAGE_EXT:
        return _image_metadata(p)
    return {}
