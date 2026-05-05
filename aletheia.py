import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
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
# DYNAMIC WEIGHTS (NUEVO CORE)
# =========================
weights = {
    "semantic": 0.6,
    "intent": 0.3,
    "context": 0.1
}

# =========================
# PERFORMANCE TRACKER (NUEVO)
# =========================
metrics = {
    "clicks": 0,
    "misses": 0,
    "avg_time": 0
}

# =========================
# UPDATE PERFORMANCE
# =========================
def update_metrics(clicked, dwell_time):
    metrics["clicks"] += 1 if clicked else 0
    metrics["misses"] += 1 if not clicked else 0

    metrics["avg_time"] = (
        metrics["avg_time"] * 0.9 + dwell_time * 0.1
    )

# =========================
# WEIGHT UPDATE ENGINE (NUEVO CORE)
# =========================
def update_weights():
    ctr = metrics["clicks"] / max(1, metrics["clicks"] + metrics["misses"])

    # ajuste suave
    if ctr > 0.6:
        weights["semantic"] += 0.01
        weights["intent"] += 0.005
    else:
        weights["context"] += 0.01

    # estabilización
    for k in weights:
        weights[k] = max(0.05, min(weights[k], 0.85))

    # normalización
    total = sum(weights.values())
    for k in weights:
        weights[k] /= total

# =========================
# INTENT
# =========================
def predict_intent(query):
    q = query.lower()

    if "python" in q or "api" in q:
        return "dev"
    if "comprar" in q:
        return "shop"
    if "qué es" in q:
        return "info"
    return "info"

# =========================
# SCORE FUNCTION (AUTO-TUNED)
# =========================
def score(query, emb, intent):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    semantic = np.dot(emb, q_emb)

    intent_factor = 0.2 if intent == "dev" else 0.1

    return (
        weights["semantic"] * semantic +
        weights["intent"] * intent_factor +
        weights["context"] * np.mean(emb)
    )

# =========================
# SEARCH
# =========================
def search(query):
    intent = predict_intent(query)

    q_emb = model.encode([query], normalize_embeddings=True)[0]

    results = []

    for i, emb in enumerate(embs):
        s = score(query, emb, intent)

        results.append((i, s))

    results.sort(key=lambda x: x[1], reverse=True)

    out = []

    for i, s in results[:12]:
        d = data[i]

        out.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": float(s),
            "weights": weights
        })

    return {
        "intent": intent,
        "weights": weights,
        "results": out
    }

# =========================
# FEEDBACK ROUTE (NUEVO CORE)
# =========================
@app.route("/feedback")
def feedback():
    clicked = request.args.get("clicked","1") == "1"
    dwell = float(request.args.get("time","3"))

    update_metrics(clicked, dwell)
    update_weights()

    return jsonify({"ok": True, "weights": weights})

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v38</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.card{background:#1c1c22;padding:12px;border-radius:14px;margin:10px;cursor:pointer}
.small{color:#777;font-size:12px}
.meta{color:#888;margin:10px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div class="meta" id="m"></div>
<div id="r"></div>

<script>
let start=0;

async function go(q){
    start = Date.now();

    const r = await fetch("/api?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("m").innerHTML =
        "WEIGHTS: " + JSON.stringify(d.weights);

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let c=document.createElement("div");
        c.className="card";

        c.innerHTML =
            "<b>"+x.title+"</b><br><br>"+
            "<span class='small'>score: "+x.score.toFixed(3)+"</span><br><br>"+
            x.desc;

        c.onclick=()=>{
            let t=(Date.now()-start)/1000;
            fetch("/feedback?clicked=1&time="+t);
            window.open(x.url);
        };

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
    print("Aletheia v38 SELF-OPTIMIZING RANKING ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
