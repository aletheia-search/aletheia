import json
import numpy as np
import faiss
import requests
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

INDEX_FILE = "store/index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD DATA
# =========================
def load():
    try:
        return json.load(open(INDEX_FILE,"r",encoding="utf-8"))
    except:
        return []

data = load()

# =========================
# FAISS INDEX
# =========================
embs = np.array([d["emb"] for d in data]).astype("float32")
index = faiss.IndexFlatIP(embs.shape[1])
index.add(embs)

# =========================
# GLOBAL POPULARITY (simple)
# =========================
global_clicks = {}

def boost(url):
    return global_clicks.get(url,0) * 0.03

# =========================
# SITE TYPE
# =========================
def classify(url):
    host = urlparse(url).netloc.lower()

    if "github" in host:
        return "dev"
    if "amazon" in host or "pccomponentes" in host:
        return "shop"
    if "youtube" in host:
        return "media"
    if "wikipedia" in host:
        return "info"

    return "web"

# =========================
# THUMBNAIL (simple proxy)
# =========================
def thumb(url):
    try:
        host = urlparse(url).netloc
        return f"https://www.google.com/s2/favicons?sz=128&domain={host}"
    except:
        return ""

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

        score = float(scores[0][list(idx[0]).index(i)])
        score += boost(url)

        results.append({
            "title": d["title"],
            "url": url,
            "desc": d["text"][:120],
            "type": classify(url),
            "thumb": thumb(url),
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results

# =========================
# DISCOVERY (related items)
# =========================
def discover(results):
    # mezcla ligera de resultados no top
    return results[3:8]

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v20</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
    gap:10px;
    padding:10px;
}

.card{
    background:#1c1c22;
    padding:12px;
    border-radius:14px;
    cursor:pointer;
    transition:0.2s;
}

.card:hover{
    transform:scale(1.03);
}

img{
    width:32px;
    height:32px;
    border-radius:6px;
}

.tag{
    font-size:11px;
    color:#aaa;
}

.section-title{
    margin:20px 10px 5px;
    color:#888;
    font-size:14px;
}
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

        c.innerHTML=
            "<img src='"+x.thumb+"'><br>"+
            "<b>"+x.title+"</b><br>"+
            "<span class='tag'>"+x.type+"</span><br><br>"+
            x.desc;

        c.onclick=()=>window.open(x.url);
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

    global_clicks[url] = global_clicks.get(url,0) + 1

    return jsonify({"ok":True})

# =========================
if __name__=="__main__":
    print("Aletheia v20 VISUAL + DISCOVERY ONLINE")
    app.run(host="0.0.0.0",port=8080)
