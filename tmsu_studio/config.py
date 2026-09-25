"""常量、路径、数据库根解析。"""
import os
from pathlib import Path

APP_NAME = "TMSU Studio"
APP_VERSION = "1.0.0"

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".m4v", ".wmv"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
AUDIO_EXT = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}

CONFIG_DIR = Path.home() / ".config" / "tmsu-studio"
CACHE_DIR = Path.home() / ".cache" / "tmsu-studio"
THUMB_DIR = CACHE_DIR / "thumbs"
STATE_FILE = CONFIG_DIR / "state.json"

THUMB_WIDTH = 480
THUMB_VIDEO_SEEK = 1
FACET_LIMIT = 200


def find_db_root(start: Path | None = None) -> Path:
    d = Path(start or Path.cwd()).resolve()
    while True:
        if (d / ".tmsu").is_dir():
            return d
        if d.parent == d:
            return Path.cwd().resolve()
        d = d.parent


def find_db_root_or_none(start: Path | None = None) -> Path | None:
    """从 start 向上找 .tmsu，返回其父目录；找不到返回 None。"""
    d = Path(start or Path.cwd()).resolve()
    while True:
        if (d / ".tmsu").is_dir():
            return d
        if d.parent == d:
            return None
        d = d.parent


def resolve_root() -> Path:
    env = os.environ.get("TMSU_ROOT")
    if env and (Path(env) / ".tmsu").is_dir():
        return Path(env).resolve()
    return find_db_root()


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)


def is_valid_db(path: Path | str) -> bool:
    p = Path(path)
    return p.is_dir() and (p / ".tmsu").is_dir()
