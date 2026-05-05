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
# IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# CONFIG
# -----------------------------
INDEX_FILE = "index.json"
MAX_INDEX = 800

START_TIME = time.time()

# -----------------------------
# ESTADO
# -----------------------------
INDEX = []
VISITED = set()
CACHE = {}  # 🔥 NUEVO: cache de búsquedas
EMB_CACHE = {}

crawl_queue = queue.Queue()

# -----------------------------
# LOAD INDEX
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
    EMB_CACHE[h] = v
    return v

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# -----------------------------
# EXTRACT
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

        for
