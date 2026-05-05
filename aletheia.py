import json
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import os
from collections import Counter

# =========================
# CONFIG
# =========================
INDEX_FILE = "store/index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LOAD DATA
# =========================
def load_data():
    try:
        return json.load(open(INDEX_FILE, "r", encoding="utf-8"))
    except:
        return []

data = load_data()

def save_data():
    os.makedirs("store", exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

# =========================
# EMBEDDINGS
# =========================
def embeddings():
    texts = [d["text"] for d in data]
    if not texts:
        return np.array([])
    return model.encode(texts, normalize_embeddings=True)

embs = embeddings()

# =========================
# TOPIC EXTRACTION (SIMPLIFIED)
# =========================
def topic(url):
    if "github" in url:
        return "dev"
    if "amazon" in url:
        return "shop"
    if "wikipedia" in url:
        return "info"
    return "web"

# =========================
# ENTROPY (NUEVO CORE)
# =========================
def entropy():
    topics = [topic(d["url"]) for d in data]

    if not topics:
        return 0

    counts = Counter(topics)

    total = len(topics)

    probs = [c / total for c in counts.values()]

    return -sum(p * np.log(p + 1e-9) for p in probs)

# =========================
# BALANCE SCORE (NUEVO)
# =========================
def imbalance_penalty():
    topics = [topic(d["url"]) for d in data]

    counts = Counter(topics)

    if not counts:
        return 0

    max_topic = max(counts.values())
    total = sum(counts.values())

    return max_topic / total

# =========================
# DRIFT CONTROL (NUEVO CORE)
# =========================
def stability_factor():
    ent = entropy()
    imbalance = imbalance_penalty()

    return (ent * 0.6) + ((1 - imbalance) * 0.4)

# =========================
# ADJUST SCORES (NUEVO)
# =========================
def score(query, emb, text, url):
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    semantic = np.dot(emb, q_emb)

    stability = stability_factor()

    return semantic * stability

# =========================
# SEARCH
# =========================
def search(query):
    global embs
    embs = embeddings()

    results = []

    for i, emb in enumerate(embs):
        d = data[i]

        s = score(query, emb, d["text"], d["url"])

        results.append({
            "title": d.get("title",""),
            "url": d["url"],
            "desc": d["text"][:140],
            "score": float(s),
            "stability": stability_factor()
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "entropy": entropy(),
        "stability": stability_factor(),
        "results": results[:10]
    }

# =========================
@app.route("/api")
def api():
    q = request.args.get("q","")
    return jsonify(search(q))

@app.route("/")
def home():
    return """
    <html>
    <body style="background:#111;color:white;font-family:Arial">
    <h3>Aletheia v43</h3>
    <input id="q" style="padding:10px;width:60%">
    <div id="r"></div>

    <script>
    async function go(){
        let q=document.getElementById("q").value;
        let r=await fetch("/api?q="+q);
        let d=await r.json();

        let box=document.getElementById("r");
        box.innerHTML =
            "ENTROPY: "+d.entropy+"<br>"+
            "STABILITY: "+d.stability+"<br><br>";

        d.results.forEach(x=>{
            let div=document.createElement("div");
            div.innerHTML="<b>"+x.title+"</b><br>"+x.desc+"<hr>";
            box.appendChild(div);
        });
    }

    document.getElementById("q").onkeydown=e=>{
        if(e.key==="Enter") go();
    }
    </script>
    </body>
    </html>
    """

# =========================
if __name__ == "__main__":
    print("Aletheia v43 COGNITIVE STABILITY ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
