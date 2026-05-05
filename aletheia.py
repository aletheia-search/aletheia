import json
import numpy as np
import faiss
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

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
# EMBEDDINGS
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
# ENTRY NODE
# =========================
def get_entry(query):
    qv = model.encode([query], normalize_embeddings=True)
    qv = np.array(qv).astype("float32")

    scores, idx = index.search(qv, 1)
    return idx[0][0]

# =========================
# NEIGHBORS (GRAPH)
# =========================
def neighbors(url, topk=5):
    if url not in graph:
        return []

    links = graph[url].get("links", [])
    return links[:topk]

# =========================
# SCORE NODE
# =========================
def node_score(url):
    if url not in graph:
        return 0
    return len(graph[url].get("links", [])) * 0.1

# =========================
# BUILD PATH (NUEVO CORE)
# =========================
def build_paths(start_url, depth=2):
    paths = []

    def dfs(node, path, d):
        if d == 0:
            paths.append(path)
            return

        next_nodes = neighbors(node)

        if not next_nodes:
            paths.append(path)
            return

        for n in next_nodes:
            if n in path:
                continue
            dfs(n, path + [n], d-1)

    dfs(start_url, [start_url], depth)

    return paths

# =========================
# SCORE PATH
# =========================
def score_path(path):
    score = 0

    for i, url in enumerate(path):
        score += node_score(url) * (1 / (i + 1))

    return score

# =========================
# SEARCH (PATH-BASED)
# =========================
def search(query):
    entry_idx = get_entry(query)
    entry_url = data[entry_idx]["url"]

    paths = build_paths(entry_url, depth=2)

    scored = []

    for p in paths:
        s = score_path(p)

        last = p[-1]

        scored.append({
            "path": p,
            "final": last,
            "score": s
        })

    scored = sorted(scored, key=lambda x: x["score"], reverse=True)

    results = []

    for p in scored[:10]:
        u = p["final"]

        # buscar metadata si existe
        meta = next((d for d in data if d["url"] == u), None)

        if meta:
            results.append({
                "title": meta["title"],
                "url": u,
                "desc": meta["text"][:140],
                "type": classify(u),
                "score": p["score"]
            })

    return {
        "entry": entry_url,
        "paths": scored[:5],
        "results": results
    }

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v32</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.path{color:#888;font-size:12px;margin:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;padding:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;cursor:pointer}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div id="p"></div>
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("p").innerText =
        "ENTRY: " + d.entry;

    let box=document.getElementById("r");
    box.innerHTML="";

    let grid=document.createElement("div");
    grid.className="grid";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br>"+
            "<small>"+x.type+"</small><br><br>"+
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
    print("Aletheia v32 INTENT NAVIGATION ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
