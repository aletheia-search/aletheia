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
# UTIL
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
def get_user(user_id):
    users = load_json(USERS_FILE, {})
    if user_id not in users:
        users[user_id] = {"clicks": {}}
        save_json(USERS_FILE, users)
    return users[user_id], users

def update_user(user_id, user, all_users):
    all_users[user_id] = user
    save_json(USERS_FILE, all_users)

# =========================
# INDEX
# =========================
def load_index():
    return load_json(INDEX_FILE, [])

# =========================
# SEARCH
# =========================
def embed(text):
    v = model.encode([text])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def search(query, user):
    index = load_index()
    q = embed(query)

    results = []

    for item in index:
        try:
            score = cosine(q, item.get("emb", []))
        except:
            continue

        clicks = user["clicks"].get(item["url"], 0)
        score += clicks * 0.05

        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("text", "")[:120],
            "favicon": f"https://www.google.com/s2/favicons?sz=64&domain={item.get('url','')}",
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:9]

# =========================
# FRONTEND
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v10</title>

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

.grid {
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap:12px;
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
    background:#2a2a33;
    transform: scale(1.02);
}

.fav {
    width:24px;
    height:24px;
}

.title {
    font-weight:bold;
    margin-top:8px;
}

.text {
    font-size:12px;
    opacity:0.7;
    margin-top:6px;
}
</style>

</head>

<body>

<div class="top">
    <input id="q" placeholder="Buscar en Aletheia..." />
</div>

<div class="grid" id="results"></div>

<script>

async function search(q){
    const r = await fetch("/search?q="+encodeURIComponent(q));
    const d = await r.json();

    const box = document.getElementById("results");
    box.innerHTML = "";

    d.results.forEach(x => {
        const c = document.createElement("div");
        c.className = "card";

        c.innerHTML = `
            <img class="fav" src="${x.favicon}">
            <div class="title">${x.title}</div>
            <div class="text">${x.text}</div>
        `;

        c.onclick = () => {
            fetch("/click?url="+encodeURIComponent(x.url));
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
    user_id = request.args.get("user", "default")

    user, all_users = get_user(user_id)

    return jsonify({
        "results": search(q, user)
    })

@app.route("/click")
def click():
    user_id = request.args.get("user", "default")
    url = request.args.get("url")

    user, all_users = get_user(user_id)

    user["clicks"][url] = user["clicks"].get(url, 0) + 1
    update_user(user_id, user, all_users)

    return jsonify({"ok": True})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v10 VISUAL ONLINE")
    app.run(host="0.0.0.0", port=8080)
