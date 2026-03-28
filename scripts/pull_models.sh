#!/usr/bin/env bash
set -euo pipefail

REASONING_MODEL="${REASONING_MODEL:-qwen3:30b}"
VISION_MODEL="${VISION_MODEL:-gemma3:27b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-embeddinggemma}"

echo "Pulling ${REASONING_MODEL} ..."
docker compose exec ollama ollama pull "${REASONING_MODEL}"

echo "Pulling ${VISION_MODEL} ..."
docker compose exec ollama ollama pull "${VISION_MODEL}"

echo "Pulling ${EMBEDDING_MODEL} ..."
docker compose exec ollama ollama pull "${EMBEDDING_MODEL}" || true

echo "Done."
