import json
import numpy as np
import faiss
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

INDEX_FILE = "store/index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD
# =========================
def load_data():
    return json.load(open(INDEX_FILE,"r",encoding="utf-8"))

data = load_data()

faiss_index = faiss.read_index("store/faiss.index")

# =========================
# SEARCH FAST
# =========================
def search(query, k=10):
    qv = model.encode([query], normalize_embeddings=True)
    qv = np.array(qv).astype("float32")

    scores, idx = faiss_index.search(qv, k)

    results = []
    for i in idx[0]:
        if i == -1:
            continue

        d = data[i]

        results.append({
            "title": d["title"],
            "url": d["url"],
            "desc": d["text"][:150],
            "score": float(scores[0][list(idx[0]).index(i)])
        })

    return results

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v17</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.card{background:#1c1c22;margin:10px;padding:10px;cursor:pointer;border-radius:10px}
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

    d.results.forEach(x=>{
        let div=document.createElement("div");
        div.className="card";
        div.innerHTML="<b>"+x.title+"</b><br>"+x.desc;
        div.onclick=()=>window.open(x.url);
        box.appendChild(div);
    });
}

document.getElementById("q").onkeydown=e=>{
    if(e.key==="Enter") go(e.target.value);
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return HTML

@app.route("/search")
def search_route():
    q=request.args.get("q","")
    return jsonify({"results": search(q)})

if __name__=="__main__":
    print("Aletheia v17 VECTOR SEARCH ONLINE")
    app.run(host="0.0.0.0",port=8080)
