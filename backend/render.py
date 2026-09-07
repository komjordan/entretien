"""
Génère le document Word de préparation d'entretien à partir du JSON
produit par l'IA. Tout se passe en mémoire, rien n'est écrit sur disque
de façon persistante.
"""
import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Inches

NAVY = RGBColor(0x1F, 0x29, 0x37)
ACCENT = RGBColor(0x21, 0x63, 0xEB)
GRAY = RGBColor(0x6B, 0x72, 0x80)


def _heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = NAVY
    return h


def _add_qa(doc, question, reponse):
    p = doc.add_paragraph()
    run = p.add_run(question)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = ACCENT

    p2 = doc.add_paragraph(reponse)
    p2.paragraph_format.space_after = Pt(10)


def render_docx(data: dict) -> bytes:
    doc = Document()

    # Style de base
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    # Titre
    title = doc.add_heading(f"Préparation d'entretien — {data.get('entreprise', '')}", level=0)
    for run in title.runs:
        run.font.color.rgb = NAVY

    sous_titre = doc.add_paragraph(data.get("poste", ""))
    sous_titre.runs[0].font.size = Pt(13)
    sous_titre.runs[0].font.color.rgb = GRAY
    sous_titre.alignment = WD_ALIGN_PARAGRAPH.LEFT

    doc.add_paragraph()

    # Analyse de l'offre
    _heading(doc, "Analyse de l'offre", level=1)
    doc.add_paragraph(data.get("analyse_offre", ""))

    # Pitch
    _heading(doc, "Votre présentation (pitch 60-90s)", level=1)
    doc.add_paragraph(data.get("pitch", ""))

    # Questions STAR
    _heading(doc, "Questions probables et réponses STAR", level=1)
    for qa in data.get("questions_star", []):
        _add_qa(doc, qa.get("question", ""), qa.get("reponse", ""))

    # Cadrage des écarts
    ecarts = data.get("cadrage_ecarts", [])
    if ecarts:
        _heading(doc, "Cadrage des points faibles", level=1)
        for e in ecarts:
            p = doc.add_paragraph()
            run = p.add_run(e.get("ecart", ""))
            run.bold = True
            run.font.color.rgb = ACCENT
            doc.add_paragraph(e.get("reponse", ""))

    # Questions à poser au recruteur
    _heading(doc, "Questions à poser au recruteur", level=1)
    for q in data.get("questions_recruteur", []):
        doc.add_paragraph(q, style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
