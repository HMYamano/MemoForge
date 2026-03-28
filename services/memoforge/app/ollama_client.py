from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from .config import settings


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(f"{self.base_url}{path}", json=payload, timeout=600)
        if not resp.ok:
            raise OllamaError(f"Ollama request failed: {resp.status_code} {resp.text}")
        return resp.json()

    def chat(self, model: str, messages: list[dict[str, Any]], format_json: bool = False) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"
        data = self._post("/api/chat", payload)
        return data["message"]["content"]

    def generate(self, model: str, prompt: str) -> str:
        data = self._post(
            "/api/generate",
            {"model": model, "prompt": prompt, "stream": False},
        )
        return data["response"]

    def embed(self, model: str, input_texts: list[str]) -> list[list[float]]:
        data = self._post(
            "/api/embed",
            {"model": model, "input": input_texts},
        )
        return data["embeddings"]

    def list_models(self) -> list[dict[str, Any]]:
        resp = requests.get(f"{self.base_url}/api/tags", timeout=30)
        if not resp.ok:
            raise OllamaError(f"Ollama tags failed: {resp.status_code} {resp.text}")
        return resp.json().get("models", [])


def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")
