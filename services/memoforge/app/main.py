from __future__ import annotations

import asyncio
import json
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .chat_tools import answer_run_question, ensure_run_chat_index
from .config import settings
from .graph import create_run_record, run_workflow
from .storage import clear_run_chat_thread, list_runs, load_run, load_run_chat_thread, now_iso, save_run_chat_thread

app = FastAPI(title="MemoForge", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _execute_run_job(run_id: str, created_at: str, instruction: str, file_paths: list[str], lang: str = "ja") -> None:
    try:
        run_workflow(
            instruction=instruction,
            file_paths=file_paths,
            run_id=run_id,
            created_at=created_at,
            lang=lang,
        )
    except Exception:
        # The failure state is already persisted by run_workflow.
        return


def _run_chat_ready(run: dict[str, Any]) -> bool:
    return bool(str(run.get("final_markdown") or "").strip())


def _chat_payload(run: dict[str, Any], messages: list[dict[str, Any]], *, ready: bool) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "ready": ready,
        "status": run.get("status", "queued"),
        "messages": messages,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "runs": list_runs(limit=20),
            "reasoning_model": settings.reasoning_model,
            "vision_model": settings.vision_model,
        },
    )


@app.get("/api/runs")
def api_runs(limit: int = 20) -> list[dict[str, Any]]:
    return list_runs(limit=limit)


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> dict[str, Any]:
    run = load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.post("/api/runs")
async def create_run(
    instruction: str = Form(...),
    files: list[UploadFile] | None = File(default=None),
    lang: str = Form("ja"),
):
    upload_dir = settings.uploads_dir
    saved_paths: list[str] = []
    if files:
        for upload in files:
            original_name = Path(upload.filename or "upload").name
            target = upload_dir / f"{uuid.uuid4().hex[:8]}_{original_name}"
            content = await upload.read()
            target.write_bytes(content)
            saved_paths.append(str(target))

    initial_run = create_run_record(instruction=instruction, file_paths=saved_paths, lang=lang)
    thread = threading.Thread(
        target=_execute_run_job,
        kwargs={
            "run_id": initial_run["run_id"],
            "created_at": initial_run["created_at"],
            "instruction": instruction,
            "file_paths": saved_paths,
            "lang": lang,
        },
        daemon=True,
        name=f"memoforge-run-{initial_run['run_id']}",
    )
    thread.start()
    return JSONResponse(initial_run, status_code=202)


@app.get("/api/runs/{run_id}/chat")
def api_run_chat(run_id: str) -> dict[str, Any]:
    run = load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    ready = _run_chat_ready(run) and bool(ensure_run_chat_index(run))
    messages = load_run_chat_thread(run_id) if ready else []
    return _chat_payload(run, messages, ready=ready)


@app.delete("/api/runs/{run_id}/chat")
def api_run_chat_clear(run_id: str) -> dict[str, Any]:
    run = load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    clear_run_chat_thread(run_id)
    ready = _run_chat_ready(run) and bool(ensure_run_chat_index(run))
    return _chat_payload(run, [], ready=ready)


@app.post("/api/runs/{run_id}/chat")
async def api_run_chat_message(run_id: str, request: Request) -> dict[str, Any]:
    run = load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if not _run_chat_ready(run):
        raise HTTPException(status_code=409, detail="run is not ready for chat")

    chat_index = ensure_run_chat_index(run)
    if not chat_index:
        raise HTTPException(status_code=409, detail="chat index is not available")

    payload = await request.json()
    message = str(payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    mode = str(payload.get("mode") or "ask").strip().lower()
    lang = str(payload.get("lang") or run.get("lang") or "ja").strip().lower()
    messages = load_run_chat_thread(run_id)
    user_turn = {
        "id": f"user-{uuid.uuid4().hex[:8]}",
        "role": "user",
        "content": message,
        "mode": "discuss" if mode == "discuss" else "ask",
        "created_at": now_iso(),
    }
    assistant_turn = await asyncio.to_thread(
        answer_run_question,
        run,
        message=message,
        mode=mode,
        lang=lang,
        thread=messages,
    )

    updated_messages = [*messages, user_turn, assistant_turn]
    save_run_chat_thread(run_id, updated_messages)
    return _chat_payload(run, updated_messages, ready=True)


# ---- Minimal OpenAI-compatible API for Open WebUI ----
@app.get("/v1/models")
def v1_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": "memoforge",
                "object": "model",
                "owned_by": "local",
            },
            {
                "id": "memoforge-vision",
                "object": "model",
                "owned_by": "local",
            },
        ],
    }


@app.post("/v1/chat/completions")
async def v1_chat_completions(request: Request) -> dict[str, Any]:
    payload = await request.json()
    messages = payload.get("messages", [])
    instruction = "\n".join(
        msg.get("content", "")
        if isinstance(msg.get("content"), str)
        else json.dumps(msg.get("content") or "", ensure_ascii=False)
        for msg in messages
        if msg.get("role") == "user"
    ).strip()
    if not instruction:
        instruction = "保存済み研究メモを整理し、関連ノートも踏まえて応答してください。"

    result = await asyncio.to_thread(run_workflow, instruction=instruction, file_paths=[])
    content = result.get("final_markdown", "").strip()
    if not content:
        content = "出力が生成されませんでした。"

    return {
        "id": f"chatcmpl-{result['run_id']}",
        "object": "chat.completion",
        "created": 0,
        "model": payload.get("model", "memoforge"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "memoforge": {
            "run_id": result["run_id"],
            "note_path": result.get("note_path"),
        },
    }
