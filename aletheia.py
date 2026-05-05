from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import hashlib
import time

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
CRAWL_QUEUE_FILE = "queue.json"

MAX_INDEX = 800
MAX_PER_RUN = 10
MAX_DEPTH = 2


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


INDEX = load_json(INDEX_FILE, [])
QUEUE = load_json(CRAWL_QUEUE_FILE, [])


# -----------------------------
# UTIL
# -----------------------------
def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def rebuild_embeddings():
    for item in INDEX:
        if "emb" not in item:
            item["emb"] = model.encode([item["text"]])[0]


rebuild_embeddings()


# -----------------------------
# EXTRACT
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
# CRAWL CONTINUO (CONTROLADO)
# -----------------------------
@app.route("/crawl")
def crawl():
    global QUEUE, INDEX

    start = request.args.get("url", "").strip()

    if start and not QUEUE:
        QUEUE.append({"url": start, "depth": 0})

    processed = 0

    while QUEUE and processed < MAX_PER_RUN and len(INDEX) < MAX_INDEX:
        item = QUEUE.pop(0)
        url = item["url"]
        depth = item["depth"]

        if depth > MAX_DEPTH:
            continue

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

        for l in links[:5]:
            QUEUE.append({"url": l, "depth": depth + 1})

        processed += 1

    save_json(INDEX_FILE, INDEX)
    save_json(CRAWL_QUEUE_FILE, QUEUE)

    return f"Crawled {processed} páginas | Index: {len(INDEX)} | Queue: {len(QUEUE)}"


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
        return "vacío"

    q_emb = model.encode([q])[0]

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        score = sim * 10

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
    return html


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia v26</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Iniciar crawl</button>
        </form>

        <p>El crawler continúa desde donde lo dejaste.</p>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
