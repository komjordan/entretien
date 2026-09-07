"""
Génère le document de préparation d'entretien (Word ou PDF) à partir du
JSON produit par l'IA. Tout se passe en mémoire, rien n'est écrit sur
disque de façon persistante (sauf le fichier HTML/PDF temporaire pour
wkhtmltopdf, supprimé immédiatement après génération).
"""
import io
import subprocess
import tempfile
from html import escape
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

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


def _esc(text) -> str:
    return escape(str(text or ""), quote=False)


def _html_qa_block(qa_list):
    out = []
    for qa in qa_list:
        out.append(
            f'<div class="qa"><div class="q">{_esc(qa.get("question"))}</div>'
            f'<div class="r">{_esc(qa.get("reponse"))}</div></div>'
        )
    return "".join(out)


def _html_ecarts_block(ecarts):
    out = []
    for e in ecarts:
        out.append(
            f'<div class="qa"><div class="q">{_esc(e.get("ecart"))}</div>'
            f'<div class="r">{_esc(e.get("reponse"))}</div></div>'
        )
    return "".join(out)


PDF_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 18mm 16mm; size: A4; }}
  body {{ font-family: Helvetica, Arial, sans-serif; color: #1f2430; font-size: 10.5pt; line-height: 1.5; }}
  h1 {{ color: #1F2937; font-size: 18pt; margin: 0 0 2mm 0; }}
  .sous-titre {{ color: #6B7280; font-size: 12pt; margin-bottom: 8mm; }}
  h2 {{ color: #1F2937; font-size: 12pt; text-transform: uppercase; letter-spacing: 0.03em;
        border-bottom: 2px solid #2563EB; padding-bottom: 1.5mm; margin: 7mm 0 3mm 0; }}
  p {{ margin: 0 0 3mm 0; }}
  .qa {{ margin-bottom: 4mm; }}
  .qa .q {{ font-weight: bold; color: #2563EB; margin-bottom: 1mm; }}
  .qa .r {{ margin: 0; }}
  ul {{ margin: 0; padding-left: 5mm; }}
  li {{ margin-bottom: 1.5mm; }}
</style>
</head>
<body>
  <h1>Préparation d'entretien — {entreprise}</h1>
  <div class="sous-titre">{poste}</div>

  <h2>Analyse de l'offre</h2>
  <p>{analyse_offre}</p>

  <h2>Votre présentation (pitch 60-90s)</h2>
  <p>{pitch}</p>

  <h2>Questions probables et réponses STAR</h2>
  {questions_star}

  {ecarts_section}

  <h2>Questions à poser au recruteur</h2>
  <ul>{questions_recruteur}</ul>
</body>
</html>"""


def render_pdf(data: dict) -> bytes:
    ecarts = data.get("cadrage_ecarts", [])
    ecarts_html = ""
    if ecarts:
        ecarts_html = f'<h2>Cadrage des points faibles</h2>{_html_ecarts_block(ecarts)}'

    questions_recruteur_html = "".join(
        f"<li>{_esc(q)}</li>" for q in data.get("questions_recruteur", [])
    )

    html = PDF_TEMPLATE.format(
        entreprise=_esc(data.get("entreprise")),
        poste=_esc(data.get("poste")),
        analyse_offre=_esc(data.get("analyse_offre")),
        pitch=_esc(data.get("pitch")),
        questions_star=_html_qa_block(data.get("questions_star", [])),
        ecarts_section=ecarts_html,
        questions_recruteur=questions_recruteur_html,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        html_path = tmp / "prep.html"
        pdf_path = tmp / "prep.pdf"
        html_path.write_text(html, encoding="utf-8")

        subprocess.run(
            [
                "wkhtmltopdf",
                "--enable-local-file-access",
                "--page-size", "A4",
                "--dpi", "300",
                "--disable-smart-shrinking",
                str(html_path),
                str(pdf_path),
            ],
            check=True,
            capture_output=True,
        )
        return pdf_path.read_bytes()
