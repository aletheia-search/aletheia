import requests
import json
import time
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np

INDEX_FILE = "index.json"
SEEDS = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://github.com",
    "https://www.bbc.com",
]

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed(t):
    v = model.encode([t])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def load():
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save(data):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def extract(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None, []

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join(p.text for p in soup.find_all("p"))[:2000]

        links = []
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("http"):
                links.append(a["href"])

        return {
            "url": url,
            "title": title,
            "text": text,
            "emb": embed(text).tolist(),
            "type": "info"
        }, links[:3]

    except:
        return None, []

def run():
    index = load()
    visited = set(i["url"] for i in index)

    queue = SEEDS[:]

    while queue and len(index) < 1000:
        url = queue.pop(0)

        if url in visited:
            continue

        data, links = extract(url)
        if data:
            index.append(data)
            visited.add(url)
            save(index)

            queue.extend(links)

        time.sleep(0.5)

if __name__ == "__main__":
    print("Crawler Aletheia ON")
    run()
