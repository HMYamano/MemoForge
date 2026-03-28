from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi
from slugify import slugify

from .config import settings


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def simple_tokens(text: str) -> list[str]:
    return re.findall(r"[\w\-\u3040-\u30ff\u3400-\u9fff]+", text.lower())


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def save_run(run_id: str, payload: dict[str, Any]) -> Path:
    path = settings.runs_dir / f"{run_id}.json"
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def load_run(run_id: str) -> dict[str, Any] | None:
    path = settings.runs_dir / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(settings.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if len(runs) >= limit:
            break
    return runs


def save_markdown_note(title: str, body: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stamp}_{slugify(title, allow_unicode=True)[:80]}.md"
    path = settings.notes_dir / filename
    _atomic_write_text(path, body)
    return path


def search_related_notes(query: str, k: int | None = None) -> list[dict[str, Any]]:
    note_paths = sorted(settings.notes_dir.glob("*.md"))
    if not note_paths:
        return []
    docs = [p.read_text(encoding="utf-8", errors="ignore") for p in note_paths]
    tokenized = [simple_tokens(doc) for doc in docs]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(simple_tokens(query))
    ranked = sorted(zip(note_paths, docs, scores), key=lambda x: x[2], reverse=True)
    out = []
    for path, doc, score in ranked[: (k or settings.max_related_notes)]:
        out.append(
            {
                "path": str(path),
                "name": path.name,
                "score": float(score),
                "snippet": doc[:1000],
            }
        )
    return out
