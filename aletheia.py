import os
import json
import time
import requests
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================
INDEX_FILE = "data/index.json"
CACHE_FILE = "data/cache.json"
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
# CACHE
# =========================
def load_cache():
    return load_json(CACHE_FILE, {})

def get_cached(url, cache):
    return cache.get(url)

def set_cache(url, data, cache):
    cache[url] = data
    save_json(CACHE_FILE, cache)

# =========================
# USERS
# =========================
def get_user(user_id):
    users = load_json(USERS_FILE, {})
    if user_id not in users:
        users[user_id] = {"clicks": {}}
    return users[user_id], users

def save_user(user_id, user, users):
    users[user_id] = user
    save_json(USERS_FILE, users)

# =========================
# INDEX
# =========================
def load_index():
    return load_json(INDEX_FILE, [])

# =========================
# EMBEDDING
# =========================
def embed(text):
    v = model.encode([text])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# =========================
# PREVIEW (con cache)
# =========================
def fetch_preview(url, cache):
    cached = get_cached(url, cache)
    if cached:
        return cached

    try:
        r = requests.get(url, timeout=4)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url

        desc = ""
        d = soup.find("meta", attrs={"name": "description"})
        if d and d.get("content"):
            desc = d["content"]

        img = ""
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            img = og["content"]

        if not img:
            img = f"https://www.google.com/s2/favicons?sz=128&domain={url}"

        data = {
            "title": title,
            "desc": desc[:140],
            "img": img
        }

        set_cache(url, data, cache)
        return data

    except:
        data = {
            "title": url,
            "desc": "",
            "img": f"https://www.google.com/s2/favicons?sz=128&domain={url}"
        }
        set_cache(url, data, cache)
        return data

# =========================
# SEARCH
# =========================
def search(query, user):
    index = load_index()
    cache = load_cache()

    q = embed(query)

    results = []

    for item in index:
        try:
            score = cosine(q, item.get("emb", []))
        except:
            continue

        clicks = user["clicks"].get(item["url"], 0)
        score += clicks * 0.05

        preview = fetch_preview(item["url"], cache)

        results.append({
            "url": item["url"],
            "score": score,
            "title": preview["title"],
            "desc": preview["desc"] or item.get("text", "")[:120],
            "img": preview["img"]
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
<title>Aletheia v12</title>

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
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap:14px;
    padding:20px;
}

.card {
    background:#1c1c22;
    border-radius:14px;
    overflow:hidden;
    cursor:pointer;
    transition:0.2s;
}

.card:hover {
    transform: scale(1.03);
    background:#2a2a33;
}

.card img {
    width:100%;
    height:140px;
    object-fit:cover;
}

.content {
    padding:12px;
}

.title {
    font-weight:bold;
}

.desc {
    font-size:12px;
    opacity:0.75;
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
            <img src="${x.img}">
            <div class="content">
                <div class="title">${x.title}</div>
                <div class="desc">${x.desc}</div>
            </div>
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

    user, users = get_user(user_id)

    return jsonify({
        "results": search(q, user)
    })

@app.route("/click")
def click():
    user_id = request.args.get("user", "default")
    url = request.args.get("url")

    user, users = get_user(user_id)

    user["clicks"][url] = user["clicks"].get(url, 0) + 1
    save_user(user_id, user, users)

    return jsonify({"ok": True})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v12 CACHE+FAST ONLINE")
    app.run(host="0.0.0.0", port=8080)
