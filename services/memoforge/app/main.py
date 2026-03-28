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

from .config import settings
from .graph import create_run_record, run_workflow
from .storage import list_runs, load_run

app = FastAPI(title="MemoForge", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _execute_run_job(run_id: str, created_at: str, instruction: str, file_paths: list[str]) -> None:
    try:
        run_workflow(
            instruction=instruction,
            file_paths=file_paths,
            run_id=run_id,
            created_at=created_at,
        )
    except Exception:
        # The failure state is already persisted by run_workflow.
        return


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

    initial_run = create_run_record(instruction=instruction, file_paths=saved_paths)
    thread = threading.Thread(
        target=_execute_run_job,
        kwargs={
            "run_id": initial_run["run_id"],
            "created_at": initial_run["created_at"],
            "instruction": instruction,
            "file_paths": saved_paths,
        },
        daemon=True,
        name=f"memoforge-run-{initial_run['run_id']}",
    )
    thread.start()
    return JSONResponse(initial_run, status_code=202)


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
    content = (
        "研究メモを保存しました。\n\n"
        f"保存先: {result.get('note_path')}\n\n"
        f"---\n\n{result.get('final_markdown', '')}"
    )

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
    }
