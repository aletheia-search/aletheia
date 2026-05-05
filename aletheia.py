import queue
import threading
import time
import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer

# =========================
# MODELO
# =========================
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# CONFIG
# =========================
INDEX_FILE = "index.json"
STATE_FILE = "visited.json"
MAX_INDEX = 1000

INDEX = []
VISITED = set()

crawl_queue = queue.Queue()
lock = threading.Lock()

# =========================
# PERSISTENCIA
# =========================
def load_index():
    global INDEX
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            INDEX = json.load(f)

def save_index():
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(INDEX, f, ensure_ascii=False)

def load_visited():
    global VISITED
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            VISITED = set(json.load(f))

def save_visited():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(VISITED), f, ensure_ascii=False)

# =========================
# EMBEDDINGS
# =========================
def embed(text):
    v = model.encode([text])[0]
    return (v / (np.linalg.norm(v) + 1e-9)).tolist()

# =========================
# VALIDACIÓN
# =========================
def valid(text):
    return text and len(text) > 300

# =========================
# EXTRACCIÓN
# =========================
def extract(url):
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "AletheiaBot/1.0"})
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text.strip() if soup.title else url
        text = " ".join([p.get_text(" ", strip=True) for p in soup.find_all("p")])

        if not valid(text):
            return None

        links = []
        for a in soup.find_all("a", href=True):
            l = urllib.parse.urljoin(url, a["href"])
            if l.startswith("http"):
                links.append(l)

        return {
            "url": url,
            "title": title,
            "text": text[:2000],
            "emb": embed(text)
        }, links

    except Exception as e:
        print(f"[extract error] {url} -> {e}")
        return None

# =========================
# WORKER
# =========================
def worker():
    load_index()
    load_visited()

    while True:
        try:
            url = crawl_queue.get(timeout=5)

        except queue.Empty:
            continue

        if url in VISITED or len(INDEX) >= MAX_INDEX:
            crawl_queue.task_done()
            continue

        result = extract(url)
        if not result:
            crawl_queue.task_done()
            continue

        item, links = result

        with lock:
            VISITED.add(url)
            INDEX.append(item)

        save_index()
        save_visited()

        for l in links[:3]:
            if l not in VISITED:
                crawl_queue.put(l)

        crawl_queue.task_done()
        time.sleep(0.3)

# =========================
# ARRANQUE
# =========================
threading.Thread(target=worker, daemon=True).start()
