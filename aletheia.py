from flask import Flask, request
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
import urllib.parse

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# CONFIG
# -----------------------------
INDEX_FILE = "index.json"
MAX_INDEX = 800

START_TIME = time.time()

INDEX = []
VISITED = set()
EMB_CACHE = {}
CACHE = {}

crawl_queue = queue.Queue()

# -----------------------------
# LOAD
# -----------------------------
def load_index():
    global INDEX
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            INDEX = json.load(f)

def save_index():
    with open(INDEX_FILE, "w") as f:
        json.dump(INDEX, f)

load_index()

# -----------------------------
# EMBEDDINGS NORMALIZADOS
# -----------------------------
def embed(text):
    h = hashlib.md5(text.encode()).hexdigest()

    if h in EMB_CACHE:
        return EMB_CACHE[h]

    v = model.encode([text])[0]

    # 🔥 normalización (CLAVE PARA RANKING ESTABLE)
    v = v / (np.linalg.norm(v) + 1e-9)

    EMB_CACHE[h] = v
    return v

def cosine(a, b):
    return float(np.dot(a, b))

# -----------------------------
# EXTRACTOR
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
def crawler():
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

        save_index()

        for l in links[:2]:
            if l not in VISITED:
                crawl_queue.put(l)

threading.Thread(target=crawler, daemon=True).start()

# -----------------------------
# SEARCH CACHEADA
# -----------------------------
def search_engine(q):
    if q in CACHE:
        return CACHE[q]

    q_emb = embed(q)

    results = []

    for item in INDEX:
        score = cosine(q_emb, item["emb"])

        if score > 0.25:  # 🔥 umbral más estable
            results.append({
                "title": item["title"],
                "url": item["url"],
                "text": item["text"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    CACHE[q] = results[:10]  # cache limitada

    return CACHE[q]

# -----------------------------
# UI
# -----------------------------
def render(results):
    html = """
    <html>
    <body style="font-family:Arial;margin:40px;">
    <h2>Aletheia</h2>
    <hr>
    """

    if not results:
        html += "<p>No results</p>"

    for r in results:
        domain = r["url"].split("/")[2] if "://" in r["url"] else r["url"]

        html += f"""
        <div style="margin-bottom:20px;">
            <a href="{r['url']}" target="_blank">{r['title']}</a>
            <div style="font-size:12px;color:gray;">{domain}</div>
            <div style="font-size:13px;color:#444;">{r['text'][:140]}</div>
        </div>
        """

    html += "</body></html>"
    return html

# -----------------------------
# SEARCH ROUTE
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return home()

    results = search_engine(q)
    return render(results)

# -----------------------------
# CRAWL
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url:
        return "No URL"

    crawl_queue.put(url)
    return f"Queued: {url}"

# -----------------------------
# HEALTH
# -----------------------------
@app.route("/health")
def health():
    return {
        "status": "ok",
        "uptime": int(time.time() - START_TIME),
        "index": len(INDEX),
        "queue": crawl_queue.qsize(),
        "cache_queries": len(CACHE)
    }

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia v43</h1>

        <form action="/search">
            <input name="q" placeholder="Search">
            <button>Go</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Index URL">
            <button>Crawl</button>
        </form>

        <p>Stable ranking + normalized embeddings + cache</p>
    </body>
    </html>
    """

# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
