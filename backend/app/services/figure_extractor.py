import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from backend.app.core.paths import figures_dir

CAPTION_RE = re.compile(r"^\s*((Figure|Fig\.|Table)\s+\d+[:.\s].{5,})$", re.IGNORECASE)
CAPTION_LABEL_RE = re.compile(r"^\s*((Figure|Fig\.|Table)\s+\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedFigure:
    image_path: Path
    caption: str | None
    page: int
    order: int
    label: str | None


def find_captions(page_text: str) -> list[str]:
    captions: list[str] = []
    for line in page_text.splitlines():
        match = CAPTION_RE.match(line.strip())
        if match:
            captions.append(" ".join(match.group(1).split()))
    return captions


def caption_label(caption: str | None) -> str | None:
    if not caption:
        return None
    match = CAPTION_LABEL_RE.match(caption)
    return match.group(1) if match else None


def extract_pdf_figures(document_id: str, pdf_path: Path) -> list[ExtractedFigure]:
    doc = fitz.open(pdf_path)
    output_dir = figures_dir(document_id)
    extracted: list[ExtractedFigure] = []
    for page_index, page in enumerate(doc, start=1):
        captions = find_captions(page.get_text("text"))
        images = page.get_images(full=True)
        for image_index, image in enumerate(images, start=1):
            xref = image[0]
            data = doc.extract_image(xref)
            extension = data.get("ext", "png")
            image_path = output_dir / f"page-{page_index:03d}-image-{image_index:02d}.{extension}"
            image_path.write_bytes(data["image"])
            caption = captions[min(image_index - 1, len(captions) - 1)] if captions else None
            extracted.append(
                ExtractedFigure(
                    image_path=image_path,
                    caption=caption,
                    page=page_index,
                    order=len(extracted),
                    label=caption_label(caption),
                )
            )
    return extracted
