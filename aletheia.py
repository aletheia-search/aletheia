import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

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
# INTENT LAYER
# =========================
def intent(query):
    q = query.lower()

    if any(x in q for x in ["python", "api", "flask"]):
        return "dev"
    if any(x in q for x in ["comprar", "precio"]):
        return "shop"
    if any(x in q for x in ["qué es", "explica"]):
        return "info"
    return "info"

# =========================
# CONTEXT LAYER
# =========================
session_state = {
    "intent": None,
    "history": []
}

def update_context(query, intent):
    session_state["intent"] = intent
    session_state["history"].append(query)

    if len(session_state["history"]) > 10:
        session_state["history"] = session_state["history"][-10:]

# =========================
# UTILITY SCORE (NUEVO CORE)
# =========================
def utility_score(text, intent):
    base = len(text) / 1000

    if intent == "dev" and "code" in text.lower():
        base += 0.2
    if intent == "shop" and any(x in text.lower() for x in ["price", "buy"]):
        base += 0.2
    if intent == "info":
        base += 0.1

    return base

# =========================
# ACTION SCORE (CLAVE DEL SISTEMA)
# =========================
def action_score(query, emb, text, intent):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    semantic = np.dot(emb, q_emb)

    utility = utility_score(text, intent)

    continuity = semantic * 0.3 + utility * 0.7

    return continuity

# =========================
# DECISION ENGINE (NUEVO CORE)
# =========================
def decide(query):
    i = intent(query)
    update_context(query, i)

    results = []

    for idx, emb in enumerate(embs):
        d = data[idx]

        score = action_score(
            query,
            emb,
            d["text"],
            i
        )

        results.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    best_action = results[0] if results else None

    return {
        "intent": i,
        "best_action": best_action,
        "results": results[:10],
        "context": session_state
    }

# =========================
# UI
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v39</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.card{background:#1c1c22;padding:12px;border-radius:14px;margin:10px;cursor:pointer}
.best{border:1px solid #4caf50}
.meta{color:#888;margin:10px}
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
        "INTENT: " + d.intent + "<br>" +
        "BEST ACTION: " + (d.best_action ? d.best_action.title : "");

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let c=document.createElement("div");

        c.className="card";

        if(d.best_action && x.url === d.best_action.url){
            c.classList.add("best");
        }

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
    return jsonify(decide(q))

# =========================
if __name__ == "__main__":
    print("Aletheia v39 COGNITIVE DECISION ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
