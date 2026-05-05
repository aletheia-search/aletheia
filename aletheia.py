import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD DATA
# =========================
def load_index():
    try:
        return json.load(open(INDEX_FILE, "r", encoding="utf-8"))
    except:
        return []

data = load_index()

texts = [d["text"] for d in data]
urls = [d["url"] for d in data]

embs = model.encode(texts, normalize_embeddings=True)
embs = np.array(embs)

# =========================
# CLUSTERING (NUEVO CORE)
# =========================
N_CLUSTERS = 8

kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
labels = kmeans.fit_predict(embs)

clusters = {}

for i, label in enumerate(labels):
    if label not in clusters:
        clusters[label] = []

    clusters[label].append({
        "url": urls[i],
        "text": texts[i]
    })

centroids = kmeans.cluster_centers_

# =========================
# CLUSTER SCORE (NUEVO)
# =========================
def cluster_score(cluster_id):
    items = clusters[cluster_id]
    return len(items)

# =========================
# FIND CLOSEST CLUSTER
# =========================
def closest_cluster(query_emb):
    sims = np.dot(centroids, query_emb)

    return int(np.argmax(sims))

# =========================
# SEARCH
# =========================
def search(query):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    cid = closest_cluster(q_emb)

    cluster = clusters[cid]

    results = []

    for item in cluster:
        results.append({
            "url": item["url"],
            "desc": item["text"][:140],
            "cluster": cid,
            "score": cluster_score(cid)
        })

    return {
        "query_cluster": cid,
        "clusters": len(clusters),
        "results": results[:10]
    }

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v34</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.cluster{color:#888;margin:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;margin:10px;cursor:pointer}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div id="info"></div>
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("info").innerText =
        "Cluster: " + d.query_cluster + " | Total clusters: " + d.clusters;

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>URL</b><br>"+
            "<small>cluster "+x.cluster+"</small><br><br>"+
            x.desc;

        c.onclick=()=>window.open(x.url);

        box.appendChild(c);
    });
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
    print("Aletheia v34 DYNAMIC KNOWLEDGE CLUSTERS ONLINE")
    app.run(host="0.0.0.0", port=8080)
