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
import heapq

app = Flask(__name__)

model = SentenceTransformer("all-MiniLM-L6-v2")

INDEX_FILE = "index.json"
MAX_INDEX = 800

START_TIME = time.time()

INDEX = []
VISITED = set()
CACHE = {}
EMB_CACHE = {}

crawl_queue = []

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
# EMBEDDINGS
# -----------------------------
def embed(text):
    h = hashlib.md5(text.encode()).hexdigest()
    if h in EMB_CACHE:
        return EMB_CACHE[h]

    v = model.encode([text])[0]
    v = v / (np.linalg.norm(v) + 1e-9)

    EMB_CACHE[h] = v
    return v

def cosine(a, b):
    return float(np.dot(a, b))

# -----------------------------
# QUALITY CHECK FINAL (CLAVE)
# -----------------------------
def valid(text):
    if not text:
        return False
    if len(text) < 300:
        return False
    if len(set(text.split())) < 60:
        return False
    return True

# -----------------------------
# EXTRACTOR ROBUSTO
# -----------------------------
def extract(url):
    try:
        r = requests.get(url, timeout=4)
        if r.status_code != 200:
            return None, None, None, 0

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url

        paragraphs = [p.text for p in soup.find_all("p")]
        text = " ".join(paragraphs)

        if not valid(text):
            return None, None, None, 0

        text = text[:2000]

        links = []
        for a in soup.find_all("a", href=True):
            l = urllib.parse.urljoin(url, a["href"])
            if l.startswith("http"):
                links.append(l)

        quality = min(len(text) / 1200, 2.0)

        return title, text, links, quality

    except:
        return None, None, None, 0

# -----------------------------
# CRAWLER SIMPLE
# -----------------------------
def crawler():
    while True:
        if not crawl_queue:
            time.sleep(0.2)
            continue

        url = crawl_queue.pop(0)

        if url in VISITED or len(INDEX) >= MAX_INDEX:
            continue

        title, text, links, quality = extract(url)
        if not text:
            continue

        VISITED.add(url)

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": embed(text),
            "quality": quality
        })

        save_index()

        for l in links[:2]:
            if l not in VISITED:
                crawl_queue.append(l)

threading.Thread(target=crawler, daemon=True).start()

# -----------------------------
# SEARCH SAFE
# -----------------------------
def search_engine(q):
    if q in CACHE:
        return CACHE[q]

    q_emb = embed(q)

    results = []

    for item in INDEX:
        if not item.get("text"):
            continue

        sim = cosine(q_emb, item["emb"])
        score = sim * item["quality"]

        if score > 0.23:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "text": item["text"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    CACHE[q] = results[:10]
    return CACHE[q]

# -----------------------------
# RENDER FIABLE
# -----------------------------
def render(results):
    html = """
    <html>
    <body style="font-family:Arial;margin:40px;">
    <h2>Aletheia</h2>
    <hr>
    """

    if not results:
        html += "<p>No results found</p>"

    for r in results:
        try:
            domain = r["url"].split("/")[2]
        except:
            domain = "unknown"

        snippet = r.get("text", "")
        if not snippet:
            continue

        html += f"""
        <div style="margin-bottom:20px;">
            <a href="{r['url']}" target="_blank">{r['title']}</a>
            <div style="font-size:12px;color:gray;">{domain}</div>
            <div style="font-size:13px;color:#444;">{snippet[:140]}</div>
        </div>
        """

    html += "</body></html>"
    return html

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return home()

    return render(search_engine(q))

@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url:
        return "No URL"

    crawl_queue.append(url)
    return f"Queued: {url}"

@app.route("/health")
def health():
    return {
        "status": "ok",
        "uptime": int(time.time() - START_TIME),
        "index": len(INDEX),
        "queue": len(crawl_queue),
        "cache": len(CACHE)
    }

@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h1>Aletheia</h1>

        <form action="/search">
            <input name="q" placeholder="Search">
            <button>Go</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Index URL">
            <button>Crawl</button>
        </form>

        <p>Stable output + safe rendering</p>
    </body>
    </html>
    """

# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
