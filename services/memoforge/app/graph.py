from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .chat_tools import build_run_chat_index
from .config import settings
from .document_tools import extract_document
from .ollama_client import OllamaClient
from .prompts import (
    get_plan_prompt,
    get_review_prompt,
    get_revision_prompt,
    get_structure_prompt,
    get_system_supervisor,
    get_tag_prompt,
)
from .storage import load_run, now_iso, save_markdown_note, save_run, save_run_chat_index, search_related_notes

STEP_PROGRESS: dict[str, int] = {
    "queued": 0,
    "intake": 12,
    "extract": 38,
    "retrieve": 52,
    "structure": 71,
    "review": 84,
    "revise": 92,
    "accept": 92,
    "save": 100,
}


class MemoState(TypedDict, total=False):
    run_id: str
    instruction: str
    file_paths: list[str]
    lang: str
    plan: list[str]
    logs: list[dict[str, Any]]
    extracted_docs: list[dict[str, Any]]
    related_notes: list[dict[str, Any]]
    draft_markdown: str
    final_markdown: str
    saved_note_path: str
    review: dict[str, Any]
    tags: list[str]
    created_at: str
    updated_at: str
    status: str
    progress: int
    current_step: str
    error_message: str


def _log(state: MemoState, step: str, message: str, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    logs = list(state.get("logs", []))
    payload = {"time": now_iso(), "step": step, "message": message}
    if extra:
        payload["extra"] = extra
    logs.append(payload)
    return logs


def _build_run_payload(state: MemoState) -> dict[str, Any]:
    note_path = state.get("saved_note_path")
    final_markdown = state.get("final_markdown") or state.get("draft_markdown", "")
    status = state.get("status") or ("completed" if note_path else "running")
    progress = int(state.get("progress", STEP_PROGRESS.get(state.get("current_step", "queued"), 0)))
    current_step = state.get("current_step", "queued")
    # NOTE: extracted_docs is intentionally omitted from the persisted payload.
    # It can be large (full document text + vision notes) and is only needed
    # during the workflow execution. load_run() will therefore never return it.
    return {
        "run_id": state["run_id"],
        "created_at": state["created_at"],
        "updated_at": state.get("updated_at", now_iso()),
        "instruction": state["instruction"],
        "file_paths": state.get("file_paths", []),
        "lang": state.get("lang", "ja"),
        "plan": state.get("plan", []),
        "logs": state.get("logs", []),
        "related_notes": state.get("related_notes", []),
        "review": state.get("review", {}),
        "note_path": note_path,
        "final_markdown": final_markdown,
        "tags": state.get("tags", []),
        "status": status,
        "progress": progress,
        "current_step": current_step,
        "error_message": state.get("error_message", ""),
    }


def _persist_state(
    state: MemoState,
    *,
    status: str | None = None,
    current_step: str | None = None,
    progress: int | None = None,
    error_message: str | None = None,
) -> MemoState:
    next_state: MemoState = dict(state)
    if status is not None:
        next_state["status"] = status
    if current_step is not None:
        next_state["current_step"] = current_step
    if progress is not None:
        next_state["progress"] = progress
    if error_message is not None:
        next_state["error_message"] = error_message
    next_state["updated_at"] = now_iso()
    save_run(next_state["run_id"], _build_run_payload(next_state))
    return next_state


def _persist_node_result(state: MemoState, delta: MemoState, step: str) -> MemoState:
    merged: MemoState = {
        **state,
        **delta,
        "status": "running",
        "current_step": step,
        "progress": STEP_PROGRESS[step],
        "error_message": "",
        "updated_at": now_iso(),
    }
    save_run(merged["run_id"], _build_run_payload(merged))
    return {
        **delta,
        "status": "running",
        "current_step": step,
        "progress": STEP_PROGRESS[step],
        "error_message": "",
        "updated_at": merged["updated_at"],
    }


def build_initial_state(
    instruction: str,
    file_paths: list[str],
    *,
    run_id: str | None = None,
    created_at: str | None = None,
    status: str = "queued",
    lang: str = "ja",
) -> MemoState:
    timestamp = created_at or now_iso()
    return {
        "run_id": run_id or uuid.uuid4().hex[:12],
        "created_at": timestamp,
        "updated_at": timestamp,
        "instruction": instruction,
        "file_paths": file_paths,
        "lang": lang,
        "logs": [],
        "status": status,
        "progress": STEP_PROGRESS["queued"],
        "current_step": "queued",
        "error_message": "",
    }


def create_run_record(instruction: str, file_paths: list[str], *, run_id: str | None = None, lang: str = "ja") -> dict[str, Any]:
    state = build_initial_state(instruction, file_paths, run_id=run_id, status="queued", lang=lang)
    save_run(state["run_id"], _build_run_payload(state))
    return _build_run_payload(state)


_FALLBACK_PLAN: dict[str, list[str]] = {
    "ja": [
        "依頼文から目的と期待する出力を整理する",
        "添付資料から主要情報を抽出する",
        "関連ノートを参照して背景を補強する",
        "依頼に沿った形式で再構成する",
        "レビューして保存する",
    ],
    "en": [
        "Clarify the goal and expected output from the instruction",
        "Extract key information from attached materials",
        "Supplement background using related notes",
        "Reconstruct in the format requested by the user",
        "Review and save",
    ],
}

_LOG_MESSAGES: dict[str, dict[str, str]] = {
    "ja": {
        "intake": "依頼内容を整理しました。",
        "extract": "資料の抽出が完了しました。",
        "retrieve": "関連ノートを検索しました。",
        "structure": "依頼に沿った草案を作成しました。",
        "review": "草案をレビューしました。",
        "revise": "レビュー結果を反映しました。",
        "accept": "草案をそのまま採用しました。",
        "save": "出力を保存しました。",
        "error": "ワークフローの実行中にエラーが発生しました。",
    },
    "en": {
        "intake": "Instruction organized.",
        "extract": "Document extraction complete.",
        "retrieve": "Related notes searched.",
        "structure": "Draft created in the requested format.",
        "review": "Draft reviewed.",
        "revise": "Review feedback applied.",
        "accept": "Draft accepted as-is.",
        "save": "Output saved.",
        "error": "An error occurred during workflow execution.",
    },
}


def _lmsg(state: MemoState, step: str) -> str:
    lang = state.get("lang", "ja")
    return _LOG_MESSAGES.get(lang, _LOG_MESSAGES["ja"]).get(step, step)


def intake_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="intake", progress=STEP_PROGRESS["intake"], error_message="")
    lang = state.get("lang", "ja")
    client = OllamaClient()
    files = [Path(path).name for path in state.get("file_paths", [])]
    raw = client.chat(
        settings.reasoning_model,
        [
            {"role": "system", "content": get_system_supervisor(lang)},
            {"role": "user", "content": get_plan_prompt(lang).format(instruction=state["instruction"], files=json.dumps(files, ensure_ascii=False))},
        ],
        format_json=True,
    )
    try:
        plan = json.loads(raw).get("plan", [])
    except Exception:
        plan = _FALLBACK_PLAN.get(lang, _FALLBACK_PLAN["ja"])
    return _persist_node_result(
        state,
        {
            "plan": plan,
            "logs": _log(state, "intake", _lmsg(state, "intake"), {"plan": plan}),
        },
        "intake",
    )


def extract_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="extract", progress=STEP_PROGRESS["extract"], error_message="")
    lang = state.get("lang", "ja")
    extracted = [extract_document(Path(path), lang=lang) for path in state.get("file_paths", [])]
    summary = [
        {
            "name": doc["name"],
            "type": doc["type"],
            "text_chars": len(doc.get("text", "")),
            "vision_notes": len(doc.get("vision_notes", [])),
        }
        for doc in extracted
    ]
    return _persist_node_result(
        state,
        {
            "extracted_docs": extracted,
            "logs": _log(state, "extract", _lmsg(state, "extract"), {"documents": summary}),
        },
        "extract",
    )


def retrieve_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="retrieve", progress=STEP_PROGRESS["retrieve"], error_message="")
    query_parts = [state["instruction"]]
    for doc in state.get("extracted_docs", []):
        query_parts.append(doc.get("text", "")[:1500])
        query_parts.extend(doc.get("vision_notes", []))
    related = search_related_notes("\n".join(query_parts), k=settings.max_related_notes)
    return _persist_node_result(
        state,
        {
            "related_notes": related,
            "logs": _log(state, "retrieve", _lmsg(state, "retrieve"), {"count": len(related)}),
        },
        "retrieve",
    )


def structure_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="structure", progress=STEP_PROGRESS["structure"], error_message="")
    lang = state.get("lang", "ja")
    client = OllamaClient()
    extracted_for_prompt = [
        {
            "name": doc["name"],
            "type": doc["type"],
            "text_excerpt": doc.get("text", "")[:6000],
            "vision_notes": doc.get("vision_notes", []),
        }
        for doc in state.get("extracted_docs", [])
    ]
    related_for_prompt = [
        {"name": note["name"], "snippet": note["snippet"][:1200], "score": note["score"]}
        for note in state.get("related_notes", [])
    ]
    draft = client.chat(
        settings.reasoning_model,
        [
            {"role": "system", "content": get_system_supervisor(lang)},
            {
                "role": "user",
                "content": get_structure_prompt(lang).format(
                    instruction=state["instruction"],
                    extracted=json.dumps(extracted_for_prompt, ensure_ascii=False),
                    related_notes=json.dumps(related_for_prompt, ensure_ascii=False),
                ),
            },
        ],
    )
    return _persist_node_result(
        state,
        {
            "draft_markdown": draft,
            "logs": _log(state, "structure", _lmsg(state, "structure")),
        },
        "structure",
    )


def review_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="review", progress=STEP_PROGRESS["review"], error_message="")
    lang = state.get("lang", "ja")
    client = OllamaClient()
    raw = client.chat(
        settings.reasoning_model,
        [
            {"role": "system", "content": get_system_supervisor(lang)},
            {
                "role": "user",
                "content": get_review_prompt(lang).format(
                    instruction=state["instruction"],
                    draft=state["draft_markdown"][:14000],
                ),
            },
        ],
        format_json=True,
    )
    try:
        review = json.loads(raw)
    except Exception:
        review = {"verdict": "accept", "issues": [], "revision_instruction": ""}
    return _persist_node_result(
        state,
        {
            "review": review,
            "logs": _log(state, "review", _lmsg(state, "review"), review),
        },
        "review",
    )


def revise_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="revise", progress=STEP_PROGRESS["revise"], error_message="")
    lang = state.get("lang", "ja")
    client = OllamaClient()
    review = state.get("review", {})
    fallback_instruction = "草案を改善してください。" if lang == "ja" else "Please improve the draft."
    final_markdown = client.chat(
        settings.reasoning_model,
        [
            {"role": "system", "content": get_system_supervisor(lang)},
            {
                "role": "user",
                "content": get_revision_prompt(lang).format(
                    instruction=state["instruction"],
                    revision_instruction=review.get("revision_instruction", fallback_instruction),
                    draft=state["draft_markdown"],
                ),
            },
        ],
    )
    return _persist_node_result(
        state,
        {
            "final_markdown": final_markdown,
            "logs": _log(state, "revise", _lmsg(state, "revise")),
        },
        "revise",
    )


def pass_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="accept", progress=STEP_PROGRESS["accept"], error_message="")
    return _persist_node_result(
        state,
        {
            "final_markdown": state["draft_markdown"],
            "logs": _log(state, "accept", _lmsg(state, "accept")),
        },
        "accept",
    )


def _derive_note_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or "research_memo"

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped in {"---", "```"}:
            continue
        candidate = stripped.strip("|").strip()
        candidate = candidate.removeprefix("#").strip()
        candidate = candidate.lstrip("-*0123456789.> ").strip()
        if candidate and not set(candidate) <= {"-", ":", "|"}:
            return candidate[:80]

    return "research_memo"


def _extract_tags(markdown: str, lang: str) -> list[str]:
    client = OllamaClient()
    try:
        raw = client.chat(
            settings.reasoning_model,
            [{"role": "user", "content": get_tag_prompt(lang).format(markdown=markdown[:4000])}],
            format_json=True,
        )
        return json.loads(raw).get("tags", [])
    except Exception:
        return []


def save_node(state: MemoState) -> MemoState:
    state = _persist_state(state, status="running", current_step="save", progress=STEP_PROGRESS["save"], error_message="")
    lang = state.get("lang", "ja")
    final_markdown = state.get("final_markdown") or state.get("draft_markdown", "")
    title = _derive_note_title(final_markdown)
    tags = _extract_tags(final_markdown, lang)
    note_path = save_markdown_note(title=title, body=final_markdown, tags=tags)
    chat_index = build_run_chat_index(
        run_id=state["run_id"],
        instruction=state["instruction"],
        lang=state.get("lang", "ja"),
        extracted_docs=state.get("extracted_docs", []),
        related_notes=state.get("related_notes", []),
        final_markdown=final_markdown,
        note_path=str(note_path),
    )
    save_run_chat_index(state["run_id"], chat_index)
    result = {
        "saved_note_path": str(note_path),
        "final_markdown": final_markdown,
        "tags": tags,
        "logs": _log(state, "save", _lmsg(state, "save"), {"note_path": str(note_path), "tags": tags}),
    }
    return _persist_node_result(state, result, "save")


def should_revise(state: MemoState) -> str:
    verdict = str(state.get("review", {}).get("verdict", "accept")).lower()
    return "revise" if verdict == "revise" else "accept"


workflow = StateGraph(MemoState)
workflow.add_node("intake", intake_node)
workflow.add_node("extract", extract_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("structure", structure_node)
workflow.add_node("review", review_node)
workflow.add_node("revise", revise_node)
workflow.add_node("accept", pass_node)
workflow.add_node("save", save_node)
workflow.set_entry_point("intake")
workflow.add_edge("intake", "extract")
workflow.add_edge("extract", "retrieve")
workflow.add_edge("retrieve", "structure")
workflow.add_edge("structure", "review")
workflow.add_conditional_edges("review", should_revise, {"revise": "revise", "accept": "accept"})
workflow.add_edge("revise", "save")
workflow.add_edge("accept", "save")
workflow.add_edge("save", END)
app_graph = workflow.compile()


def run_workflow(
    instruction: str,
    file_paths: list[str],
    *,
    run_id: str | None = None,
    created_at: str | None = None,
    lang: str = "ja",
) -> dict[str, Any]:
    state = build_initial_state(
        instruction,
        file_paths,
        run_id=run_id,
        created_at=created_at,
        status="running",
        lang=lang,
    )
    # intake_node() calls _persist_state() itself as its first action,
    # so no pre-persist is needed here.

    try:
        result = app_graph.invoke(state)
        final_state: MemoState = {
            **state,
            **result,
            "status": "completed",
            "current_step": "save",
            "progress": STEP_PROGRESS["save"],
            "error_message": "",
            "updated_at": now_iso(),
        }
        payload = _build_run_payload(final_state)
        save_run(final_state["run_id"], payload)
        return payload
    except Exception as exc:
        existing = load_run(state["run_id"]) or _build_run_payload(state)
        failed_logs = list(existing.get("logs", []))
        failed_logs.append(
            {
                "time": now_iso(),
                "step": "error",
                "message": _LOG_MESSAGES.get(state.get("lang", "ja"), _LOG_MESSAGES["ja"])["error"],
                "extra": {"error": str(exc)},
            }
        )
        existing["logs"] = failed_logs
        existing["status"] = "failed"
        existing["error_message"] = str(exc)
        existing["updated_at"] = now_iso()
        save_run(state["run_id"], existing)
        raise
