import time
import json
import threading
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np

INDEX_FILE = "store/index.json"

model = SentenceTransformer("all-MiniLM-L6-v2")

SEEDS = [
    "https://en.wikipedia.org/wiki/Technology",
    "https://github.com/explore",
    "https://www.bbc.com/news"
]

def embed(t):
    v = model.encode([t])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def load():
    try:
        return json.load(open(INDEX_FILE,"r",encoding="utf-8"))
    except:
        return []

def save(data):
    json.dump(data, open(INDEX_FILE,"w",encoding="utf-8"), indent=2)

def extract(url):
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text,"html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join(p.text for p in soup.find_all("p"))[:2000]

        links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("http")]

        return {
            "url": url,
            "title": title,
            "text": text,
            "emb": embed(text).tolist(),
            "type": "info"
        }, links[:3]

    except:
        return None, []

def loop():
    while True:
        index = load()
        visited = set(i["url"] for i in index)
        queue = SEEDS[:]

        while queue and len(index) < 1500:
            url = queue.pop(0)
            if url in visited:
                continue

            data, links = extract(url)
            if data:
                index.append(data)
                visited.add(url)
                save(index)

                queue.extend(links)

            time.sleep(0.4)

threading.Thread(target=loop, daemon=True).start()

print("Crawler v15 running...")
while True:
    time.sleep(10)
