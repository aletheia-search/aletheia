import json
import numpy as np
import faiss
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
# INTENT DETECTION
# =========================
def intent(q):
    q = q.lower()

    if any(x in q for x in ["comprar", "precio", "tienda", "oferta"]):
        return "buy"

    if any(x in q for x in ["ver", "video", "youtube", "stream"]):
        return "media"

    if any(x in q for x in ["github", "codigo", "repo"]):
        return "dev"

    if any(x in q for x in ["ir a", "abrir", "entrar"]):
        return "direct"

    return "info"

# =========================
# SITE TYPE
# =========================
def classify(url):
    host = urlparse(url).netloc.lower()

    if "amazon" in host or "aliexpress" in host or "pccomponentes" in host:
        return "shop"

    if "github" in host:
        return "dev"

    if "youtube" in host:
        return "media"

    if "wikipedia" in host:
        return "info"

    return "web"

# =========================
# SEARCH ENGINE
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

        results.append({
            "title": d["title"],
            "url": d["url"],
            "desc": d["text"][:120],
            "type": classify(d["url"]),
            "score": float(scores[0][list(idx[0]).index(i)])
        })

    return results

# =========================
# GROUPING INTO CAROUSELS
# =========================
def group(results):
    groups = {
        "shop": [],
        "media": [],
        "dev": [],
        "info": [],
        "web": []
    }

    for r in results:
        groups[r["type"]].append(r)

    return groups

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v19</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}

.section{
    margin:20px;
}

.row{
    display:flex;
    overflow-x:auto;
    gap:10px;
}

.card{
    min-width:220px;
    background:#1c1c22;
    padding:12px;
    border-radius:12px;
    cursor:pointer;
}

.title{
    font-size:18px;
    margin-top:10px;
    color:#ccc;
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

    for (let key in d.results){
        let section=document.createElement("div");
        section.className="section";

        let title=document.createElement("div");
        title.className="title";
        title.innerText=key.toUpperCase();

        let row=document.createElement("div");
        row.className="row";

        d.results[key].forEach(x=>{
            let c=document.createElement("div");
            c.className="card";
            c.innerHTML="<b>"+x.title+"</b><br>"+x.desc;
            c.onclick=()=>window.open(x.url);
            row.appendChild(c);
        });

        section.appendChild(title);
        section.appendChild(row);
        box.appendChild(section);
    }
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

    raw = search(q)
    grouped = group(raw)

    return jsonify({"results": grouped})

# =========================
if __name__=="__main__":
    print("Aletheia v19 INTENT + CAROUSEL ONLINE")
    app.run(host="0.0.0.0",port=8080)
