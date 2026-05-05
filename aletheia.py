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
# MODELO IA (solo una vez)
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# CACHE GLOBAL
# -----------------------------
EMB_CACHE = {}
SEARCH_CACHE = {}

# -----------------------------
# PERSISTENCIA
# -----------------------------
INDEX_FILE = "index.json"
QUEUE_FILE = "queue.json"

MAX_INDEX = 800
MAX_DEPTH = 2
CRAWL_LIMIT = 10


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
# EMBEDDING CON CACHE
# -----------------------------
def embed(text):
    if text in EMB_CACHE:
        return EMB_CACHE[text]

    vec = model.encode([text])[0]
    EMB_CACHE[text] = vec
    return vec


# -----------------------------
# UTIL
# -----------------------------
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def hash_url(u):
    return hashlib.md5(u.encode()).hexdigest()


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
            l = urllib.parse.urljoin(url, a["href"])
            if l.startswith("http"):
                links.append(l)

        return title, text, links
    except:
        return None, None, []


# -----------------------------
# CRAWLER
# -----------------------------
@app.route("/crawl")
def crawl():
    global QUEUE, INDEX

    start = request.args.get("url", "")

    if start and not QUEUE:
        QUEUE.append({"url": start, "depth": 0})

    count = 0

    while QUEUE and count < CRAWL_LIMIT and len(INDEX) < MAX_INDEX:
        item = QUEUE.pop(0)
        url = item["url"]
        depth = item["depth"]

        if depth > MAX_DEPTH:
            continue

        title, text, links = extract(url)
        if not text:
            continue

        emb = embed(text)

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": emb
        })

        for l in links[:5]:
            QUEUE.append({"url": l, "depth": depth + 1})

        count += 1

    save_json(INDEX_FILE, INDEX)
    save_json(QUEUE_FILE, QUEUE)

    return f"Crawled {count} | Index {len(INDEX)} | Queue {len(QUEUE)}"


# -----------------------------
# SEARCH OPTIMIZADO
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    # cache de búsquedas
    if q in SEARCH_CACHE:
        return SEARCH_CACHE[q]

    q_emb = embed(q)

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

    SEARCH_CACHE[q] = html  # guardamos cache
    return html


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia v28</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Crawl</button>
        </form>

        <p>Cache activo + IA optimizada</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
