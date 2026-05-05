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
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# PERSISTENCIA
# -----------------------------
INDEX_FILE = "index.json"


def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    return []


def save_index():
    with open(INDEX_FILE, "w") as f:
        json.dump(INDEX, f)


INDEX = load_index()


# -----------------------------
# LINK GRAPH (para PageRank)
# -----------------------------
GRAPH = {}
PAGERANK = {}


def hash_url(u):
    return hashlib.md5(u.encode()).hexdigest()


# -----------------------------
# REBUILD EMBEDDINGS
# -----------------------------
def rebuild_embeddings():
    for item in INDEX:
        if "emb" not in item:
            item["emb"] = model.encode([item["text"]])[0]


rebuild_embeddings()


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
# CRAWLER
# -----------------------------
@app.route("/crawl")
def crawl():
    start = request.args.get("url", "")
    if not start:
        return "URL vacía"

    visited = set()
    queue = [(start, 0)]
    MAX_DEPTH = 1

    while queue:
        url, depth = queue.pop(0)
        if depth > MAX_DEPTH:
            continue
        if url in visited:
            continue

        visited.add(url)

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

        GRAPH[url] = links[:5]

        for l in links[:5]:
            queue.append((l, depth + 1))

    compute_pagerank()
    save_index()

    return f"Indexadas: {len(INDEX)} páginas"


# -----------------------------
# PAGE RANK (ITERATIVO)
# -----------------------------
def compute_pagerank(iterations=10, d=0.85):
    global PAGERANK

    nodes = set(GRAPH.keys())

    for n in nodes:
        PAGERANK[n] = 1.0 / len(nodes) if nodes else 1

    for _ in range(iterations):
        new_rank = {}

        for node in nodes:
            rank_sum = 0.0

            for src, outs in GRAPH.items():
                if node in outs:
                    rank_sum += PAGERANK.get(src, 0) / max(len(outs), 1)

            new_rank[node] = (1 - d) + d * rank_sum

        PAGERANK = new_rank


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
    q = request.args.get("q", "")
    if not q:
        return "vacío"

    q_emb = model.encode([q])[0]

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        pr = PAGERANK.get(item["url"], 0.5)

        score = (sim * 10) + (pr * 2)

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
        <h1>Aletheia PageRank</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Crawl</button>
        </form>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
