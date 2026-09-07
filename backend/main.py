"""
API de préparation d'entretien publique — entretien.komjordan.fr

Principe : zéro conservation. Le CV, le nom de l'entreprise et la fiche
de poste sont traités en mémoire pour la durée de la requête, envoyés à
l'API Anthropic pour générer la préparation, transformés en document
Word, puis tout est jeté. Rien n'est écrit sur disque de façon
persistante, aucune base de données.
"""
import logging
import re

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from adapt import AdaptationError, generate_prep
from extract import ExtractionError, extract_text
from ratelimit import RateLimitExceeded, check_and_record
from render import render_docx, render_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("entretien-generator")

app = FastAPI(title="Préparateur d'entretien")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://entretien.komjordan.fr", "https://komjordan.fr"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

MAX_OFFER_LEN = 8000
MAX_ENTREPRISE_LEN = 200


def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-]", "_", name.strip())
    return name[:60] or "Entreprise"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate")
async def generate(
    request: Request,
    cv: UploadFile = File(...),
    entreprise: str = Form(...),
    offre: str = Form(...),
    format: str = Form("docx"),
):
    client_ip = request.client.host if request.client else "unknown"

    format = format.strip().lower()
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Format invalide (docx ou pdf attendu).")

    try:
        check_and_record(client_ip)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    entreprise = entreprise.strip()
    offre = offre.strip()

    if not entreprise:
        raise HTTPException(status_code=400, detail="Le nom de l'entreprise est requis.")
    if len(entreprise) > MAX_ENTREPRISE_LEN:
        raise HTTPException(status_code=400, detail="Nom d'entreprise trop long.")
    if not offre:
        raise HTTPException(status_code=400, detail="La fiche de poste est vide.")
    if len(offre) > MAX_OFFER_LEN:
        raise HTTPException(status_code=400, detail="Fiche de poste trop longue (8000 caractères max).")

    cv_bytes = await cv.read()

    try:
        cv_text = extract_text(cv_bytes, cv.content_type)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        del cv_bytes

    try:
        data = generate_prep(cv_text, entreprise, offre)
    except AdaptationError as exc:
        logger.error("Génération échouée: %s", exc)
        raise HTTPException(
            status_code=502, detail="Erreur lors de la génération du contenu. Réessaie."
        ) from exc
    finally:
        del cv_text

    try:
        if format == "pdf":
            file_bytes = render_pdf(data)
            media_type = "application/pdf"
            ext = "pdf"
        else:
            file_bytes = render_docx(data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Rendu %s échoué: %s", format, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du document.") from exc
    finally:
        del data

    filename = f"Preparation_Entretien_{safe_filename(entreprise)}.{ext}"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
