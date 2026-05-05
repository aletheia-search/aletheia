from flask import Flask, request, session
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import hashlib

app = Flask(__name__)
app.secret_key = "aletheia_secret_key"

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# PERSISTENCIA
# -----------------------------
INDEX_FILE = "index.json"
QUEUE_FILE = "queue.json"

MAX_INDEX = 800
MAX_CRAWL_PER_RUN = 10
MAX_DEPTH = 2


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w"):
        json.dump(data, f)


INDEX = load_json(INDEX_FILE, [])
QUEUE = load_json(QUEUE_FILE, [])

# -----------------------------
# SESIONES (ranking ligero por usuario)
# -----------------------------
if "clicks" not in session:
    session["clicks"] = {}


# -----------------------------
# UTIL
# -----------------------------
def hash_url(u):
    return hashlib.md5(u.encode()).hexdigest()


def rebuild():
    for i in INDEX:
        if "emb" not in i:
            i["emb"] = model.encode([i["text"]])[0]


rebuild()


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
# CRAWLER CONTROLADO
# -----------------------------
@app.route("/crawl")
def crawl():
    global QUEUE, INDEX

    start = request.args.get("url", "")

    if start and not QUEUE:
        QUEUE.append({"url": start, "depth": 0})

    count = 0

    while QUEUE and count < MAX_CRAWL_PER_RUN and len(INDEX) < MAX_INDEX:
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

        count += 1

    save_json(INDEX_FILE, INDEX)
    save_json(QUEUE_FILE, QUEUE)

    return f"Crawled {count} | Index: {len(INDEX)} | Queue: {len(QUEUE)}"


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
        return home()

    q_emb = model.encode([q])[0]

    clicks = session.get("clicks", {})

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        # ranking híbrido final
        link_score = clicks.get(item["url"], 0) * 0.5

        score = (sim * 10) + link_score

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
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="/go?url={urllib.parse.quote(r['url'])}" style="font-size:18px;">
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


# -----------------------------
# CLICK TRACKING
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")

    if url:
        clicks = session.get("clicks", {})
        clicks[url] = clicks.get(url, 0) + 1
        session["clicks"] = clicks

        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'

    return home()


# -----------------------------
# HOME FINAL
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia v27</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Crawl</button>
        </form>

        <p>Sistema completo: IA + crawler + ranking + sesión</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
