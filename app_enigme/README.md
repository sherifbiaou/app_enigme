# Énigme du jour

Une mini-appli d’apprentissage : chaque jour, une énigme courte à partir d’un article Wikipédia. Tu devines le terme caché, tu gagnes des points, tu découvres la source.

## Fonctionnement

1. Le serveur choisit un sujet dans un domaine (statistiques et data, économie, informatique et IA , histoire , etc...) et récupère l’extrait de la page web française.
2. Le modèle DeepSeek reçoit **uniquement** cet extrait et rédige une énigme au format JSON.
3. Garde-fou anti-invention : si le terme caché ne figure pas dans l’extrait, l’énigme est rejetée.
4. La réponse reste côté serveur jusqu’à ce que l’utilisateur réponde. Barème : 10 points, 5 avec l’indice.
5. Chaque énigme générée est gardée dans `puzzles.json` et sert de secours si l’API est indisponible.

| Fichier | Rôle |
|---|---|
| `main.py` | API FastAPI, appel Wikipédia et DeepSeek, validation des réponses |
| `index.html` | Interface (HTML, CSS et JavaScript, sans framework) |
| `.env.example` | Modèle de configuration |

## Installation

```bash
git clone https://github.com/sherifbiaou/app_enigme.git
cd app_enigme
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # puis colle ta clé dans .env
python main.py
```

Ouvre ensuite http://127.0.0.1:8000.

## Configuration

| Variable | Rôle |
|---|---|
| `DEEPSEEK_API_KEY` | Clé de l’API DeepSeek (compte rechargé sur platform.deepseek.com) |
| `DEEPSEEK_MODEL` | Nom du modèle. Vérifie-le dans la documentation DeepSeek, il a déjà changé en 2026 |

## API

| Route | Rôle |
|---|---|
| `GET /api/domaines` | Liste des domaines |
| `GET /api/enigme?domaine=...` | Nouvelle énigme (sans la réponse) |
| `POST /api/repondre` | Vérifie la réponse et renvoie solution, explication, source |
| `GET /api/pregenerer?n=8` | Remplit le cache de secours |

## Sécurité

- La clé API vit dans `.env` (ignoré par Git) et ne quitte jamais le serveur.
- **Ne pas déployer en public en l’état** : aucune authentification ni limitation de débit, donc n’importe qui pourrait consommer ton crédit API via `/api/enigme` et `/api/pregenerer`.

## Limites connues

- Les réponses sont validées par correspondance de texte (variantes fournies par le modèle), pas par compréhension.
- Les points et la série sont stockés dans le navigateur (`localStorage`).

## Feuille de route

- Notification quotidienne (canal Telegram), puis widget Android.
- Nouveaux domaines, comptes et classement.
- Validation sémantique des réponses.

## Licence

MIT
