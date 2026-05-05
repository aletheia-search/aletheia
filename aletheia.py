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
# INTENT VECTOR (NUEVO)
# =========================
intent = {
    "dev": 0.0,
    "shop": 0.0,
    "media": 0.0,
    "info": 0.0,
    "web": 0.0
}

def normalize_intent():
    total = sum(abs(v) for v in intent.values())
    if total == 0:
        return
    for k in intent:
        intent[k] /= total

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
# MEMORY UPDATE
# =========================
def update_memory(url, tag):
    now = time.time()

    if url not in memory:
        memory[url] = {"score": 0, "last": now, "tag": tag}

    m = memory[url]

    age = (now - m["last"]) / 86400
    m["score"] *= (0.98 ** age)

    m["score"] += 1
    m["last"] = now
    m["tag"] = tag

# =========================
# INTENT UPDATE (NUEVO)
# =========================
def update_intent(tag, value=0.05):
    intent[tag] = intent.get(tag, 0) + value
    normalize_intent()

# =========================
# MEMORY SCORE
# =========================
def memory_score(url):
    if url not in memory:
        return 0
    return memory[url]["score"] * 0.2

# =========================
# INTENT BOOST (NUEVO)
# =========================
def intent_score(tag):
    return intent.get(tag, 0) * 0.5

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
        update_intent(tag)

        semantic = float(scores[0][list(idx[0]).index(i)])

        final = semantic + memory_score(url) + intent_score(tag)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": final
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# PRE-PREDICTION FEED (NUEVO)
# =========================
def predicted_feed():
    ranked = []

    for d in data:
        url = d["url"]
        tag = classify(url)

        score = memory_score(url) + intent_score(tag)

        ranked.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": score
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:12]

# =========================
# ROUTER
# =========================
def route(q):
    if not q:
        return "predict"
    return "search"

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v27</title>
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
        results = search(q)
    else:
        results = predicted_feed()

    return jsonify({"results": results})

# =========================
if __name__ == "__main__":
    print("Aletheia v27 INTENT PREDICTION ONLINE")
    app.run(host="0.0.0.0", port=8080)
