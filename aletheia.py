import json
import numpy as np
import faiss
import time
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
import os

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"
MEMORY_FILE = "store/memory.json"
GLOBAL_FILE = "store/global.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD
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
global_mem = load_json(GLOBAL_FILE)

# =========================
# SAVE GLOBAL
# =========================
def save_global():
    with open(GLOBAL_FILE, "w", encoding="utf-8") as f:
        json.dump(global_mem, f)

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
# GLOBAL UPDATE (NUEVO)
# =========================
def update_global(url, time_spent):
    if url not in global_mem:
        global_mem[url] = {
            "clicks": 0,
            "avg_time": 0,
            "trend": 0,
            "type": classify(url)
        }

    g = global_mem[url]

    g["clicks"] += 1

    g["avg_time"] = (g["avg_time"] * (g["clicks"] - 1) + time_spent) / g["clicks"]

    # tendencia global
    if time_spent > 5:
        g["trend"] += 0.05
    else:
        g["trend"] -= 0.02

    g["trend"] = max(0.0, min(1.0, g["trend"]))

    save_global()

# =========================
# GLOBAL SCORE (NUEVO)
# =========================
def global_score(url):
    if url not in global_mem:
        return 0

    g = global_mem[url]

    return g["trend"] * 0.6 + min(g["clicks"] / 1000, 0.4)

# =========================
# MEMORY SCORE
# =========================
def memory_score(url):
    if url not in memory:
        return 0
    return memory[url]["score"] * 0.15

# =========================
# SEARCH
# =========================
def search(query, k=12):
    qv = model.encode([query], normalize_embeddings=True)
    qv = np.array(qv).astype("float32")

    scores, idx = index.search(qv, k)

    results = []

    for i in idx[0]:
        if i == -1:
            continue

        d = data[i]
        url = d["url"]

        semantic = float(scores[0][list(idx[0]).index(i)])

        score = (
            semantic +
            memory_score(url) +
            global_score(url)
        )

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:160],
            "type": classify(url),
            "score": score
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# CLICK TRACKING (NUEVO)
# =========================
@app.route("/click")
def click():
    url = request.args.get("url","")
    t = float(request.args.get("time","5"))

    update_global(url, t)

    return jsonify({"ok":True})

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v30</title>
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
let start=0;

async function go(q){
    start = Date.now();

    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    let box=document.getElementById("r");
    box.innerHTML="";

    let grid=document.createElement("div");
    grid.className="grid";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br>"+
            "<span class='small'>"+x.type+"</span><br><br>"+
            x.desc;

        c.onclick=()=>{
            let t=(Date.now()-start)/1000;
            fetch("/click?url="+encodeURIComponent(x.url)+"&time="+t);
            window.open(x.url);
        };

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
    return jsonify({"results": search(q)})

# =========================
if __name__ == "__main__":
    print("Aletheia v30 GLOBAL RELEVANCE ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
