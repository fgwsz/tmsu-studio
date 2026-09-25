"""缩略图缓存：图片直接用原文件，视频用 ffmpeg 抓帧并缓存。"""
import hashlib
import subprocess
from pathlib import Path

from .config import IMAGE_EXT, THUMB_DIR, THUMB_VIDEO_SEEK, THUMB_WIDTH, VIDEO_EXT


class ThumbnailCache:
    def __init__(self, cache_dir: Path = THUMB_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, path: Path | str) -> str | None:
        p = Path(path)
        if not p.is_file():
            return None
        ext = p.suffix.lower()
        if ext in IMAGE_EXT:
            return str(p)
        if ext in VIDEO_EXT:
            return self._video_thumb(p)
        return None

    def _video_thumb(self, path: Path) -> str | None:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None

        key = hashlib.md5(f"{path}|{mtime}".encode()).hexdigest()
        out = self.cache_dir / f"{key}.jpg"
        if out.exists():
            return str(out)

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-ss", str(THUMB_VIDEO_SEEK),
                 "-i", str(path),
                 "-frames:v", "1",
                 "-vf", f"scale={THUMB_WIDTH}:-1",
                 str(out)],
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        return str(out) if out.exists() else None

    def needs_generation(self, path: Path | str) -> bool:
        """判断是否需要 ffmpeg 抓帧。图片和已缓存的视频返回 False。"""
        p = Path(path)
        if not p.is_file():
            return False
        ext = p.suffix.lower()
        if ext in IMAGE_EXT:
            return False
        if ext not in VIDEO_EXT:
            return False
        try:
            mtime = p.stat().st_mtime
        except OSError:
            return False
        key = hashlib.md5(f"{p}|{mtime}".encode()).hexdigest()
        return not (self.cache_dir / f"{key}.jpg").exists()
