from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import hashlib

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# ARCHIVOS PERSISTENTES
# -----------------------------
INDEX_FILE = "index.json"
EMB_FILE = "embeddings.json"

MAX_INDEX = 800


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


# -----------------------------
# CARGA DE DATOS
# -----------------------------
RAW_INDEX = load_json(INDEX_FILE, [])
EMB_INDEX = load_json(EMB_FILE, {})

INDEX = []


# -----------------------------
# EMBEDDINGS PERSISTENTES
# -----------------------------
def get_embedding(text):
    h = hashlib.md5(text.encode()).hexdigest()

    if h in EMB_INDEX:
        return np.array(EMB_INDEX[h])

    v = model.encode([text])[0]
    EMB_INDEX[h] = v.tolist()

    return v


def build_index():
    global INDEX
    INDEX = []

    for item in RAW_INDEX:
        emb = get_embedding(item["text"])

        INDEX.append({
            "url": item["url"],
            "title": item["title"],
            "text": item["text"],
            "emb": np.array(emb)
        })


build_index()


# -----------------------------
# COSENO
# -----------------------------
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# -----------------------------
# EXTRACTOR
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
# SEARCH (ESTABLE)
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return home()

    q_emb = model.encode([q])[0]

    results = []

    for item in INDEX:
        score = cosine(q_emb, item["emb"]) * 10

        if score > 2:
            results.append(item)

    results.sort(key=lambda x: cosine(q_emb, x["emb"]), reverse=True)

    html = "<html><body style='font-family:Arial;margin:40px;'><h2>Resultados</h2><hr>"

    for r in results[:10]:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['url']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">{r['text'][:120]}</div>
        </div>
        """

    html += "</body></html>"
    return html


# -----------------------------
# CRAWL PERSISTENTE
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url or len(RAW_INDEX) >= MAX_INDEX:
        return "Error"

    title, text = extract(url)
    if not text:
        return "Error"

    RAW_INDEX.append({
        "url": url,
        "title": title,
        "text": text
    })

    # guardar todo de forma segura
    save_json(INDEX_FILE, RAW_INDEX)
    save_json(EMB_FILE, EMB_INDEX)

    build_index()

    return f"Indexado: {title} | Total: {len(RAW_INDEX)}"


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia v34</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Indexar URL">
            <button>Crawl</button>
        </form>

        <p>Arquitectura estable con embeddings persistentes</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
