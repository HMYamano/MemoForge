# MemoForge

[日本語版はこちら](./README.ja.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/HMYamano/MemoForge)](../../releases)
[![CI](https://github.com/HMYamano/MemoForge/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

MemoForge is a fully local research-note organization system. It turns PDFs, images, Markdown files, and plain text into reusable Markdown research notes — with automatic tagging, a note library, and real-time progress streaming.

- UI 1: Open WebUI (`http://localhost:3000`)
- UI 2: MemoForge Dashboard (`http://localhost:8001`)
- LLM runtime: Ollama
- Default reasoning model: `qwen3:30b`
- Default vision model: `gemma3:27b`

## Features

- Organize research notes entirely on your local machine
- Combine PDF text extraction with page-image-based visual interpretation
- Reuse existing notes in `notes/` through BM25-based local retrieval
- **Automatic tag extraction** — LLM-generated tags written as YAML frontmatter in every note
- **Note Library UI** — browse, filter by tag, edit, delete, and export notes from the dashboard
- **Export formats** — Markdown, standalone HTML, and Obsidian-compatible Markdown
- **Real-time progress** — SSE-based streaming replaces polling for instant status updates
- **Incoming directory watcher** — drop a file into `incoming/` and a run is created automatically
- Connect from Open WebUI as an OpenAI-compatible provider (streaming supported)
- Save outputs as editable Markdown

## Architecture

- `ollama`: local LLM / VLM runtime
- `open-webui`: chat UI and model interaction
- `memoforge`: FastAPI + LangGraph workflow for research memo organization

## Quick Start

### 1. Requirements

- Docker / Docker Compose
- Enough disk space for Ollama models
- Sufficient GPU / RAM if you use larger models

### 1.1 Recommended PC Requirements

These are practical recommendations for local use. Actual requirements depend on model quantization, document size, and how many apps are running at the same time.

Default profile: `qwen3:30b` + `gemma3:27b`

- OS: Windows 11, macOS, or Linux with Docker support
- CPU: 8 cores or more recommended
- System RAM: 64 GB or more recommended
- GPU: 24 GB or more VRAM recommended
- Free storage: 120 GB or more recommended for Docker data and Ollama models

Lighter profile: `qwen3:14b` + `gemma3:12b`

- System RAM: 32 GB or more recommended
- GPU: 12 GB to 16 GB or more VRAM recommended
- Free storage: 60 GB or more recommended

CPU-only operation is possible for experimentation with smaller models, but it is not recommended for the default profile because response times can become very slow.

### 2. Optionally create `.env`

```bash
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Start the containers

```bash
docker compose up -d --build
```

### 4. Pull the models

macOS / Linux / Git Bash:

```bash
./scripts/pull_models.sh
```

PowerShell:

```powershell
./scripts/pull_models.ps1
```

### 5. Open the UIs

- MemoForge Dashboard: `http://localhost:8001`
- Open WebUI: `http://localhost:3000`

## Start and Stop After Installation

### Start

If you have already completed the initial setup and pulled the required models, daily startup is:

```bash
docker compose up -d
```

Then open:

- MemoForge Dashboard: `http://localhost:8001`
- Open WebUI: `http://localhost:3000`

If you changed model settings in `.env`, run the same command again after saving the file so the containers pick up the new environment values.

### Stop

To stop the running containers while keeping local data such as notes, Ollama models, and Open WebUI state:

```bash
docker compose stop
```

To stop and remove the containers:

```bash
docker compose down
```

Both commands keep your local bind-mounted data directories. `down` removes the containers, while `stop` only stops them.

## Usage

### MemoForge Dashboard

1. Open `http://localhost:8001`
2. Enter an instruction
3. Attach PDFs, PNGs, JPGs, Markdown files, text files, and similar inputs
4. Run the workflow — progress updates in real time via SSE
5. Find the generated Markdown note (with auto-extracted tags) in `notes/`
6. Browse, edit, and export all notes from the **Library** tab

### Note Library

Click the **Library** tab in the inspector panel to:

- Browse all generated notes with titles and tag chips
- Filter notes by tag using the tag cloud or the text input
- Open a note to preview its full content
- Edit the note body in the browser and save it back to disk
- Export as **Markdown**, **standalone HTML**, or **Obsidian-compatible Markdown**
- Delete notes you no longer need

### Incoming Directory Watcher

Set `WATCHER_ENABLED=true` in `.env` to automatically process files dropped into the `incoming/` directory.
Any supported file (PDF, image, Markdown, plain text) placed there will trigger a new run without opening the dashboard.

```env
WATCHER_ENABLED=true
WATCHER_LANG=en   # ja or en
```

Check the watcher status at `GET /api/watcher`.

### From Open WebUI

- You can use Ollama models directly for regular chat
- You can also add `memoforge` as an OpenAI-compatible provider
- API URL: `http://memoforge:8001/v1` from inside Docker
- If Open WebUI runs elsewhere: `http://host.docker.internal:8001/v1`
- API Key: leave empty
- Streaming (`stream: true`) is fully supported

## Model Configuration

The defaults favor quality. If you need a lighter setup, override them in `.env`.

```env
REASONING_MODEL=qwen3:14b
VISION_MODEL=gemma3:12b
EMBEDDING_MODEL=embeddinggemma
```

### How to Change Models

1. Copy `.env.example` to `.env` if you have not created it yet.
2. Edit the model names in `.env`.

```env
REASONING_MODEL=qwen3:14b
VISION_MODEL=gemma3:12b
EMBEDDING_MODEL=embeddinggemma
```

3. Pull the models you want to use.

macOS / Linux / Git Bash:

```bash
./scripts/pull_models.sh
```

PowerShell:

```powershell
./scripts/pull_models.ps1
```

4. Restart or recreate the containers so the new environment variables are applied.

```bash
docker compose up -d
```

The current model settings are shown in the dashboard header. In this project, `REASONING_MODEL` is used for memo generation, review, and tag extraction; `VISION_MODEL` is used for image and PDF-page interpretation; and `EMBEDDING_MODEL` is reserved for future retrieval features.

## Advanced Configuration

All options can be set in `.env` (see `.env.example` for the full list).

| Variable | Default | Description |
|---|---|---|
| `REASONING_MODEL` | `qwen3:30b` | LLM for text generation, review, and tag extraction |
| `VISION_MODEL` | `gemma3:27b` | VLM for image and PDF page interpretation |
| `EMBEDDING_MODEL` | `embeddinggemma` | Reserved for vector retrieval |
| `OLLAMA_TIMEOUT` | `600` | Ollama request timeout in seconds |
| `MAX_UPLOAD_BYTES` | `104857600` | Maximum upload file size (100 MB) |
| `MAX_RELATED_NOTES` | `5` | Top-k related notes retrieved per run |
| `PDF_VISION_MAX_PAGES` | `4` | Maximum PDF pages rendered for vision processing |
| `WATCHER_ENABLED` | `false` | Enable incoming directory watcher |
| `WATCHER_LANG` | `ja` | Language used for auto-created watcher runs |
| `APP_DATA_DIR` | `/app/data` | Run data directory (Docker default) |
| `NOTES_DIR` | `/app/notes` | Notes output directory (Docker default) |
| `INCOMING_DIR` | `/app/incoming` | Watched incoming directory (Docker default) |

For local execution without Docker, override the path variables to relative paths, e.g.:

```env
APP_DATA_DIR=./data
NOTES_DIR=./notes
INCOMING_DIR=./incoming
```

## API Reference (key endpoints)

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard HTML |
| `POST` | `/api/runs` | Create a new run |
| `GET` | `/api/runs/{id}` | Get run details |
| `GET` | `/api/runs/{id}/stream` | SSE stream of run progress |
| `POST` | `/api/runs/{id}/chat` | Send a follow-up chat message |
| `GET` | `/api/notes` | List all notes (optional `?tag=` filter) |
| `GET` | `/api/notes/{filename}` | Get note with parsed frontmatter |
| `PUT` | `/api/notes/{filename}` | Update note body |
| `DELETE` | `/api/notes/{filename}` | Delete a note |
| `GET` | `/api/notes/{filename}/export?fmt=md\|html\|obsidian` | Export note |
| `GET` | `/api/watcher` | Watcher status |
| `GET` | `/v1/models` | OpenAI-compatible model list |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat (streaming supported) |

## Implementation Notes

- Related-note retrieval uses a cached BM25 index rebuilt only when notes change
- PDF text extraction uses `pypdf`, and PDF page rendering uses `pypdfium2`
- Visual information from images and PDF pages is summarized by a vision model
- Tags are extracted by the LLM at the end of each run and stored as YAML frontmatter
- Run progress is pushed to the browser via Server-Sent Events (SSE)
- The `incoming/` watcher uses `watchdog` and is disabled by default

## Repository Data

The following are runtime-generated and are intentionally not meant to be committed:

- `data/`
- `notes/`
- `incoming/`
- `__pycache__/`

These directories contain only placeholders in the repository. Real data is created locally at runtime.

## Security and Deployment Notes

- This project is intended for local use
- The MemoForge API is designed for use on your machine or within a local network
- It is not intended to be exposed directly to the public internet
- If you handle sensitive documents, also review your model sourcing and Open WebUI settings

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before submitting a pull request.

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for release history.

## License

The source code in this repository is licensed under the `MIT License`. Commercial use, modification, and redistribution are allowed.

However, external components and models used alongside this project have their own licenses or terms. In particular, please review the upstream terms for:

- Ollama: MIT
- Open WebUI: current releases include branding-related license terms
- Qwen3: Apache-2.0
- Gemma / EmbeddingGemma: Gemma Terms of Use

The MIT license for this repository does not override the licenses or terms of those external components.
