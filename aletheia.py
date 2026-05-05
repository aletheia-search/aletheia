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
import threading
import queue

app = Flask(__name__)

# -----------------------------
# IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# ESTADO DEL SISTEMA
# -----------------------------
START_TIME = time.time()


# -----------------------------
# STORAGE
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
VISITED = set()


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
# CRAWLER QUEUE
# -----------------------------
crawl_queue = queue.Queue()


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
def crawler_worker():
    global INDEX

    while True:
        url = crawl_queue.get()

        if url in VISITED or len(INDEX) >= MAX_INDEX:
            continue

        title, text, links = extract(url)
        if not text:
            continue

        VISITED.add(url)

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": embed(text)
        })

        save_json(INDEX_FILE, INDEX)

        for l in links[:2]:
            if l not in VISITED:
                crawl_queue.put(l)


threading.Thread(target=crawler_worker, daemon=True).start()


# -----------------------------
# SEARCH
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
            <a href="{r['url']}" target="_blank">{r['title']}</a>
            <div style="color:gray;">{r['text'][:120]}</div>
        </div>
        """

    html += "</body></html>"
    return html


# -----------------------------
# CRAWL
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url:
        return "URL vacía"

    crawl_queue.put(url)

    return f"En cola: {url}"


# -----------------------------
# HEALTH CHECK (NUEVO)
# -----------------------------
@app.route("/health")
def health():
    uptime = int(time.time() - START_TIME)

    return {
        "status": "ok",
        "uptime_sec": uptime,
        "index_size": len(INDEX),
        "queue_size": crawl_queue.qsize(),
        "visited": len(VISITED),
        "memory_embeddings": len(EMB)
    }


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia v39</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Indexar URL">
            <button>Crawl</button>
        </form>

        <p>Incluye monitorización del sistema (/health)</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
