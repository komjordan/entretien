"""
Extraction du texte brut d'un CV uploadé (PDF ou DOCX).
Tout se fait en mémoire, rien n'est écrit sur disque.
"""
import io

import pdfplumber
from docx import Document

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo


class ExtractionError(Exception):
    pass


def extract_text(file_bytes: bytes, content_type: str) -> str:
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ExtractionError("Fichier trop volumineux (5 Mo max).")

    kind = ALLOWED_TYPES.get(content_type)
    if kind is None:
        raise ExtractionError("Format non supporté. Utilisez un PDF ou un DOCX.")

    if kind == "pdf":
        return _extract_pdf(file_bytes)
    return _extract_docx(file_bytes)


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    text = "\n".join(text_parts).strip()
    if not text:
        raise ExtractionError(
            "Impossible d'extraire le texte du PDF (probablement un scan/image)."
        )
    return text


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text.strip())
    text = "\n".join(parts).strip()
    if not text:
        raise ExtractionError("Le document DOCX semble vide.")
    return text
