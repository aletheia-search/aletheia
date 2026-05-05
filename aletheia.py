from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import hashlib
import threading

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# ARCHIVOS
# -----------------------------
INDEX_FILE = "index.json"
LOCK = threading.Lock()

MAX_INDEX = 800


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with LOCK:
        with open(path, "w") as f:
            json.dump(data, f)


# -----------------------------
# DATOS
# -----------------------------
INDEX = load_json(INDEX_FILE, [])


# -----------------------------
# EMBEDDINGS CACHE
# -----------------------------
EMB = {}


def embed(text):
    h = hashlib.md5(text.encode()).hexdigest()

    if h in EMB:
        return EMB[h]

    v = model.encode([text])[0]
    EMB[h] = v
    return v


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
# CRAWL SEGURO
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url or len(INDEX) >= MAX_INDEX:
        return "Error"

    title, text = extract(url)
    if not text:
        return "Error"

    INDEX.append({
        "url": url,
        "title": title,
        "text": text,
        "emb": embed(text)
    })

    save_json(INDEX_FILE, INDEX)

    return f"Indexado: {title} | Total: {len(INDEX)}"


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia v35</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Indexar URL">
            <button>Crawl</button>
        </form>

        <p>Sistema estable listo para usuarios públicos</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
