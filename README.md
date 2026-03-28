# MemoForge

[日本語版はこちら](./README.ja.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/HMYamano/MemoForge)](../../releases)
[![CI](https://github.com/HMYamano/MemoForge/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

MemoForge is a fully local research-note organization system. It turns PDFs, images, Markdown files, and plain text into reusable Markdown research notes.

- UI 1: Open WebUI (`http://localhost:3000`)
- UI 2: MemoForge Dashboard (`http://localhost:8001`)
- LLM runtime: Ollama
- Default reasoning model: `qwen3:30b`
- Default vision model: `gemma3:27b`

## Features

- Organize research notes entirely on your local machine
- Combine PDF text extraction with page-image-based visual interpretation
- Reuse existing notes in `notes/` through BM25-based local retrieval
- Connect from Open WebUI as an OpenAI-compatible provider
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
4. Run the workflow
5. Find the generated Markdown note in `notes/`

### From Open WebUI

- You can use Ollama models directly for regular chat
- You can also add `memoforge` as an OpenAI-compatible provider
- API URL: `http://memoforge:8001/v1` from inside Docker
- If Open WebUI runs elsewhere: `http://host.docker.internal:8001/v1`
- API Key: leave empty

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

The current model settings are shown in the dashboard header. In this project, `REASONING_MODEL` is used for memo generation and review, `VISION_MODEL` is used for image and PDF-page interpretation, and `EMBEDDING_MODEL` is reserved for local retrieval-related features.

## Implementation Notes

- Related-note retrieval is BM25-based over local Markdown files
- PDF text extraction uses `pypdf`, and PDF page rendering uses `pypdfium2`
- Visual information from images and PDF pages is summarized by a vision model
- The structure is intentionally simple so it can later be replaced with vector DBs or other document pipelines

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
