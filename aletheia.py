from flask import Flask, request, make_response
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
import time
import hashlib

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# PERSISTENCIA GLOBAL
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


# -----------------------------
# EMBEDDING CACHE
# -----------------------------
EMB_CACHE = {}


def embed(text):
    if text in EMB_CACHE:
        return EMB_CACHE[text]
    v = model.encode([text])[0]
    EMB_CACHE[text] = v
    return v


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# -----------------------------
# USER ID (sin login)
# -----------------------------
def get_user_id():
    uid = request.cookies.get("uid")
    if not uid:
        uid = hashlib.md5(str(time.time()).encode()).hexdigest()
    return uid


USER_MEMORY = {}


def get_user_memory(uid):
    if uid not in USER_MEMORY:
        USER_MEMORY[uid] = {"clicks": {}}
    return USER_MEMORY[uid]


# -----------------------------
# EXTRACT
# -----------------------------
def extract(url):
    try:
        r = requests.get(url, timeout=4)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:1500]

        return title, text
    except:
        return None, None


# -----------------------------
# SEARCH MULTIUSUARIO
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    uid = get_user_id()
    mem = get_user_memory(uid)

    if not q:
        return home()

    q_emb = embed(q)

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])

        clicks = mem["clicks"].get(item["url"], 0)

        score = (sim * 10) + (clicks * 0.5)

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
            <a href="/go?url={urllib.parse.quote(r['url'])}" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">score: {round(r['score'],2)}</div>
        </div>
        """

    html += "</body></html>"

    resp = make_response(html)
    resp.set_cookie("uid", uid)
    return resp


# -----------------------------
# CLICK TRACKING POR USUARIO
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    uid = get_user_id()
    mem = get_user_memory(uid)

    if url:
        mem["clicks"][url] = mem["clicks"].get(url, 0) + 1

        resp = make_response(
            f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
        )
        resp.set_cookie("uid", uid)
        return resp

    return home()


# -----------------------------
# CRAWL SIMPLE
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url or len(INDEX) >= MAX_INDEX:
        return "Error o límite alcanzado"

    title, text = extract(url)
    if not text:
        return "Error"

    INDEX.append({
        "url": url,
        "title": title,
        "text": text,
        "emb": embed(text)
    })

    save_json(INDEX_FILE, INDEX)

    return f"Indexado: {title} | Total: {len(INDEX)}"


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia v30</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;">
            <button>Buscar</button>
        </form>

        <br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;">
            <button>Indexar URL</button>
        </form>

        <p>Sistema multiusuario sin login + ranking personalizado</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
