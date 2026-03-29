from __future__ import annotations

from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader

from .config import settings
from .ollama_client import OllamaClient, image_to_base64

TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".json", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXTENSIONS = {".pdf"}


def summarize_image_with_gemma(image_path: Path, prompt: str) -> str:
    client = OllamaClient()
    return client.chat(
        settings.vision_model,
        [
            {
                "role": "user",
                "content": prompt,
                "images": [image_to_base64(image_path)],
            }
        ],
    )


_IMAGE_PROMPT: dict[str, str] = {
    "ja": (
        "あなたは研究メモ整理補助です。画像の内容を日本語で簡潔に要約し、"
        "図・顕微鏡画像・グラフ・注釈・読めるテキスト・重要そうな比較対象を箇条書きで整理してください。"
    ),
    "en": (
        "You are a research note assistant. Summarize the image content concisely in English. "
        "List figures, microscope images, graphs, annotations, readable text, and important comparisons as bullet points."
    ),
}

_PDF_PROMPT: dict[str, str] = {
    "ja": (
        "あなたは研究メモ整理補助です。PDF の各ページ画像を見て、"
        "図・表・模式図・軸ラベル・キャプションっぽい要素・重要な比較を日本語で短く整理してください。"
        "読み取れない部分は無理に推測しないでください。"
    ),
    "en": (
        "You are a research note assistant. For each PDF page image, briefly summarize in English: "
        "figures, tables, diagrams, axis labels, caption-like elements, and important comparisons. "
        "Do not guess what cannot be clearly read."
    ),
}


def extract_document(file_path: Path, lang: str = "ja") -> dict[str, Any]:
    suffix = file_path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return {
            "type": "text",
            "path": str(file_path),
            "name": file_path.name,
            "text": file_path.read_text(encoding="utf-8", errors="ignore"),
            "vision_notes": [],
            "rendered_pages": [],
        }
    if suffix in IMAGE_EXTENSIONS:
        img = Image.open(file_path)
        img.verify()
        vision = summarize_image_with_gemma(
            file_path,
            _IMAGE_PROMPT.get(lang, _IMAGE_PROMPT["ja"]),
        )
        return {
            "type": "image",
            "path": str(file_path),
            "name": file_path.name,
            "text": "",
            "vision_notes": [vision],
            "rendered_pages": [str(file_path)],
        }
    if suffix in PDF_EXTENSIONS:
        return extract_pdf(file_path, lang=lang)
    return {
        "type": "unknown",
        "path": str(file_path),
        "name": file_path.name,
        "text": "",
        "vision_notes": [],
        "rendered_pages": [],
    }


def extract_pdf(file_path: Path, lang: str = "ja") -> dict[str, Any]:
    page_texts: list[str] = []
    rendered_pages: list[str] = []
    vision_notes: list[str] = []

    reader = PdfReader(str(file_path))
    pdf = pdfium.PdfDocument(str(file_path))
    try:
        render_count = min(settings.pdf_vision_max_pages, len(pdf))
        render_dir = settings.rendered_pages_dir / file_path.stem
        render_dir.mkdir(parents=True, exist_ok=True)

        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            page_texts.append(f"## Page {idx + 1}\n{page_text}")
            if idx < render_count:
                page_png = render_dir / f"page_{idx + 1:03d}.png"
                bitmap = pdf[idx].render(scale=1.5)
                bitmap.to_pil().save(page_png)
                rendered_pages.append(str(page_png))
    finally:
        pdf.close()

    if rendered_pages:
        client = OllamaClient()
        prompt = _PDF_PROMPT.get(lang, _PDF_PROMPT["ja"])
        for page_png in rendered_pages:
            vision_notes.append(
                client.chat(
                    settings.vision_model,
                    [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_to_base64(Path(page_png))],
                        }
                    ],
                )
            )

    return {
        "type": "pdf",
        "path": str(file_path),
        "name": file_path.name,
        "text": "\n\n".join(page_texts),
        "vision_notes": vision_notes,
        "rendered_pages": rendered_pages,
    }
