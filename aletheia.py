import json
import numpy as np
import faiss
import time
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
# MEMORY SCORE
# =========================
def memory_score(url):
    if url not in memory:
        return 0
    return memory[url]["score"] * 0.2

# =========================
# SEARCH CORE
# =========================
def search_raw(query, k=12):
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

        score = float(scores[0][list(idx[0]).index(i)]) + memory_score(url)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:160],
            "type": tag,
            "score": score
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# GROUPING (NUEVO)
# =========================
def group(results):
    grouped = {}

    for r in results:
        t = r["type"]
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(r)

    return grouped

# =========================
# SYNTHESIS (NUEVO)
# =========================
def synthesize(grouped):
    summary = []

    for k, items in grouped.items():
        top = items[:3]

        titles = ", ".join([x["title"] for x in top])

        summary.append(f"{k.upper()}: {titles}")

    return " | ".join(summary)

# =========================
# FULL SEARCH
# =========================
def search(query):
    raw = search_raw(query)
    grouped = group(raw)

    return {
        "summary": synthesize(grouped),
        "results": raw
    }

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v29</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.summary{padding:10px;margin:10px;color:#aaa;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;padding:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;cursor:pointer}
.small{color:#888;font-size:12px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div class="summary" id="s"></div>
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("s").innerText = d.summary;

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
    return jsonify(search(q))

# =========================
if __name__ == "__main__":
    print("Aletheia v29 SYNTHESIS ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
