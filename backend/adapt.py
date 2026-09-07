"""
Appel à l'API Anthropic pour générer une préparation d'entretien complète
à partir du CV utilisé pour postuler, du nom de l'entreprise, et de la
fiche de poste.

Règle stricte : toutes les réponses STAR doivent s'appuyer uniquement sur
des expériences réellement présentes dans le CV fourni. Ne jamais inventer
d'expérience, d'employeur, de chiffre ou de compétence.
"""
import json
import os

from anthropic import Anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

CLIENT = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """Tu es un coach de préparation à l'entretien d'embauche.

RÈGLES ABSOLUES (ne jamais les enfreindre) :
- Toutes les réponses STAR doivent s'appuyer UNIQUEMENT sur des expériences,
  employeurs, dates ou chiffres réellement présents dans le CV fourni.
- N'invente JAMAIS une expérience, un résultat chiffré ou une compétence
  absente du CV.
- Si une information manque pour répondre pleinement à une question,
  reste général plutôt que d'inventer.
- Le contenu doit être en français, sauf si la fiche de poste est
  rédigée en anglais (dans ce cas, ajoute aussi une version anglaise
  des réponses clés).

TÂCHE :
On te donne (1) le texte brut extrait d'un CV, (2) le nom de l'entreprise,
et (3) le texte de la fiche de poste. Tu dois produire une préparation
d'entretien complète et renvoyer UNIQUEMENT un objet JSON (aucun texte
avant/après, aucun bloc markdown) respectant exactement ce schéma :

{
  "entreprise": "string",
  "poste": "string (intitulé du poste tel que dans l'offre)",
  "analyse_offre": "string (5-8 lignes : compétences clés attendues, correspondances fortes avec le profil, écarts éventuels)",
  "pitch": "string (présentation personnelle de 60-90 secondes à l'oral, basée sur le CV)",
  "questions_star": [
    {
      "question": "string (question probable en entretien)",
      "reponse": "string (réponse STAR complète, 100-150 mots, prête à dire à l'oral, ancrée dans une expérience réelle du CV)"
    }
  ],
  "cadrage_ecarts": [
    {
      "ecart": "string (compétence ou point demandé par l'offre mais absent/faible dans le CV)",
      "reponse": "string (cadrage positif court, une phrase + une preuve, sans sur-justification)"
    }
  ],
  "questions_recruteur": ["string - question à poser au recruteur", "..."]
}

Pour "questions_star", génère 8 à 10 questions couvrant : présentation/pitch
(pas de style STAR, c'est déjà couvert par le champ "pitch"), motivation pour
ce poste et cette entreprise, pourquoi ce candidat, une réussite concrète,
une difficulté ou un échec géré, le travail en équipe ou un utilisateur/client
difficile, la projection à 5 ans, et les prétentions salariales/disponibilité.

Pour "cadrage_ecarts", identifie 2 à 4 écarts réels entre l'offre et le CV.
Si aucun écart notable, renvoie un tableau vide.

Pour "questions_recruteur", génère 5 à 7 questions pertinentes sur
l'organisation de l'équipe, l'environnement technique, la projection
d'évolution, et les prochaines étapes du recrutement. Évite les questions
dont la réponse est déjà dans l'offre."""


class AdaptationError(Exception):
    pass


def generate_prep(cv_text: str, entreprise: str, offre_text: str) -> dict:
    message = CLIENT.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"--- TEXTE BRUT DU CV ---\n{cv_text}\n\n"
                    f"--- ENTREPRISE ---\n{entreprise}\n\n"
                    f"--- FICHE DE POSTE ---\n{offre_text}\n\n"
                    "Renvoie uniquement le JSON demandé."
                ),
            }
        ],
    )

    raw = "".join(block.text for block in message.content if block.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdaptationError(f"Réponse IA invalide (non-JSON) : {exc}") from exc

    return data
