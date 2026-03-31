from __future__ import annotations

import asyncio
import json
import re
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .chat_tools import answer_run_question, ensure_run_chat_index
from .config import settings
from .graph import create_run_record, run_workflow
from .storage import (
    clear_run_chat_thread,
    delete_note,
    list_notes,
    list_runs,
    load_note,
    load_run,
    load_run_chat_thread,
    now_iso,
    save_run_chat_thread,
    update_note_body,
)
from .watcher import start_watcher, stop_watcher, watcher_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_watcher()
    yield
    stop_watcher()


app = FastAPI(title="MemoForge", version="1.1.0", lifespan=lifespan)
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
            if len(content) > settings.max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{original_name}: file exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit",
                )
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


# ---- Notes library API -------------------------------------------------------

@app.get("/api/notes")
def api_notes(tag: str | None = None) -> list[dict[str, Any]]:
    return list_notes(tag=tag)


@app.get("/api/notes/{filename:path}")
def api_note(filename: str) -> dict[str, Any]:
    note = load_note(filename)
    if not note:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@app.put("/api/notes/{filename:path}")
async def api_note_update(filename: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    new_body = str(payload.get("body") or "").strip()
    if not new_body:
        raise HTTPException(status_code=400, detail="body is required")
    if not update_note_body(filename, new_body):
        raise HTTPException(status_code=404, detail="note not found")
    note = load_note(filename)
    return note  # type: ignore[return-value]


@app.delete("/api/notes/{filename:path}")
def api_note_delete(filename: str) -> dict[str, str]:
    if not delete_note(filename):
        raise HTTPException(status_code=404, detail="note not found")
    return {"deleted": filename}


# ---- Note export -------------------------------------------------------------

def _markdown_to_html(markdown: str, title: str) -> str:
    """Minimal Markdown → standalone HTML conversion (no external deps)."""
    def escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def inline(line: str) -> str:
        line = escape(line)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", line)
        return line

    lines = markdown.replace("\r\n", "\n").split("\n")
    html: list[str] = []
    in_code = False
    code_buf: list[str] = []
    in_list: str | None = None

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            html.append(f"</{in_list}>")
            in_list = None

    for line in lines:
        if in_code:
            if line.strip().startswith("```"):
                html.append(f"<pre><code>{escape(chr(10).join(code_buf))}</code></pre>")
                in_code = False
                code_buf = []
            else:
                code_buf.append(line)
            continue
        if line.strip().startswith("```"):
            flush_list()
            in_code = True
            continue
        if not line.strip():
            flush_list()
            html.append("<br>")
            continue
        if re.match(r"^#{1,6}\s", line):
            flush_list()
            level = len(re.match(r"^(#+)", line).group(1))
            content = line.lstrip("#").strip()
            html.append(f"<h{level}>{inline(content)}</h{level}>")
        elif re.match(r"^[-*]\s", line):
            if in_list != "ul":
                flush_list()
                html.append("<ul>")
                in_list = "ul"
            html.append(f"<li>{inline(line[2:])}</li>")
        elif re.match(r"^\d+\.\s", line):
            if in_list != "ol":
                flush_list()
                html.append("<ol>")
                in_list = "ol"
            html.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', line))}</li>")
        else:
            flush_list()
            html.append(f"<p>{inline(line)}</p>")

    flush_list()
    body_html = "\n".join(html)
    return (
        f"<!doctype html><html lang='ja'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title>"
        f"<style>body{{font-family:sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;line-height:1.7}}"
        f"pre{{background:#f4f4f4;padding:1rem;overflow:auto}}code{{font-size:.9em}}"
        f"table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.4rem .6rem}}</style>"
        f"</head><body>{body_html}</body></html>"
    )


def _markdown_to_obsidian(note: dict[str, Any]) -> str:
    """Return Obsidian-compatible Markdown (with #tag syntax appended)."""
    tags = note.get("tags", [])
    body = note.get("body", "")
    if not tags:
        return body
    tag_line = "  ".join(f"#{t}" for t in tags)
    return f"{body}\n\n{tag_line}\n"


@app.get("/api/notes/{filename:path}/export")
def api_note_export(filename: str, fmt: str = "md") -> Any:
    note = load_note(filename)
    if not note:
        raise HTTPException(status_code=404, detail="note not found")

    fmt = fmt.lower()
    stem = Path(filename).stem

    if fmt == "html":
        content = _markdown_to_html(note["body"], note["title"])
        return StreamingResponse(
            iter([content]),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{stem}.html"'},
        )

    if fmt == "obsidian":
        content = _markdown_to_obsidian(note)
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
        )

    # Default: plain Markdown
    return StreamingResponse(
        iter([note["raw"]]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
    )


# ---- Watcher status ----------------------------------------------------------

@app.get("/api/watcher")
def api_watcher_status() -> dict[str, Any]:
    return watcher_status()


# ---- Run SSE stream ----------------------------------------------------------

@app.get("/api/runs/{run_id}/stream")
async def api_run_stream(run_id: str, request: Request) -> StreamingResponse:
    async def event_generator():
        while True:
            if await request.is_disconnected():
                return
            run = load_run(run_id)
            if not run:
                yield f"event: error\ndata: {json.dumps({'detail': 'run not found'})}\n\n"
                return
            yield f"data: {json.dumps(run, ensure_ascii=False)}\n\n"
            status = run.get("status", "")
            if status in ("completed", "failed"):
                yield "event: done\ndata: {}\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
async def v1_chat_completions(request: Request) -> Any:
    payload = await request.json()
    messages = payload.get("messages", [])
    stream: bool = bool(payload.get("stream", False))
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

    completion_id = f"chatcmpl-{result['run_id']}"
    model_name = payload.get("model", "memoforge")

    if stream:
        async def stream_generator():
            # Send content as a single SSE chunk then a [DONE] sentinel.
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            done_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": 0,
        "model": model_name,
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
