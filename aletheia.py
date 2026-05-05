import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

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
# INTENT MODEL (NUEVO CORE)
# =========================
INTENT_LABELS = [
    "dev",
    "shop",
    "info",
    "nav",
    "media"
]

def predict_intent(query):
    q = query.lower()

    if any(x in q for x in ["python", "code", "flask", "api"]):
        return "dev"

    if any(x in q for x in ["comprar", "precio", "amazon", "producto"]):
        return "shop"

    if any(x in q for x in ["qué es", "definición", "explica"]):
        return "info"

    if any(x in q for x in ["github", "login", "youtube", "google"]):
        return "nav"

    return "info"

# =========================
# QUERY EXPANSION (NUEVO)
# =========================
def expand_query(query, intent):
    if intent == "dev":
        return query + " tutorial documentation examples"

    if intent == "shop":
        return query + " reviews price comparison"

    if intent == "info":
        return query + " explanation summary"

    return query

# =========================
# INTENT FILTERING (NUEVO)
# =========================
def filter_by_intent(results, intent):
    filtered = []

    for r in results:
        url = r["url"]

        if intent == "dev" and "github" in url:
            filtered.append(r)
        elif intent == "shop" and any(x in url for x in ["amazon", "shop"]):
            filtered.append(r)
        elif intent == "nav":
            filtered.append(r)
        elif intent == "info":
            filtered.append(r)
        else:
            filtered.append(r)

    return filtered

# =========================
# SEARCH CORE
# =========================
def search(query):
    intent = predict_intent(query)
    expanded = expand_query(query, intent)

    q_emb = model.encode([expanded], normalize_embeddings=True)[0]

    sims = np.dot(embs, q_emb)

    top_idx = np.argsort(-sims)[:12]

    results = []

    for i in top_idx:
        d = data[i]

        results.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": float(sims[i])
        })

    results = filter_by_intent(results, intent)

    return {
        "intent": intent,
        "expanded_query": expanded,
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
<title>Aletheia v35</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.tag{color:#888;margin:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;margin:10px;cursor:pointer}
.small{color:#777;font-size:12px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div id="meta"></div>
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("meta").innerHTML =
        "INTENT: " + d.intent + "<br>" +
        "<span class='small'>EXPANDED: " + d.expanded_query + "</span>";

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br><br>"+
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
    print("Aletheia v35 INTENT PREDICTION ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
