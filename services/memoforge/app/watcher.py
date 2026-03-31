from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import settings
from .graph import create_run_record, run_workflow

if TYPE_CHECKING:
    pass

# Extensions that trigger automatic run creation when dropped in incoming/
_WATCHED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    ".txt", ".md", ".rst", ".json", ".csv",
}


class _IncomingHandler(FileSystemEventHandler):
    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in _WATCHED_EXTENSIONS:
            return

        lang = settings.watcher_lang
        instruction = (
            f"添付ファイル「{path.name}」を整理し、内容を研究メモとしてまとめてください。"
            if lang == "ja"
            else f"Organize the attached file '{path.name}' into a research note."
        )
        initial_run = create_run_record(
            instruction=instruction,
            file_paths=[str(path)],
            lang=lang,
        )
        thread = threading.Thread(
            target=_run_job,
            kwargs={
                "run_id": initial_run["run_id"],
                "created_at": initial_run["created_at"],
                "instruction": instruction,
                "file_paths": [str(path)],
                "lang": lang,
            },
            daemon=True,
            name=f"memoforge-watch-{initial_run['run_id']}",
        )
        thread.start()


def _run_job(run_id: str, created_at: str, instruction: str, file_paths: list[str], lang: str) -> None:
    try:
        run_workflow(
            instruction=instruction,
            file_paths=file_paths,
            run_id=run_id,
            created_at=created_at,
            lang=lang,
        )
    except Exception:
        return


_observer: Observer | None = None


def start_watcher() -> None:
    global _observer
    if not settings.watcher_enabled:
        return
    incoming = settings.incoming_dir
    incoming.mkdir(parents=True, exist_ok=True)
    _observer = Observer()
    _observer.schedule(_IncomingHandler(), str(incoming), recursive=False)
    _observer.start()


def stop_watcher() -> None:
    global _observer
    if _observer is not None:
        _observer.stop()
        _observer.join()
        _observer = None


def watcher_status() -> dict[str, Any]:
    return {
        "enabled": settings.watcher_enabled,
        "running": _observer is not None and _observer.is_alive(),
        "watching": str(settings.incoming_dir),
        "lang": settings.watcher_lang,
    }
