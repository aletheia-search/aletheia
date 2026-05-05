import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
import time

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
# SESSION CONTEXT (NUEVO)
# =========================
session = {
    "queries": [],
    "clicks": [],
    "dominant": None,
    "last_update": time.time()
}

# =========================
# INTENT DETECTION
# =========================
def predict_intent(query):
    q = query.lower()

    if any(x in q for x in ["python", "code", "api", "flask"]):
        return "dev"
    if any(x in q for x in ["comprar", "precio", "amazon"]):
        return "shop"
    if any(x in q for x in ["qué es", "definición", "explica"]):
        return "info"
    if any(x in q for x in ["github", "youtube", "login"]):
        return "nav"

    return "info"

# =========================
# SESSION UPDATE (NUEVO CORE)
# =========================
def update_session(query, intent):
    session["queries"].append(query)

    session["dominant"] = intent

    session["last_update"] = time.time()

    if len(session["queries"]) > 10:
        session["queries"] = session["queries"][-10:]

# =========================
# CONTEXT BIAS VECTOR (NUEVO)
# =========================
def context_bias(intent):
    bias = np.zeros(384)

    if intent == "dev":
        bias += 0.3
    elif intent == "shop":
        bias += 0.2
    elif intent == "info":
        bias += 0.1
    elif intent == "nav":
        bias += 0.25

    return bias

# =========================
# SCORE FUNCTION (NUEVO CORE)
# =========================
def score(query, emb, intent):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    semantic = np.dot(emb, q_emb)

    bias = context_bias(intent)

    context_factor = np.mean(bias)  # simplificado

    return semantic + context_factor

# =========================
# SEARCH ENGINE
# =========================
def search(query):
    intent = predict_intent(query)

    update_session(query, intent)

    q_emb = model.encode([query], normalize_embeddings=True)[0]

    scores = []

    for i, emb in enumerate(embs):
        s = score(query, emb, intent)

        scores.append((i, s))

    scores.sort(key=lambda x: x[1], reverse=True)

    results = []

    for i, s in scores[:12]:
        d = data[i]

        results.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": float(s),
            "intent": intent,
            "session_mode": session["dominant"]
        })

    return {
        "intent": intent,
        "session": session["dominant"],
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
<title>Aletheia v37</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.meta{color:#888;margin:10px}
.card{background:#1c1c22;padding:12px;border-radius:14px;margin:10px;cursor:pointer}
.small{color:#777;font-size:12px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div class="meta" id="m"></div>
<div id="r"></div>

<script>
async function go(q){
    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("m").innerHTML =
        "INTENT: " + d.intent + " | SESSION: " + d.session;

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br><br>"+
            "<span class='small'>score: "+x.score.toFixed(3)+"</span><br><br>"+
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
    print("Aletheia v37 CONTEXT-AWARE RANKING ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
