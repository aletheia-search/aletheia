from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import json
import os

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# ARCHIVO PERSISTENTE
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


# -----------------------------
# ESTADO GLOBAL
# -----------------------------
INDEX = load_index()
LINK_GRAPH = defaultdict(set)
PAGE_SCORE = defaultdict(float)


# reconstrucción de embeddings al arrancar
def rebuild_embeddings():
    for item in INDEX:
        item["emb"] = model.encode([item["text"]])[0]


rebuild_embeddings()


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia Persistente</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;" placeholder="Buscar...">
            <button>Buscar</button>
        </form>

        <br><br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;" placeholder="URL">
            <button>Crawl + Guardar</button>
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
# CRAWLER 2 NIVEL
# -----------------------------
@app
