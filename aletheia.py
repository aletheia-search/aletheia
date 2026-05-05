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
FEEDBACK_FILE = "store/feedback.json"

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
feedback = load_json(FEEDBACK_FILE)

# =========================
# FAISS
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

# =========================
# WEIGHTS (NUEVO AUTOEVOLUTIVO)
# =========================
weights = {
    "semantic": 0.6,
    "memory": 0.25,
    "intent": 0.15
}

def normalize_weights():
    total = sum(weights.values())
    for k in weights:
        weights[k] /= total

# =========================
# MEMORY
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
# FEEDBACK SIGNAL (NUEVO)
# =========================
def reward(click_time):
    if click_time < 2:
        return -0.2
    if click_time < 8:
        return 0.1
    return 0.3

# =========================
# UPDATE WEIGHTS (NUEVO CORE)
# =========================
def update_weights(signal):
    lr = 0.01

    weights["semantic"] += lr * (0.5 * signal)
    weights["memory"] += lr * (0.3 * signal)
    weights["intent"] += lr * (0.2 * signal)

    # clamp
    for k in weights:
        weights[k] = max(0.05, min(weights[k], 0.9))

    normalize_weights()

# =========================
# MEMORY SCORE
# =========================
def memory_score(url):
    if url not in memory:
        return 0
    return memory[url]["score"] * 0.2

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

        final = (
            weights["semantic"] * semantic +
            weights["memory"] * memory_score(url) +
            weights["intent"] * memory_score(url)
        )

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": final
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# FEEDBACK ROUTE (NUEVO)
# =========================
@app.route("/click")
def click():
    url = request.args.get("url","")
    t = float(request.args.get("time","5"))

    signal = reward(t)
    update_weights(signal)

    return jsonify({"ok":True})

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v28</title>
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
let startTime=0;

async function go(q){
    startTime = Date.now();

    const r = await fetch("/search?q="+encodeURIComponent(q));
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
            let t = (Date.now()-startTime)/1000;
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

@app.route("/search")
def search_route():
    q = request.args.get("q","")
    return jsonify({"results": search(q)})

# =========================
if __name__ == "__main__":
    print("Aletheia v28 SELF-ADAPTIVE RANKING ONLINE")
    app.run(host="0.0.0.0", port=8080)
