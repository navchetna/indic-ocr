"""Application configuration and settings."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Paths
    home_dir: str
    ocr_output_base: str = ""
    ocr_input_base: str = ""

    # Server
    ocr_host: str = "0.0.0.0"
    ocr_port: int = 8111
    log_level: str = "INFO"

    # Model (using defaults via lang parameter only)
    preload_languages: str = ""  # Comma-separated, e.g. "hi,mr"

    # Limits
    max_image_size_mb: int = 50

    # Image extensions
    supported_extensions: str = ".png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **data):
        super().__init__(**data)
        # Expand paths with home_dir if not set explicitly
        if not self.ocr_output_base:
            self.ocr_output_base = f"{self.home_dir}/outputs/ocr"
        if not self.ocr_input_base:
            self.ocr_input_base = f"{self.home_dir}/resources/ocr_inputs"

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def supported_ext_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.supported_extensions.split(",")}

    @property
    def preload_language_list(self) -> list[str]:
        if not self.preload_languages.strip():
            return []
        return [lang.strip() for lang in self.preload_languages.split(",") if lang.strip()]

    @property
    def single_output_dir(self) -> Path:
        return Path(self.ocr_output_base) / "single"

    @property
    def batch_output_dir(self) -> Path:
        return Path(self.ocr_output_base) / "batch"


# Supported languages configuration
SUPPORTED_LANGUAGES = {
    "hi": {"name": "Hindi", "script": "Devanagari"},
    "mr": {"name": "Marathi", "script": "Devanagari"},
    "te": {"name": "Telugu", "script": "Telugu"},
    "ta": {"name": "Tamil", "script": "Tamil"},
}


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
