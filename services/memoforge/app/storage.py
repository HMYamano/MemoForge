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

# ── BM25 index cache ──────────────────────────────────────────────────────────
# Rebuilt only when the set of note files or their modification times change.
_bm25_cache: dict[str, Any] = {
    "bm25": None,
    "note_paths": [],
    "docs": [],
    "key": None,  # frozenset of (path, mtime) tuples
}


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


def save_run_chat_index(run_id: str, payload: dict[str, Any]) -> Path:
    path = settings.chat_indexes_dir / f"{run_id}.json"
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def load_run_chat_index(run_id: str) -> dict[str, Any] | None:
    path = settings.chat_indexes_dir / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_run_chat_thread(run_id: str, messages: list[dict[str, Any]]) -> Path:
    path = settings.chat_threads_dir / f"{run_id}.json"
    _atomic_write_text(path, json.dumps(messages, ensure_ascii=False, indent=2))
    return path


def load_run_chat_thread(run_id: str) -> list[dict[str, Any]]:
    path = settings.chat_threads_dir / f"{run_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def clear_run_chat_thread(run_id: str) -> None:
    path = settings.chat_threads_dir / f"{run_id}.json"
    if path.exists():
        path.unlink()


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


def save_markdown_note(title: str, body: str, tags: list[str] | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stamp}_{slugify(title, allow_unicode=True)[:80]}.md"
    path = settings.notes_dir / filename
    if tags:
        tag_line = ", ".join(tags)
        body = f"---\ntags: [{tag_line}]\ncreated: {stamp}\n---\n\n{body}"
    _atomic_write_text(path, body)
    return path


def parse_note_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-like frontmatter block. Returns (meta, body_without_frontmatter)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict[str, Any] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        # tags: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            meta[key.strip()] = [t.strip() for t in val[1:-1].split(",") if t.strip()]
        else:
            meta[key.strip()] = val
    return meta, body


def list_notes(tag: str | None = None) -> list[dict[str, Any]]:
    """Return metadata for all notes, optionally filtered by tag."""
    out: list[dict[str, Any]] = []
    for path in sorted(settings.notes_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        meta, body = parse_note_frontmatter(text)
        note_tags: list[str] = meta.get("tags", [])
        if tag and tag not in note_tags:
            continue
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        out.append({
            "filename": path.name,
            "path": str(path),
            "title": title,
            "tags": note_tags,
            "created": meta.get("created", ""),
            "mtime": path.stat().st_mtime,
            "snippet": body[:300].strip(),
        })
    return out


def load_note(filename: str) -> dict[str, Any] | None:
    path = settings.notes_dir / filename
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse_note_frontmatter(text)
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem
    return {
        "filename": path.name,
        "path": str(path),
        "title": title,
        "tags": meta.get("tags", []),
        "created": meta.get("created", ""),
        "body": body,
        "raw": text,
    }


def delete_note(filename: str) -> bool:
    path = settings.notes_dir / filename
    if not path.exists():
        return False
    path.unlink()
    # Invalidate BM25 cache so next search picks up the deletion.
    _bm25_cache["key"] = None
    return True


def update_note_body(filename: str, new_body: str) -> bool:
    """Overwrite note body, preserving existing frontmatter."""
    path = settings.notes_dir / filename
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta, _ = parse_note_frontmatter(text)
    if meta:
        tag_line = ", ".join(meta.get("tags", []))
        created = meta.get("created", "")
        new_text = f"---\ntags: [{tag_line}]\ncreated: {created}\n---\n\n{new_body}"
    else:
        new_text = new_body
    _atomic_write_text(path, new_text)
    _bm25_cache["key"] = None
    return True


def _get_bm25_index() -> tuple[Any, list[Path], list[str]]:
    """Return a cached BM25 index, rebuilding only when notes change."""
    note_paths = sorted(settings.notes_dir.glob("*.md"))
    cache_key = frozenset((str(p), p.stat().st_mtime) for p in note_paths)
    if _bm25_cache["key"] == cache_key and _bm25_cache["bm25"] is not None:
        return _bm25_cache["bm25"], _bm25_cache["note_paths"], _bm25_cache["docs"]
    docs = [p.read_text(encoding="utf-8", errors="ignore") for p in note_paths]
    tokenized = [simple_tokens(doc) for doc in docs]
    bm25 = BM25Okapi(tokenized) if tokenized else None
    _bm25_cache["bm25"] = bm25
    _bm25_cache["note_paths"] = note_paths
    _bm25_cache["docs"] = docs
    _bm25_cache["key"] = cache_key
    return bm25, note_paths, docs


def search_related_notes(query: str, k: int | None = None) -> list[dict[str, Any]]:
    bm25, note_paths, docs = _get_bm25_index()
    if not note_paths or bm25 is None:
        return []
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
