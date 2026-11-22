"""Énigme du jour : FastAPI + DeepSeek + Wikipédia (rien d'inventé : l'IA ne voit que l'extrait Wikipédia)."""
import json, os, random, re, unicodedata, uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")  # vérifie le nom dans la doc DeepSeek
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY", "manquante"), base_url="https://api.deepseek.com")
app = FastAPI(title="Énigme du jour")

STORE_FILE = Path("puzzles.json")  # cache + secours si l'API ou le Wi-Fi lâche
STORE = json.loads(STORE_FILE.read_text("utf-8")) if STORE_FILE.exists() else {}

SUJETS = {  # titres de pages Wikipédia FR ; un titre invalide est simplement sauté
    "Statistiques et data": ["Paradoxe de Simpson", "Loi des grands nombres", "Théorème central limite",
                             "Biais du survivant", "Régression vers la moyenne", "Loi de Benford",
                             "Problème de Monty Hall", "Paradoxe des anniversaires"],
    "Économie": ["Dilemme du prisonnier", "Tragédie des biens communs", "Courbe de Laffer", "Loi de Gresham"],
    "Informatique et IA": ["Apprentissage automatique", "Réseau de neurones artificiels", "Machine de Turing", "Ada Lovelace"],
}

PROMPT = """Tu écris pour une appli d'apprentissage, sur un ton d'ami (tutoiement, chaleureux, simple).
Utilise UNIQUEMENT le texte fourni : n'ajoute aucun fait extérieur. Réponds avec un JSON seul, sans commentaire, avec les clés :
accroche : une phrase d'ami qui donne envie, sans nommer le concept
enigme : 2-3 phrases commençant par « Mon énigme du jour : », décrivant le concept sans le nommer ; le terme à deviner est remplacé par <<???>> (une seule fois)
masque : le terme exact caché, tel qu'il apparaît dans le texte
reponses_acceptees : liste de variantes acceptables (minuscules)
indice : une phrase d'aide sans donner le terme
explication : 2-3 phrases fondées sur le texte"""


def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def wiki(titre: str):
    r = httpx.get("https://fr.wikipedia.org/api/rest_v1/page/summary/" + titre.replace(" ", "_"),
                  headers={"User-Agent": "EnigmeDuJour/0.1 (hackathon)"}, timeout=10, follow_redirects=True)
    r.raise_for_status()
    d = r.json()
    return d["title"], d["extract"], d["content_urls"]["desktop"]["page"]


def generer(domaine: str):
    for _ in range(3):
        try:
            titre, extrait, url = wiki(random.choice(SUJETS[domaine]))
            rep = client.chat.completions.create(
                model=MODEL, temperature=0.7,
                messages=[{"role": "system", "content": PROMPT},
                          {"role": "user", "content": f"Titre : {titre}\nTexte : {extrait}"}])
            txt = rep.choices[0].message.content
            d = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
            # garde-fou anti-invention : le terme caché doit figurer dans l'extrait Wikipédia
            if "<<???>>" not in d["enigme"] or norm(d["masque"]) not in norm(titre + " " + extrait):
                continue
            d.update(id=uuid.uuid4().hex[:8], domaine=domaine, source={"titre": titre, "url": url})
            STORE[d["id"]] = d
            STORE_FILE.write_text(json.dumps(STORE, ensure_ascii=False, indent=1), "utf-8")
            return d
        except Exception as e:
            print("Génération échouée :", e)
    return None


class Reponse(BaseModel):
    id: str
    reponse: str
    indice_utilise: bool = False


@app.get("/api/domaines")
def domaines():
    return list(SUJETS)


@app.get("/api/enigme")
def enigme(domaine: str):
    if domaine not in SUJETS:
        raise HTTPException(400, "Domaine inconnu")
    d = generer(domaine)
    if d is None:  # secours : une énigme déjà en cache
        pool = [p for p in STORE.values() if p["domaine"] == domaine] or list(STORE.values())
        if not pool:
            raise HTTPException(503, "Génération impossible et cache vide : vérifie la clé API et la connexion")
        d = random.choice(pool)
    return {k: d[k] for k in ("id", "accroche", "enigme", "indice")}  # la réponse reste côté serveur


@app.post("/api/repondre")
def repondre(r: Reponse):
    d = STORE.get(r.id)
    if not d:
        raise HTTPException(404, "Énigme inconnue")
    donnee = norm(r.reponse)
    ok = bool(donnee) and any(a and a in donnee for a in {norm(x) for x in d["reponses_acceptees"] + [d["masque"]]})
    return {"correct": ok, "points": (5 if r.indice_utilise else 10) if ok else 0,
            "solution": d["masque"], "explication": d["explication"], "source": d["source"]}


@app.get("/api/pregenerer")
def pregenerer(n: int = 8):  # à lancer avant la démo pour remplir le cache de secours
    return {"creees": sum(generer(random.choice(list(SUJETS))) is not None for _ in range(n))}


@app.get("/")
def index():
    return FileResponse("index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)
