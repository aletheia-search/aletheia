import json
import numpy as np
import faiss
import math
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
import time

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"
FEEDBACK_FILE = "store/feedback.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

AI_WEIGHT = 0.15

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
feedback = load_json(FEEDBACK_FILE)

# =========================
# FAISS INDEX
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

# =========================
# FEEDBACK
# =========================
def save_feedback():
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedback, f)

def register_click(url):
    feedback[url] = feedback.get(url, 0) + 1
    save_feedback()

# =========================
# IA (re-ranker interno simple)
# =========================
def ai_adjust(url, semantic_score):
    # IA muy limitada: solo ajuste ligero
    base = feedback.get(url, 0) * 0.02
    return max(min(base, AI_WEIGHT), -AI_WEIGHT)

# =========================
# DECAY
# =========================
def decay(value, age_days):
    return value * (0.97 ** age_days)

# =========================
# CLASSIFY
# =========================
def classify(url):
    host = urlparse(url).netloc.lower()

    if "github" in host:
        return "dev"
    if "youtube" in host:
        return "media"
    if "wikipedia" in host:
        return "info"
    if "amazon" in host or "pccomponentes" in host:
        return "shop"

    return "web"

# =========================
# SCORING FINAL
# =========================
def final_score(url, semantic, clicks):
    behavior = clicks * 0.1
    ai = ai_adjust(url, semantic)

    score = (
        0.60 * semantic +
        0.25 * behavior +
        0.15 * ai
    )

    return score * (1 + math.log(1 + clicks))

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
        clicks = feedback.get(url, 0)

        score = final_score(url, semantic, clicks)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:160],
            "type": classify(url),
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v22</title>
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
    const r=await fetch("/search?q="+q);
    const d=await r.json();

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
            fetch("/click?url="+encodeURIComponent(x.url));
            window.open(x.url);
        };

        grid.appendChild(c);
    });

    box.appendChild(grid);
}

document.getElementById("q").onkeydown=e=>{
    if(e.key==="Enter") go(e.target.value);
}
</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return HTML

@app.route("/search")
def search_route():
    q = request.args.get("q","")
    return jsonify({"results": search(q)})

@app.route("/click")
def click():
    url = request.args.get("url")
    register_click(url)
    return jsonify({"ok":True})

# =========================
if __name__ == "__main__":
    print("Aletheia v22 ONLINE (unified scoring system)")
    app.run(host="0.0.0.0", port=8080)
