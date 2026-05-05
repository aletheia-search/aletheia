from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import json
import os
import hashlib

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# PERSISTENCIA
# -----------------------------
INDEX_FILE = "index.json"
MAX_INDEX = 500  # límite duro para no romper Railway


def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    return []


def save_index():
    with open(INDEX_FILE, "w") as f:
        json.dump(INDEX, f)


# -----------------------------
# ESTADO
# -----------------------------
INDEX = load_index()
LINK_GRAPH = defaultdict(set)
PAGE_SCORE = defaultdict(float)
VISITED_HASHES = set()


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def rebuild_embeddings():
    for item in INDEX:
        if "emb" not in item:
            item["emb"] = model.encode([item["text"]])[0]


rebuild_embeddings()


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia Stable</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;" placeholder="Buscar...">
            <button>Buscar</button>
        </form>

        <br><br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;" placeholder="URL inicial">
            <button>Crawl seguro</button>
        </form>

    </body>
    </html>
    """


# -----------------------------
# EXTRACCIÓN
# -----------------------------
def extract(url):
    try:
        r = requests.get(url, timeout=4)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:1500]

        links = []
        for a in soup.find_all("a", href=True):
            link = urllib.parse.urljoin(url, a["href"])
            if link.startswith("http"):
                links.append(link)

        return title, text, links

    except:
        return None, None, []


# -----------------------------
# CRAWLER CONTROLADO
# -----------------------------
@app.route("/crawl")
def crawl():
    start_url = request.args.get("url", "").strip()
    if not start_url:
        return "URL vacía"

    queue = [(start_url, 0)]
    MAX_DEPTH = 1

    while queue and len(INDEX) < MAX_INDEX:
        url, depth = queue.pop(0)

        if depth > MAX_DEPTH:
            continue

        h = hash_url(url)
        if h in VISITED_HASHES:
            continue

        VISITED_HASHES.add(h)

        title, text, links = extract(url)
        if not text:
            continue

        emb = model.encode([text])[0]

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": emb
        })

        PAGE_SCORE[url] += 1

        # limitar branching (IMPORTANTE)
        for l in links[:5]:
            LINK_GRAPH[url].add(l)
            queue.append((l, depth + 1))

    save_index()

    return f"Indexadas: {len(INDEX)} páginas (máx {MAX_INDEX})"


# -----------------------------
# COSENO
# -----------------------------
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# -----------------------------
# SEARCH
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    q_emb = model.encode([q])[0]

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        score = (sim * 10) + (PAGE_SCORE[item["url"]] * 0.3)

        if score > 2:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['url']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">score: {round(r['score'],2)}</div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
