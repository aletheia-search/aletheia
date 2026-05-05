import os
import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "data/index.json"
USERS_FILE = "data/users.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# IO
# =========================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# =========================
# USERS
# =========================
def get_user(uid):
    users = load_json(USERS_FILE, {})
    if uid not in users:
        users[uid] = {"clicks": {}}
    return users[uid], users

def save_user(uid, user, users):
    users[uid] = user
    save_json(USERS_FILE, users)

# =========================
# INDEX
# =========================
def load_index():
    return load_json(INDEX_FILE, [])

# =========================
# EMBEDDING
# =========================
def embed(t):
    v = model.encode([t])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# =========================
# INTENT ENGINE v2
# =========================
def detect_intent(q):
    q = q.lower()

    shopping = ["comprar", "precio", "amazon", "tienda", "barato"]
    direct = ["github", "chatgpt", "google", "youtube"]
    visual = ["ver", "imagenes", "fotos", "ideas", "ejemplos"]

    if any(x in q for x in shopping):
        return "shopping"

    if any(x in q for x in direct):
        return "direct"

    if any(x in q for x in visual):
        return "visual"

    return "info"

# =========================
# SEARCH CORE
# =========================
def search(query, user):
    index = load_index()

    intent = detect_intent(query)
    q = embed(query)

    results = []

    for item in index:
        try:
            score = cosine(q, item.get("emb", []))
        except:
            continue

        clicks = user["clicks"].get(item["url"], 0)

        # ajuste por intención (CLAVE NUEVA)
        tag = item.get("type", "info")

        if intent == tag:
            score *= 1.3

        if intent == "direct" and "github" in item["url"]:
            score *= 1.5

        score += clicks * 0.05

        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "desc": item.get("text", "")[:120],
            "score": score,
            "type": tag
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return intent, results[:9]

# =========================
# FRONTEND
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v13</title>

<style>
body {
    margin:0;
    font-family: Arial;
    background:#0f0f12;
    color:white;
}

.top {
    padding:20px;
    text-align:center;
}

input {
    width:60%;
    padding:14px;
    border-radius:10px;
    border:none;
    font-size:16px;
}

.badge {
    display:inline-block;
    margin-top:10px;
    font-size:12px;
    opacity:0.6;
}

.grid {
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap:14px;
    padding:20px;
}

.card {
    background:#1c1c22;
    padding:14px;
    border-radius:14px;
    cursor:pointer;
    transition:0.2s;
}

.card:hover {
    transform:scale(1.03);
    background:#2a2a33;
}

.title {
    font-weight:bold;
}

.desc {
    font-size:12px;
    opacity:0.7;
    margin-top:6px;
}

.type {
    font-size:10px;
    opacity:0.5;
    margin-top:8px;
}
</style>

</head>

<body>

<div class="top">
    <input id="q" placeholder="Buscar en Aletheia..." />
    <div id="mode" class="badge"></div>
</div>

<div class="grid" id="results"></div>

<script>

async function search(q){
    const r = await fetch("/search?q="+encodeURIComponent(q));
    const d = await r.json();

    document.getElementById("mode").innerText = "modo: " + d.intent;

    const box = document.getElementById("results");
    box.innerHTML = "";

    d.results.forEach(x => {
        const c = document.createElement("div");
        c.className = "card";

        c.innerHTML = `
            <div class="title">${x.title}</div>
            <div class="desc">${x.desc}</div>
            <div class="type">${x.type}</div>
        `;

        c.onclick = () => {
            window.open(x.url, "_blank");
        };

        box.appendChild(c);
    });
}

document.getElementById("q").addEventListener("keypress", e=>{
    if(e.key==="Enter") search(e.target.value);
});

</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/search")
def search_route():
    q = request.args.get("q", "")
    uid = request.args.get("user", "default")

    user, users = get_user(uid)

    intent, results = search(q, user)

    return jsonify({
        "intent": intent,
        "results": results
    })

@app.route("/click")
def click():
    uid = request.args.get("user", "default")
    url = request.args.get("url")

    user, users = get_user(uid)

    user["clicks"][url] = user["clicks"].get(url, 0) + 1
    save_user(uid, user, users)

    return jsonify({"ok": True})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v13 INTENT ENGINE ONLINE")
    app.run(host="0.0.0.0", port=8080)
