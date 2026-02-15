"""Image validation utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)


def validate_image_bytes(data: bytes, filename: str) -> bool:
    """Validate that the bytes represent a readable image."""
    settings = get_settings()

    # Check file size
    if len(data) > settings.max_image_size_bytes:
        raise ValueError(
            f"File size ({len(data) / (1024 * 1024):.1f}MB) exceeds "
            f"{settings.max_image_size_mb}MB limit"
        )

    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.supported_ext_set:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported: {', '.join(sorted(settings.supported_ext_set))}"
        )

    # Try opening with Pillow to verify it's a valid image
    try:
        from io import BytesIO
        img = Image.open(BytesIO(data))
        img.verify()
    except Exception as e:
        raise ValueError(f"Invalid or corrupt image file: {e}")

    return True


def validate_image_path(path: Path) -> bool:
    """Validate that a file path points to a readable image."""
    settings = get_settings()

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    ext = path.suffix.lower()
    if ext not in settings.supported_ext_set:
        return False  # Skip silently for batch processing

    # Check file size
    file_size = path.stat().st_size
    if file_size > settings.max_image_size_bytes:
        raise ValueError(
            f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds "
            f"{settings.max_image_size_mb}MB limit"
        )

    return True


def collect_images_from_folder(
    folder: Path, recursive: bool = False
) -> list[Path]:
    """Collect all supported image files from a folder."""
    settings = get_settings()
    images: list[Path] = []

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    if recursive:
        for ext in settings.supported_ext_set:
            images.extend(folder.rglob(f"*{ext}"))
    else:
        for ext in settings.supported_ext_set:
            images.extend(folder.glob(f"*{ext}"))

    # Sort for deterministic ordering
    images.sort(key=lambda p: p.name.lower())

    return images
