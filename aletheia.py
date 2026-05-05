import json
import numpy as np
import time
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
GRAPH_FILE = "store/graph.json"
INDEX_FILE = "store/index.json"

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

graph = load_json(GRAPH_FILE)
data = load_index()

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
# INIT GRAPH NODE
# =========================
def ensure_node(url):
    if url not in graph:
        graph[url] = {
            "edges": {},
            "score": 0,
            "last": time.time()
        }

# =========================
# UPDATE EDGE (NUEVO CORE)
# =========================
def update_edge(a, b):
    ensure_node(a)
    ensure_node(b)

    edges = graph[a]["edges"]

    edges[b] = edges.get(b, 0) + 1

    graph[a]["last"] = time.time()

# =========================
# DECAY (NUEVO)
# =========================
def decay_graph():
    now = time.time()

    for node in list(graph.keys()):
        age = (now - graph[node]["last"]) / 86400

        # decaimiento suave
        graph[node]["score"] *= (0.99 ** age)

        # decaimiento de edges
        for e in list(graph[node]["edges"].keys()):
            graph[node]["edges"][e] *= 0.98

            if graph[node]["edges"][e] < 0.1:
                del graph[node]["edges"][e]

# =========================
# BUILD RELATION
# =========================
def relate(url, neighbors):
    for n in neighbors:
        update_edge(url, n)

# =========================
# GRAPH SCORE
# =========================
def graph_score(url):
    if url not in graph:
        return 0

    return sum(graph[url]["edges"].values()) * 0.05

# =========================
# ENTRY PICK
# =========================
def get_entry(query):
    qv = model.encode([query], normalize_embeddings=True)
    qv = np.array(qv).astype("float32")

    # simplificado: primer nodo
    return list(graph.keys())[0] if graph else None

# =========================
# PATH EXPANSION
# =========================
def expand(start, depth=2):
    paths = []

    def walk(node, path, d):
        if d == 0:
            paths.append(path)
            return

        if node not in graph:
            return

        neighbors = sorted(graph[node]["edges"].items(), key=lambda x: x[1], reverse=True)

        for n, w in neighbors[:3]:
            if n in path:
                continue
            walk(n, path + [n], d-1)

    walk(start, [start], depth)

    return paths

# =========================
# SCORE PATH
# =========================
def score_path(path):
    return sum(graph_score(n) for n in path)

# =========================
# SEARCH (AUTO-ORGANIZING)
# =========================
def search(query):
    decay_graph()

    entry = get_entry(query)

    if not entry:
        return {"results": []}

    paths = expand(entry)

    ranked = []

    for p in paths:
        s = score_path(p)

        ranked.append({
            "path": p,
            "final": p[-1],
            "score": s
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    results = []

    for r in ranked[:10]:
        url = r["final"]

        meta = next((d for d in data if d["url"] == url), None)

        if meta:
            results.append({
                "title": meta["title"],
                "url": url,
                "desc": meta["text"][:140],
                "type": classify(url),
                "score": r["score"]
            })

    return {"results": results}

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v33</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;padding:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;cursor:pointer}
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
    print("Aletheia v33 SELF-ORGANIZING GRAPH ONLINE")
    app.run(host="0.0.0.0", port=8080)
