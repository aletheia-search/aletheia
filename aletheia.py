import json
import numpy as np
import faiss
import time
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"
GRAPH_FILE = "store/graph.json"

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
graph = load_json(GRAPH_FILE)

# =========================
# BUILD GRAPH INIT
# =========================
if not graph:
    graph = {}

# =========================
# EXTRACT LINKS (NUEVO)
# =========================
def extract_links(url):
    try:
        r = requests.get(url, timeout=3)
        soup = BeautifulSoup(r.text, "html.parser")

        links = []
        for a in soup.find_all("a", href=True):
            links.append(urljoin(url, a["href"]))

        return links[:10]
    except:
        return []

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
# UPDATE GRAPH (NUEVO CORE)
# =========================
def update_graph(url):
    if url not in graph:
        graph[url] = {
            "links": [],
            "neighbors": {},
            "score": 0
        }

    links = extract_links(url)

    for l in links:
        if l == url:
            continue

        if l not in graph:
            graph[l] = {
                "links": [],
                "neighbors": {},
                "score": 0
            }

        # conexión bidireccional
        graph[url]["neighbors"][l] = graph[url]["neighbors"].get(l, 0) + 1
        graph[l]["neighbors"][url] = graph[l]["neighbors"].get(url, 0) + 1

    graph[url]["links"] = links

# =========================
# GRAPH SCORE (NUEVO)
# =========================
def graph_score(url):
    if url not in graph:
        return 0

    g = graph[url]

    neighbor_strength = sum(g["neighbors"].values()) / 10

    return min(neighbor_strength, 1.0)

# =========================
# SEARCH CORE
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

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

        update_graph(url)

        semantic = float(scores[0][list(idx[0]).index(i)])

        final = semantic + graph_score(url)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:160],
            "type": classify(url),
            "score": final
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v31</title>
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
    return jsonify({"results": search(q)})

# =========================
if __name__ == "__main__":
    print("Aletheia v31 KNOWLEDGE GRAPH ONLINE")
    app.run(host="0.0.0.0", port=8080)
