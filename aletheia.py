from flask import Flask, request, make_response
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import time
import hashlib
import threading

app = Flask(__name__)

# -----------------------------
# IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# INDEX
# -----------------------------
INDEX_FILE = "index.json"
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

# -----------------------------
# CACHE EMBEDDINGS
# -----------------------------
EMB = {}

def embed(t):
    if t in EMB:
        return EMB[t]
    v = model.encode([t])[0]
    EMB[t] = v
    return v


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
# CRAWLER ASÍNCRONO
# -----------------------------
def crawl_worker(url):
    global INDEX

    if len(INDEX) >= MAX_INDEX:
        return

    title, text = extract(url)
    if not text:
        return

    INDEX.append({
        "url": url,
        "title": title,
        "text": text,
        "emb": embed(text)
    })

    save_json(INDEX_FILE, INDEX)


# -----------------------------
# SEARCH
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return home()

    q_emb = embed(q)

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
            <a href="/go?url={urllib.parse.quote(r['url'])}" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">{r['text'][:120]}</div>
        </div>
        """

    html += "</body></html>"
    return html


# -----------------------------
# CRAWL (NO BLOQUEANTE)
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url:
        return "URL vacía"

    # hilo separado (IMPORTANTE para Railway)
    thread = threading.Thread(target=crawl_worker, args=(url,))
    thread.start()

    return f"Crawling en background: {url}"


# -----------------------------
# CLICK
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    if url:
        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
    return home()


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia v32</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Indexar URL">
            <button>Crawl async</button>
        </form>

        <p>Sistema estable con crawling en segundo plano</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
