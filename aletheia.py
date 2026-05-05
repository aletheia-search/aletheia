import json
import numpy as np
import faiss
import random
from flask import Flask, request, jsonify, render_template_string, session
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"
FEEDBACK_FILE = "store/feedback.json"

app = Flask(__name__)
app.secret_key = "aletheia_v25_router"

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
feedback = load_json(FEEDBACK_FILE)

# =========================
# FAISS
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

# =========================
# SESSION PROFILE
# =========================
def get_profile():
    if "profile" not in session:
        session["profile"] = {"dev":0,"shop":0,"media":0,"info":0,"web":0}
    return session["profile"]

def update_profile(tag):
    p = get_profile()
    p[tag] = p.get(tag, 0) + 1
    session["profile"] = p

# =========================
# CLASSIFY
# =========================
def classify(url):
    host = urlparse(url).netloc.lower()
    if "github" in host: return "dev"
    if "youtube" in host: return "media"
    if "amazon" in host or "pccomponentes" in host: return "shop"
    if "wikipedia" in host: return "info"
    return "web"

# =========================
# SCORING SIMPLE
# =========================
def score_base():
    return 1.0

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
        update_profile(tag)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:140],
            "type": tag,
            "score": float(scores[0][list(idx[0]).index(i)])
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# FEED
# =========================
def feed():
    sample = random.sample(data, min(12, len(data)))

    return [{
        "title": d["title"],
        "url": d["url"],
        "desc": d["text"][:140],
        "type": classify(d["url"]),
        "score": 1.0
    } for d in sample]

# =========================
# RECOMMEND (NUEVO)
# =========================
def recommend():
    p = get_profile()

    dominant = max(p, key=p.get)

    filtered = [d for d in data if classify(d["url"]) == dominant]

    if not filtered:
        return feed()

    sample = random.sample(filtered, min(10, len(filtered)))

    return [{
        "title": d["title"],
        "url": d["url"],
        "desc": d["text"][:140],
        "type": dominant,
        "score": 2.0
    } for d in sample]

# =========================
# ROUTER (NUEVO)
# =========================
def route(query):
    if not query:
        return "feed"

    q = query.lower()

    if q in ["", "feed"]:
        return "feed"

    if q in ["ideas", "ver", "explorar", "descubrir"]:
        return "mix"

    if len(q) < 3:
        return "recommend"

    return "search"

# =========================
# MIX MODE
# =========================
def mix(query):
    return search(query)[:6] + feed()[:4]

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v25</title>
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
    let url="/route?q="+encodeURIComponent(q);

    const r = await fetch(url);
    const d = await r.json();

    let box = document.getElementById("r");
    box.innerHTML="";

    let grid = document.createElement("div");
    grid.className="grid";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML=
        "<b>"+x.title+"</b><br>"+
        "<span class='small'>"+x.type+"</span><br><br>"+
        x.desc;

        c.onclick=()=>{
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

@app.route("/route")
def route_api():
    q = request.args.get("q","")
    mode = route(q)

    if mode == "search":
        results = search(q)
    elif mode == "feed":
        results = feed()
    elif mode == "mix":
        results = mix(q)
    else:
        results = recommend()

    return jsonify({"results": results})

# =========================
if __name__ == "__main__":
    print("Aletheia v25 HYBRID ROUTER ONLINE")
    app.run(host="0.0.0.0", port=8080)
