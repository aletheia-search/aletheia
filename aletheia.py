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

model = SentenceTransformer("all-MiniLM-L6-v2")

INDEX_FILE = "index.json"
MAX_INDEX = 1000

INDEX = []
VISITED = set()
crawl_queue = queue.Queue()

def load_index():
    global INDEX
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            INDEX = json.load(f)

def save_index():
    with open(INDEX_FILE, "w") as f:
        json.dump(INDEX, f)

def embed(text):
    v = model.encode([text])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def valid(text):
    return text and len(text) > 300

def extract(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])

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

    except:
        return None

def worker():
    load_index()

    while True:
        url = crawl_queue.get()

        if url in VISITED or len(INDEX) >= MAX_INDEX:
            continue

        result = extract(url)
        if not result:
            continue

        item, links = result

        VISITED.add(url)
        INDEX.append(item)

        save_index()

        for l in links[:2]:
            if l not in VISITED:
                crawl_queue.put(l)

        time.sleep(0.3)

threading.Thread(target=worker, daemon=True).start()
