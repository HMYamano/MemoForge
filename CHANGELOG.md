# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-29

### Added
- Initial public release
- FastAPI + LangGraph workflow for research note generation
- Multi-format document ingestion: PDF, PNG, JPG, JPEG, WEBP, BMP, TIFF, Markdown, plain text
- PDF text extraction via `pypdf` and page rendering via `pypdfium2`
- Vision model integration for image and PDF page interpretation
- BM25-based local note retrieval for context reuse
- Intake → Extract → Retrieve → Structure → Review → Revise → Accept → Save workflow
- MemoForge Dashboard UI at `http://localhost:8001`
- Open WebUI integration at `http://localhost:3000`
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`)
- Docker Compose orchestration with Ollama, Open WebUI, and MemoForge services
- Model pull scripts for macOS/Linux (`pull_models.sh`) and Windows (`pull_models.ps1`)
- Pre-defined note templates: paper organization, comparison memo, experiment planning, review preparation
- Real-time progress tracking (0–100%) per run
- Run history with per-run detail view
- Configurable models via `.env` (reasoning, vision, embedding)
- English and Japanese documentation
