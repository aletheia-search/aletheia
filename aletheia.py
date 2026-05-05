import json
import requests
from bs4 import BeautifulSoup
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import threading
import time
import os

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"
MEMORY_FILE = "store/memory.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD DATA
# =========================
def load_json(path):
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except:
        return []

data = load_json(INDEX_FILE)
memory = load_json(MEMORY_FILE)

def save_index():
    os.makedirs("store", exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

# =========================
# EMBEDDINGS
# =========================
def rebuild_embeddings():
    texts = [d["text"] for d in data]
    return model.encode(texts, normalize_embeddings=True)

embs = rebuild_embeddings()

# =========================
# GAP DETECTOR (NUEVO CORE)
# =========================
def detect_gaps():
    scores = {}

    for m in memory:
        q = m["query"]

        scores[q] = scores.get(q, 0) + 1

    gaps = sorted(scores.items(), key=lambda x: x[1])

    return [g[0] for g in gaps[:5]]

# =========================
# QUERY GENERATOR (NUEVO)
# =========================
def generate_queries():
    gaps = detect_gaps()

    generated = []

    for g in gaps:
        if "python" in g:
            generated.append(g + " advanced tutorial")
        elif "api" in g:
            generated.append(g + " best practices")
        else:
            generated.append(g + " explanation")

    return generated

# =========================
# CRAWLER (NUEVO CORE)
# =========================
def crawl(url):
    try:
        r = requests.get(url, timeout=5)

        soup = BeautifulSoup(r.text, "html.parser")

        text = " ".join([p.text for p in soup.find_all("p")])

        if len(text) < 200:
            return None

        title = soup.title.text if soup.title else url

        return {
            "url": url,
            "title": title,
            "text": text[:3000]
        }

    except:
        return None

# =========================
# AUTO INGESTION (NUEVO)
# =========================
def ingest(item):
    data.append(item)

    global embs
    embs = rebuild_embeddings()

    save_index()

# =========================
# AUTONOMOUS LOOP (NUEVO CORE)
# =========================
def autonomous_loop():
    while True:
        queries = generate_queries()

        for q in queries:
            # simulación de búsqueda externa
            url = "https://example.com/" + q.replace(" ", "_")

            item = crawl(url)

            if item:
                ingest(item)

        time.sleep(30)

# =========================
# SEARCH (SIMPLIFICADO)
# =========================
def search(query):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    scores = np.dot(embs, q_emb)

    idx = np.argsort(-scores)[:10]

    results = []

    for i in idx:
        d = data[i]

        results.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": float(scores[i])
        })

    return {
        "results": results,
        "auto_crawl_active": True,
        "knowledge_size": len(data)
    }

# =========================
# START AUTONOMOUS THREAD
# =========================
threading.Thread(target=autonomous_loop, daemon=True).start()

# =========================
@app.route("/api")
def api():
    q = request.args.get("q","")
    return jsonify(search(q))

# =========================
@app.route("/")
def home():
    return """
    <html>
    <body style="background:#111;color:white;font-family:Arial">
    <h2>Aletheia v41</h2>
    <input id="q" style="padding:10px;width:60%">
    <div id="r"></div>

    <script>
    async function go(){
        let q=document.getElementById("q").value;
        let r=await fetch("/api?q="+q);
        let d=await r.json();

        let box=document.getElementById("r");
        box.innerHTML="";

        d.results.forEach(x=>{
            let div=document.createElement("div");
            div.innerHTML="<b>"+x.title+"</b><br>"+x.desc;
            box.appendChild(div);
        });
    }

    document.getElementById("q").onkeydown=e=>{
        if(e.key==="Enter") go();
    }
    </script>
    </body>
    </html>
    """

# =========================
if __name__ == "__main__":
    print("Aletheia v41 AUTONOMOUS CRAWLER ONLINE")
    app.run(host="0.0.0.0", port=8080)
