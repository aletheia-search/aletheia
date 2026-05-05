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
# IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# INDEX
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
# EMB CACHE
# -----------------------------
EMB = {}

def embed(t):
    if t in EMB:
        return EMB[t]
    v = model.encode([t])[0]
    EMB[t] = v
    return v

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# -----------------------------
# USER
# -----------------------------
def uid():
    u = request.cookies.get("uid")
    if not u:
        u = hashlib.md5(str(time.time()).encode()).hexdigest()
    return u


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
# SEARCH (UI LIMPIA)
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return home()

    q_emb = embed(q)

    results = []

    for item in INDEX:
        sim = cosine(q_emb, item["emb"])
        score = sim * 10

        if score > 2:
            results.append(item)

    results.sort(key=lambda x: cosine(q_emb, x["emb"]), reverse=True)

    html = f"""
    <html>
    <head>
        <title>Aletheia</title>
        <style>
            body {{
                font-family: Arial;
                margin: 0;
                background: #fff;
            }}
            .top {{
                text-align:center;
                margin-top:40px;
            }}
            input {{
                width: 60%;
                padding: 12px;
                font-size: 16px;
            }}
            button {{
                padding: 12px 16px;
                font-size: 16px;
            }}
            .result {{
                margin: 20px auto;
                width: 60%;
                padding: 10px;
            }}
            a {{
                font-size: 18px;
                text-decoration: none;
                color: #1a0dab;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .snippet {{
                color: #555;
                font-size: 13px;
            }}
        </style>
    </head>

    <body>

    <div class="top">
        <h1>Aletheia</h1>

        <form action="/search">
            <input name="q" value="{q}">
            <button>Buscar</button>
        </form>
    </div>

    <hr>
    """

    for r in results[:10]:
        html += f"""
        <div class="result">
            <a href="/go?url={urllib.parse.quote(r['url'])}">
                {r['title']}
            </a>
            <div class="snippet">{r['text'][:120]}</div>
        </div>
        """

    html += "</body></html>"

    resp = make_response(html)
    resp.set_cookie("uid", uid())
    return resp


# -----------------------------
# CLICK TRACK
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    if url:
        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
    return home()


# -----------------------------
# CRAWL
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "")
    if not url or len(INDEX) >= MAX_INDEX:
        return "Error"

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

    return f"Indexado: {title}"


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
            <input name="q" placeholder="Buscar en Aletheia">
            <button>Buscar</button>
        </form>

        <p style="color:gray;margin-top:20px;">
            Motor de búsqueda IA
        </p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
