# Préparateur d'entretien — entretien.komjordan.fr

Application publique : l'utilisateur upload le CV utilisé pour postuler,
indique l'entreprise et colle la fiche de poste. L'app renvoie un document
Word complet : analyse de l'offre, pitch, questions STAR, cadrage des
points faibles, questions à poser au recruteur. **Zéro conservation.**

## Architecture

Identique à `cv-generator`, hébergée sur le même VPS avec des ports différents :

| App | Backend (interne) | Frontend (interne) |
|---|---|---|
| cv.komjordan.fr | 127.0.0.1:8000 | 127.0.0.1:8080 |
| entretien.komjordan.fr | 127.0.0.1:8001 | 127.0.0.1:8081 |

## Étape 1 — DNS

Dans la zone DNS LWS de `komjordan.fr`, ajoute un enregistrement **A** :
- Nom : `entretien`
- Valeur : l'IP de ton VPS IONOS (la même que pour `cv`)

Vérifie la propagation avec `dig entretien.komjordan.fr +short`.

## Étape 2 — Cloner et configurer sur le VPS

```bash
cd ~
git clone https://github.com/komjordan/entretien.git
cd entretien
cp .env.example .env
```

Édite `.env` avec ta clé API Anthropic :

```bash
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-COLLE_TA_VRAIE_CLE_ICI
ANTHROPIC_MODEL=claude-sonnet-5
PER_IP_DAILY_MAX=3
GLOBAL_DAILY_MAX=50
EOF
```

## Étape 3 — Lancer les conteneurs

```bash
docker compose up -d --build
```

Vérifie :
```bash
curl http://127.0.0.1:8001/api/health
# {"status":"ok"}
```

## Étape 4 — Configurer Nginx

```bash
sudo cp nginx/entretien.komjordan.fr.conf /etc/nginx/sites-available/entretien.komjordan.fr
sudo ln -s /etc/nginx/sites-available/entretien.komjordan.fr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Étape 5 — HTTPS avec Certbot

```bash
sudo certbot --nginx -d entretien.komjordan.fr
```

## Étape 6 — Tester

Va sur `https://entretien.komjordan.fr`, uploade un CV test, renseigne une
entreprise et une fiche de poste, vérifie que le `.docx` se télécharge et
s'ouvre correctement.

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clé API Anthropic (obligatoire) | — |
| `ANTHROPIC_MODEL` | Modèle utilisé | `claude-sonnet-5` |
| `PER_IP_DAILY_MAX` | Générations max par IP / 24h | `3` |
| `GLOBAL_DAILY_MAX` | Générations max tous utilisateurs / 24h | `50` |

## Coûts

Même principe que `cv-generator` : chaque génération = 1 appel API
(le prompt est plus long ici — pitch + 8-10 questions STAR + cadrage +
questions recruteur — donc légèrement plus coûteux que le générateur de
CV, mais reste de l'ordre de quelques centimes par génération).

## Mettre à jour le code

```bash
cd ~/entretien
git pull
docker compose up -d --build
```

## Limites connues

- CV scannés (image) non supportés, comme pour `cv-generator`.
- Rate limiting en mémoire, remis à zéro au redémarrage du conteneur.
- Sortie uniquement en `.docx` pour l'instant (pas de PDF).
