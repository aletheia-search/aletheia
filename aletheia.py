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

# -----------------------------
# ESTADO
# -----------------------------
START_TIME = time.time()
INDEX = []
VISITED = set()

crawl_queue = queue.Queue()
EMB_CACHE = {}

# -----------------------------
# LOAD / SAVE
# -----------------------------
def load_index():
    global INDEX
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            INDEX = json.load(f)
    else:
        INDEX = []

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
    EMB_CACHE[h] = v
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

        emb = embed(text)

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": emb
        })

        save_index()

        for l in links[:2]:
            if l not in VISITED:
                crawl_queue.put(l)

threading.Thread(target=crawler, daemon=True).start()

# -----------------------------
# SEARCH
# -----------------------------
def render(results):
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial; margin: 40px; }
            a { font-size: 18px; text-decoration: none; color: #1a0dab; }
            a:hover { text-decoration: underline; }
            .item { margin-bottom: 20px; }
            .url { font-size: 12px; color: gray; }
            .text { font-size: 13px; color: #444; }
        </style>
    </head>
    <body>
    <h2>Aletheia Search</h2>
    <hr>
    """

    if not results:
        html += "<p>No results</p>"

    for r in results:
        domain = r["url"].split("/")[2] if "://" in r["url"] else r["url"]

        html += f"""
        <div class="item">
            <a href="{r['url']}" target="_blank">{r['title']}</a>
            <div class="url">{domain}</div>
            <div class="text">{r['text'][:140]}</div>
        </div>
        """

    html += "</body></html>"
    return html

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
        "queue": crawl_queue.qsize()
    }

# -----------------------------
# HOME
# -----------------------------
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

        <p>Simple semantic search engine</p>
    </body>
    </html>
    """

# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
