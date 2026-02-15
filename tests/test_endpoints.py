"""Tests for health and language endpoints."""

from __future__ import annotations


def test_health(client):
    """Health endpoint returns status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "loaded_languages" in data
    assert data["version"] == "1.0.0"


def test_languages(client):
    """Languages endpoint returns supported languages."""
    response = client.get("/ocr/languages")
    assert response.status_code == 200
    data = response.json()
    codes = [lang["code"] for lang in data["languages"]]
    assert "hi" in codes
    assert "mr" in codes
    assert "te" in codes
    assert "ta" in codes


def test_single_ocr_invalid_language(client, sample_image_bytes):
    """Single OCR rejects unsupported language."""
    response = client.post(
        "/ocr/single?lang=xx",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    assert response.status_code == 400
    assert "Unsupported language" in response.json()["detail"]


def test_single_ocr_invalid_file_type(client):
    """Single OCR rejects non-image files."""
    response = client.post(
        "/ocr/single?lang=hi",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400


def test_batch_ocr_invalid_language(client):
    """Batch OCR rejects unsupported language."""
    response = client.post(
        "/ocr/batch",
        json={"folder_path": "/tmp/nonexistent", "lang": "xx"},
    )
    assert response.status_code == 400
    assert "Unsupported language" in response.json()["detail"]


def test_batch_ocr_missing_folder(client):
    """Batch OCR rejects nonexistent folder."""
    response = client.post(
        "/ocr/batch",
        json={"folder_path": "/tmp/does_not_exist_12345", "lang": "hi"},
    )
    assert response.status_code == 404
    assert "Folder not found" in response.json()["detail"]
