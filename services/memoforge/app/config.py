from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    reasoning_model: str = os.getenv("REASONING_MODEL", "qwen3:30b")
    vision_model: str = os.getenv("VISION_MODEL", "gemma3:27b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
    app_data_dir: Path = Path(os.getenv("APP_DATA_DIR", "/app/data"))
    notes_dir: Path = Path(os.getenv("NOTES_DIR", "/app/notes"))
    incoming_dir: Path = Path(os.getenv("INCOMING_DIR", "/app/incoming"))
    max_related_notes: int = int(os.getenv("MAX_RELATED_NOTES", "5"))
    pdf_vision_max_pages: int = int(os.getenv("PDF_VISION_MAX_PAGES", "4"))

    @property
    def runs_dir(self) -> Path:
        return self.app_data_dir / "runs"

    @property
    def uploads_dir(self) -> Path:
        return self.app_data_dir / "uploads"

    @property
    def rendered_pages_dir(self) -> Path:
        return self.app_data_dir / "rendered_pages"

    @property
    def chat_indexes_dir(self) -> Path:
        return self.app_data_dir / "chat_indexes"

    @property
    def chat_threads_dir(self) -> Path:
        return self.app_data_dir / "chat_threads"


settings = Settings()
for directory in [
    settings.app_data_dir,
    settings.notes_dir,
    settings.incoming_dir,
    settings.runs_dir,
    settings.uploads_dir,
    settings.rendered_pages_dir,
    settings.chat_indexes_dir,
    settings.chat_threads_dir,
]:
    directory.mkdir(parents=True, exist_ok=True)
