from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from .config import settings
from .ollama_client import OllamaClient
from .prompts import get_chat_prompt, get_chat_system_prompt
from .storage import load_run_chat_index, now_iso, save_run_chat_index, simple_tokens

MAX_CHUNK_CHARS = 1200
MAX_CONTEXT_CHUNKS = 6
MAX_HISTORY_MESSAGES = 8
_PDF_PAGE_RE = re.compile(r"(?m)^## Page (\d+)\s*$")


def _clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", str(text or "").strip())


def _split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    if not paragraphs:
        return [cleaned[:max_chars]]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
            continue

        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            step = max_chars - 120
            while start < len(paragraph):
                piece = paragraph[start : start + max_chars].strip()
                if piece:
                    chunks.append(piece)
                start += max(step, 1)
            continue

        current = candidate

    if current:
        chunks.append(current)
    return chunks


def _extract_note_title(markdown: str) -> str:
    for line in str(markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or "Research note"
    return "Research note"


def _parse_pdf_pages(text: str) -> list[tuple[int | None, str]]:
    matches = list(_PDF_PAGE_RE.finditer(text or ""))
    if not matches:
        cleaned = _clean_text(text)
        return [(None, cleaned)] if cleaned else []

    pages: list[tuple[int | None, str]] = []
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = _clean_text(text[start:end])
        if body:
            pages.append((page_number, body))
    return pages


def _chunk_label(source_name: str, kind: str, page: int | None = None, part: int | None = None) -> str:
    label = source_name or "source"
    if page is not None:
        label = f"{label} page {page}"
    if kind == "vision":
        label = f"{label} figure notes"
    elif kind == "related_note":
        label = f"{label} related note"
    elif kind == "generated_note":
        label = f"{label} organized note"
    if part and part > 1:
        label = f"{label} part {part}"
    return label


def _add_chunks(
    chunks: list[dict[str, Any]],
    *,
    source_name: str,
    source_type: str,
    kind: str,
    text: str,
    page: int | None = None,
) -> None:
    parts = _split_text(text)
    for part_index, part in enumerate(parts, start=1):
        chunks.append(
            {
                "source_name": source_name,
                "source_type": source_type,
                "kind": kind,
                "page": page,
                "part": part_index,
                "label": _chunk_label(source_name, kind, page=page, part=part_index if len(parts) > 1 else None),
                "text": part,
            }
        )


def _document_chunks(document: dict[str, Any]) -> list[dict[str, Any]]:
    source_name = str(document.get("name") or "document")
    source_type = str(document.get("type") or "document")
    chunks: list[dict[str, Any]] = []

    if source_type == "pdf":
        for page_number, page_text in _parse_pdf_pages(str(document.get("text") or "")):
            _add_chunks(
                chunks,
                source_name=source_name,
                source_type=source_type,
                kind="text",
                text=page_text,
                page=page_number,
            )
        for index, vision_note in enumerate(document.get("vision_notes", []), start=1):
            _add_chunks(
                chunks,
                source_name=source_name,
                source_type=source_type,
                kind="vision",
                text=str(vision_note or ""),
                page=index,
            )
        return chunks

    if source_type == "image":
        for vision_note in document.get("vision_notes", []):
            _add_chunks(
                chunks,
                source_name=source_name,
                source_type=source_type,
                kind="vision",
                text=str(vision_note or ""),
            )
        return chunks

    if document.get("text"):
        _add_chunks(
            chunks,
            source_name=source_name,
            source_type=source_type,
            kind="text",
            text=str(document.get("text") or ""),
        )
    for vision_note in document.get("vision_notes", []):
        _add_chunks(
            chunks,
            source_name=source_name,
            source_type=source_type,
            kind="vision",
            text=str(vision_note or ""),
        )
    return chunks


def build_run_chat_index(
    *,
    run_id: str,
    instruction: str,
    lang: str,
    extracted_docs: list[dict[str, Any]] | None,
    related_notes: list[dict[str, Any]] | None,
    final_markdown: str,
    note_path: str | None = None,
) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    note_name = Path(note_path).name if note_path else "organized_note.md"

    if final_markdown.strip():
        _add_chunks(
            chunks,
            source_name=note_name,
            source_type="note",
            kind="generated_note",
            text=final_markdown,
        )

    for document in extracted_docs or []:
        chunks.extend(_document_chunks(document))

    for note in related_notes or []:
        snippet = _clean_text(str(note.get("snippet") or ""))
        if not snippet:
            continue
        _add_chunks(
            chunks,
            source_name=str(note.get("name") or "related_note.md"),
            source_type="related_note",
            kind="related_note",
            text=snippet,
        )

    for index, chunk in enumerate(chunks, start=1):
        chunk["chunk_id"] = f"chunk-{index:04d}"

    return {
        "run_id": run_id,
        "lang": "en" if lang == "en" else "ja",
        "instruction": instruction,
        "note_title": _extract_note_title(final_markdown),
        "note_path": note_path or "",
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def build_fallback_chat_index(run: dict[str, Any]) -> dict[str, Any]:
    return build_run_chat_index(
        run_id=str(run.get("run_id") or uuid.uuid4().hex[:12]),
        instruction=str(run.get("instruction") or ""),
        lang=str(run.get("lang") or "ja"),
        extracted_docs=[],
        related_notes=list(run.get("related_notes") or []),
        final_markdown=str(run.get("final_markdown") or ""),
        note_path=run.get("note_path"),
    )


def ensure_run_chat_index(run: dict[str, Any]) -> dict[str, Any] | None:
    run_id = str(run.get("run_id") or "").strip()
    if not run_id:
        return None

    existing = load_run_chat_index(run_id)
    if existing and existing.get("chunks"):
        return existing

    if not str(run.get("final_markdown") or "").strip():
        return None

    fallback = build_fallback_chat_index(run)
    save_run_chat_index(run_id, fallback)
    return fallback


def _rank_chunks(index: dict[str, Any], query: str, limit: int = MAX_CONTEXT_CHUNKS) -> list[dict[str, Any]]:
    chunks = [chunk for chunk in index.get("chunks", []) if str(chunk.get("text") or "").strip()]
    if not chunks:
        return []

    tokenized = [simple_tokens(str(chunk.get("text") or "")) or ["_"] for chunk in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(simple_tokens(query) or ["_"])
    ranked = sorted(zip(chunks, scores), key=lambda item: item[1], reverse=True)

    selected: list[dict[str, Any]] = []
    for chunk, score in ranked:
        if score <= 0 and selected:
            continue
        selected.append({**chunk, "score": float(score)})
        if len(selected) >= limit:
            break

    if selected:
        return selected
    return [{**chunk, "score": 0.0} for chunk in chunks[:limit]]


def _history_prompt(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return "(none)"

    lines: list[str] = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        role = "Assistant" if str(message.get("role")) == "assistant" else "User"
        content = _clean_text(str(message.get("content") or ""))
        if not content:
            continue
        lines.append(f"{role}: {content[:1200]}")
    return "\n".join(lines) if lines else "(none)"


def _fallback_answer(lang: str) -> str:
    if lang == "en":
        return "I could not find enough grounded context in this run to answer that confidently."
    return "\u3053\u306e run \u306b\u542b\u307e\u308c\u308b\u6839\u62e0\u3060\u3051\u3067\u306f\u3001\u78ba\u4fe1\u3092\u6301\u3063\u3066\u7b54\u3048\u3089\u308c\u308b\u6750\u6599\u304c\u8db3\u308a\u307e\u305b\u3093\u3002"


def answer_run_question(
    run: dict[str, Any],
    *,
    message: str,
    mode: str = "ask",
    lang: str | None = None,
    thread: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    chat_index = ensure_run_chat_index(run)
    if not chat_index:
        raise ValueError("chat index is not available for this run")

    resolved_lang = "en" if (lang or run.get("lang")) == "en" else "ja"
    resolved_mode = "discuss" if mode == "discuss" else "ask"
    conversation = list(thread or [])

    user_turns = [
        str(item.get("content") or "").strip()
        for item in conversation
        if str(item.get("role")) == "user" and str(item.get("content") or "").strip()
    ]
    retrieval_query = "\n".join([*user_turns[-3:], message])
    context_chunks = _rank_chunks(chat_index, retrieval_query)
    citations = [
        {
            "id": f"[{index}]",
            "label": chunk.get("label") or chunk.get("source_name") or "source",
            "source_name": chunk.get("source_name") or "source",
            "source_type": chunk.get("source_type") or "source",
            "page": chunk.get("page"),
            "snippet": str(chunk.get("text") or "")[:320],
        }
        for index, chunk in enumerate(context_chunks, start=1)
    ]
    context_block = "\n\n".join(
        f"{citation['id']} {citation['label']}\n{chunk.get('text', '')}"
        for citation, chunk in zip(citations, context_chunks)
    )

    raw = OllamaClient().chat(
        settings.reasoning_model,
        [
            {"role": "system", "content": get_chat_system_prompt(resolved_lang)},
            {
                "role": "user",
                "content": get_chat_prompt(resolved_lang).format(
                    instruction=str(run.get("instruction") or ""),
                    note_title=str(chat_index.get("note_title") or "Research note"),
                    mode=resolved_mode,
                    history=_history_prompt(conversation),
                    context=context_block or "(none)",
                    message=message.strip(),
                    response_language="English" if resolved_lang == "en" else "Japanese",
                ),
            },
        ],
        format_json=True,
    )

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {"answer": raw.strip(), "follow_ups": [], "citations": []}

    answer = str(parsed.get("answer") or "").strip() or _fallback_answer(resolved_lang)
    cited_ids = {str(item).strip() for item in parsed.get("citations", []) if str(item).strip()}
    used_citations = [citation for citation in citations if citation["id"] in cited_ids]
    if not used_citations:
        used_citations = citations[: min(3, len(citations))]

    follow_ups = [
        str(item).strip()
        for item in parsed.get("follow_ups", [])
        if str(item).strip()
    ][:3]

    return {
        "id": f"chat-{uuid.uuid4().hex[:8]}",
        "role": "assistant",
        "content": answer,
        "mode": resolved_mode,
        "created_at": now_iso(),
        "citations": used_citations,
        "follow_ups": follow_ups,
    }
