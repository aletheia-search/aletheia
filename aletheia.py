from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# ÍNDICE GLOBAL
# -----------------------------
INDEX = []
LINK_GRAPH = defaultdict(set)
PAGE_SCORE = defaultdict(float)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia Crawler v2</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;" placeholder="Buscar...">
            <button>Buscar</button>
        </form>

        <br><br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;" placeholder="URL inicial">
            <button>Indexar (2 niveles)</button>
        </form>

    </body>
    </html>
    """


# -----------------------------
# EXTRACCIÓN
# -----------------------------
def extract(url):
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:2000]

        links = []
        for a in soup.find_all("a", href=True):
            link = urllib.parse.urljoin(url, a["href"])
            if link.startswith("http"):
                links.append(link)

        return title, text, links
    except:
        return None, None, []


# -----------------------------
# CRAWLER MULTINIVEL
# -----------------------------
@app.route("/crawl")
def crawl():
    start_url = request.args.get("url", "").strip()
    if not start_url:
        return "URL vacía"

    visited = set()

    def crawl_level(url, depth):
        if depth > 1 or url in visited:
            return

        visited.add(url)

        title, text, links = extract(url)
        if not text:
            return

        emb = model.encode([text])[0]

        INDEX.append({
            "url": url,
            "title": title,
            "text": text,
            "emb": emb
        })

        PAGE_SCORE[url] += 1  # base score

        for l in links[:10]:  # limitamos explosión
            LINK_GRAPH[url].add(l)
            PAGE_SCORE[l] += 0.5
            crawl_level(l, depth + 1)

    crawl_level(start_url, 0)

    return f"Indexadas páginas: {len(INDEX)}"


# -----------------------------
# SIMILITUD
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

        # híbrido: semántica + importancia tipo PageRank simple
        score = (sim * 10) + (PAGE_SCORE[item["url"]] * 0.5)

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
