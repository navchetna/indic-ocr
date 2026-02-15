"""Shared test fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generate a minimal valid PNG image for testing."""
    img = Image.new("RGB", (100, 50), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_file(tmp_path: Path, sample_image_bytes: bytes) -> Path:
    """Save a sample image to a temp directory and return its path."""
    img_path = tmp_path / "test_image.png"
    img_path.write_bytes(sample_image_bytes)
    return img_path


@pytest.fixture
def sample_image_folder(tmp_path: Path, sample_image_bytes: bytes) -> Path:
    """Create a temp folder with multiple sample images."""
    folder = tmp_path / "test_images"
    folder.mkdir()
    for i in range(3):
        (folder / f"page_{i:03d}.png").write_bytes(sample_image_bytes)
    return folder
