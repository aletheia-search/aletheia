import json
import numpy as np
import faiss
import math
import time
import os
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

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
        return {}

def load_index():
    try:
        return json.load(open(INDEX_FILE, "r", encoding="utf-8"))
    except:
        return []

data = load_index()
memory = load_json(MEMORY_FILE)

# =========================
# SAVE MEMORY
# =========================
def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f)

# =========================
# FAISS
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

# =========================
# CLASSIFY
# =========================
def classify(url):
    host = urlparse(url).netloc.lower()
    if "github" in host: return "dev"
    if "youtube" in host: return "media"
    if "amazon" in host: return "shop"
    if "wikipedia" in host: return "info"
    return "web"

# =========================
# MEMORY UPDATE (NUEVO)
# =========================
def update_memory(url, tag):
    now = time.time()

    if url not in memory:
        memory[url] = {
            "count": 0,
            "last": now,
            "trend": 0,
            "tag": tag
        }

    m = memory[url]

    age_days = (now - m["last"]) / 86400

    # decay natural
    m["trend"] *= (0.97 ** age_days)

    m["count"] += 1
    m["last"] = now

    # crecimiento de interés
    m["trend"] += 1

    m["tag"] = tag

    save_memory()

# =========================
# MEMORY SCORE (NUEVO)
# =========================
def memory_score(url):
    if url not in memory:
        return 0

    m = memory[url]

    age_days = (time.time() - m["last"]) / 86400

    return (m["trend"] * 0.3) * (0.98 ** age_days)

# =========================
# SEARCH
# =========================
def search(query, k=10):
    qv = model.encode([query], normalize_embeddings=True)
    qv = np.array(qv).astype("float32")

    scores, idx = index.search(qv, k)

    results = []

    for i in idx[0]:
        if i == -1:
            continue

        d = data[i]
        url = d["url"]

        tag = classify(url)

        update_memory(url, tag)

        semantic = float(scores[0][list(idx[0]).index(i)])
        mem = memory_score(url)

        final = semantic + mem

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": final
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# FEED INTELIGENTE
# =========================
def feed():
    ranked = []

    for d in data:
        url = d["url"]
        tag = classify(url)

        update_memory(url, tag)

        score = memory_score(url)

        ranked.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": score
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:12]

# =========================
# ROUTE SIMPLE
# =========================
def route(query):
    if not query:
        return "feed"
    if len(query) < 3:
        return "feed"
    return "search"

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v26</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;padding:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;cursor:pointer}
.small{color:#888;font-size:12px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    let box = document.getElementById("r");
    box.innerHTML="";

    let grid = document.createElement("div");
    grid.className="grid";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br>"+
            "<span class='small'>"+x.type+"</span><br><br>"+
            x.desc;

        c.onclick=()=>window.open(x.url);

        grid.appendChild(c);
    });

    box.appendChild(grid);
}

document.getElementById("q").onkeydown=e=>{
    if(e.key==="Enter") go(e.target.value);
}

window.onload=()=>go("");
</script>

</body>
</html>
"""

# =========================
@app.route("/")
def home():
    return HTML

@app.route("/api")
def api():
    q = request.args.get("q","")

    mode = route(q)

    if mode == "search":
        return jsonify({"results": search(q)})
    else:
        return jsonify({"results": feed()})

# =========================
if __name__ == "__main__":
    print("Aletheia v26 MEMORY ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
