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
# IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# ARCHIVO
# -----------------------------
INDEX_FILE = "index.json"
LOG_FILE = "aletheia.log"

MAX_INDEX = 800
MAX_TEXT = 1500
REQUEST_TIMEOUT = 4


# -----------------------------
# LOAD/SAVE
# -----------------------------
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
# LOGGING SIMPLE
# -----------------------------
def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)


# -----------------------------
# EMBEDDINGS CACHE
# -----------------------------
EMB_CACHE = {}


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
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:MAX_TEXT]

        links = []
        for a in soup.find_all("a", href=True):
            l = urllib.parse.urljoin(url, a["href"])
            if l.startswith("http"):
                links.append(l)

        return title, text, links
    except:
        return None, None, []


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
# CRAWL SEGURO
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url:
        return "URL vacía"

    # evitar loops
    if url in VISITED:
        return "Ya indexado"

    if len(INDEX) >= MAX_INDEX:
        return "Límite alcanzado"

    title, text, links = extract(url)

    if not text:
        return "Error"

    VISITED.add(url)

    INDEX.append({
        "url": url,
        "title": title,
        "text": text,
        "emb": embed(text)
    })

    # guardado seguro
    save_json(INDEX_FILE, INDEX)

    log(f"INDEXED: {url} | total={len(INDEX)}")

    # crawling limitado (solo 2 links)
    for l in links[:2]:
        if l not in VISITED and len(INDEX) < MAX_INDEX:
            try:
                t, tx, _ = extract(l)
                if tx:
                    VISITED.add(l)

                    INDEX.append({
                        "url": l,
                        "title": t,
                        "text": tx,
                        "emb": embed(tx)
                    })

            except:
                pass

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
        <h1>Aletheia v36</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" placeholder="Indexar URL">
            <button>Crawl</button>
        </form>

        <p>Sistema con control de carga y seguridad básica</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    log("Aletheia started")
    app.run(host="0.0.0.0", port=8080)
