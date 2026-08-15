from pathlib import Path

from .config import get_settings


def storage_root() -> Path:
    root = get_settings().storage_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_bytes(relpath: str, data: bytes) -> str:
    path = storage_root() / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def read_bytes(relpath: str) -> bytes:
    path = Path(relpath)
    if not path.is_absolute():
        path = storage_root() / relpath
    return path.read_bytes()


def disk_usage_bytes() -> int:
    root = storage_root()
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
