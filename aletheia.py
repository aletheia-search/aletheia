from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import time

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# CACHE SIMPLE
# -----------------------------
SEARCH_CACHE = {}


# -----------------------------
# PERSISTENCIA
# -----------------------------
INDEX_FILE = "index.json"
QUEUE_FILE = "queue.json"

MAX_INDEX = 800


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


INDEX = load_json(INDEX_FILE, [])
QUEUE = load_json(QUEUE_FILE, [])


# -----------------------------
# EMBEDDINGS CACHE
# -----------------------------
EMB_CACHE = {}


def embed(text):
    if text in EMB_CACHE:
        return EMB_CACHE[text]
    v = model.encode([text])[0]
    EMB_CACHE[text] = v
    return v


# -----------------------------
# COSENO
# -----------------------------
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# -----------------------------
# EXTRACT
# -----------------------------
def extract(url):
    try:
        r = requests.get(url, timeout=4)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:1500]

        return title, text
    except:
        return None, None


# -----------------------------
# SEARCH HÍBRIDO FINAL
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    if q in SEARCH_CACHE:
        return SEARCH_CACHE[q]

    q_emb = embed(q)
    now = time.time()

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        # -----------------------------
        # FACTORES DE RANKING
        # -----------------------------

        # relevancia semántica
        semantic = sim * 10

        # frescura (contenido más reciente)
        age = now - item.get("timestamp", now)
        freshness = max(0, 5 - (age / 86400))  # penaliza días viejos

        # clicks (si existen)
        clicks = item.get("clicks", 0)

        # score final híbrido
        score = semantic + (freshness * 0.5) + (clicks * 0.3)

        if score > 2:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    html = "<html><body style='font-family:Arial;margin:40px;'><h2>Resultados</h2><hr>"

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['url']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">score: {round(r['score'],2)}</div>
        </div>
        """

    html += "</body></html>"

    SEARCH_CACHE[q] = html
    return html


# -----------------------------
# CRAWL (mínimo, estable)
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "").strip()
    if not url:
        return "URL vacía"

    if len(INDEX) >= MAX_INDEX:
        return "Índice lleno"

    title, text = extract(url)
    if not text:
        return "Error"

    INDEX.append({
        "url": url,
        "title": title,
        "text": text,
        "emb": embed(text),
        "timestamp": time.time(),
        "clicks": 0
    })

    save_json(INDEX_FILE, INDEX)

    return f"Indexado: {title} | Total: {len(INDEX)}"


# -----------------------------
# HOME FINAL
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia v29</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Indexar URL</button>
        </form>

        <p>Motor híbrido IA + enlaces + frescura + clicks</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
