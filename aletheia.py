import os
import json
import random
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "index.json"
USER_FILE = "user_profile.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# BASE LINKS
# =========================
QUICK_LINKS = [
    {"name": "Wikipedia", "url": "https://wikipedia.org"},
    {"name": "GitHub", "url": "https://github.com"},
    {"name": "ChatGPT", "url": "https://chat.openai.com"},
    {"name": "Google", "url": "https://google.com"},
    {"name": "Amazon", "url": "https://amazon.es"}
]

# =========================
# USER PROFILE
# =========================
def load_user():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clicks": {},
        "queries": [],
        "preferences": {}
    }

def save_user(data):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def track_click(url):
    user = load_user()
    user["clicks"][url] = user["clicks"].get(url, 0) + 1
    save_user(user)

# =========================
# INDEX
# =========================
def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# =========================
# EMBEDDINGS
# =========================
def embed(text):
    v = model.encode([text])[0]
    return (v / (np.linalg.norm(v) + 1e-9)).tolist()

def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# =========================
# ROUTER INTELIGENTE
# =========================
def route_query(q):
    q = q.lower()

    if "github" in q:
        return {"type": "redirect", "url": "https://github.com"}

    if "chatgpt" in q or "ia" in q:
        return {"type": "redirect", "url": "https://chat.openai.com"}

    return {"type": "search"}

# =========================
# SEARCH PERSONALIZADO
# =========================
def search(query, top_k=6):
    index = load_index()
    user = load_user()

    if not index:
        return []

    q_emb = embed(query)

    results = []
    seen = set()

    for item in index:
        url = item.get("url", "")
        if url in seen:
            continue
        seen.add(url)

        try:
            score = cosine(q_emb, item.get("emb", []))
        except:
            continue

        # 🔥 PERSONALIZACIÓN REAL
        boost = user["clicks"].get(url, 0) * 0.05
        final_score = score + boost

        results.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("text", "")[:160],
            "score": final_score,
            "favicon": "https://www.google.com/s2/favicons?sz=64&domain=" + url
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

# =========================
# FEED PERSONALIZADO
# =========================
def feed():
    index = load_index()
    user = load_user()

    scored = []

    for item in index:
        url = item.get("url", "")
        base = user["clicks"].get(url, 0)

        noise = random.uniform(0, 0.4)
        score = base + noise

        scored.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("text", "")[:140],
            "score": score,
            "favicon": "https://www.google.com/s2/favicons?sz=64&domain=" + url
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:6]

# =========================
# FRONTEND
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v8</title>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: #0f0f12;
    color: white;
}

.topbar {
    padding: 20px;
    text-align: center;
}

input {
    width: 60%;
    padding: 14px;
    border-radius: 10px;
    border: none;
    font-size: 16px;
}

.section {
    padding: 15px 20px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
}

.card {
    background: #1c1c22;
    padding: 18px;
    border-radius: 12px;
    cursor: pointer;
}

.card:hover {
    background: #2a2a33;
}

.result {
    display: flex;
    gap: 10px;
    padding: 12px;
    background: #1c1c22;
    border-radius: 10px;
    margin-bottom: 8px;
    cursor: pointer;
}

.result:hover {
    background: #2a2a33;
}

img {
    width: 32px;
    height: 32px;
}
</style>

</head>

<body>

<div class="topbar">
    <input id="q" placeholder="Buscar o explorar..." />
</div>

<div class="section">
    <h4>Accesos rápidos</h4>
    <div id="home" class="grid"></div>
</div>

<div class="section">
    <h4>Descubrimiento personalizado</h4>
    <div id="feed"></div>
</div>

<div class="section">
    <h4>Resultados</h4>
    <div id="results"></div>
</div>

<script>

async function loadHome() {
    const r = await fetch("/home");
    const d = await r.json();

    const home = document.getElementById("home");
    home.innerHTML = "";

    d.quick_links.forEach(x => {
        const c = document.createElement("div");
        c.className = "card";
        c.innerText = x.name;
        c.onclick = () => window.open(x.url, "_blank");
        home.appendChild(c);
    });
}

async function loadFeed() {
    const r = await fetch("/feed");
    const d = await r.json();

    const feed = document.getElementById("feed");
    feed.innerHTML = "";

    d.forEach(x => {
        const div = document.createElement("div");
        div.className = "result";

        div.innerHTML = `
            <img src="${x.favicon}">
            <div>
                <b>${x.title}</b><br>
                <span style="font-size:12px;opacity:0.8">${x.snippet}</span>
            </div>
        `;

        div.onclick = () => {
            fetch("/track?url=" + encodeURIComponent(x.url));
            window.open(x.url, "_blank");
        };

        feed.appendChild(div);
    });
}

async function search(q) {
    const r = await fetch("/search?q=" + encodeURIComponent(q));
    const d = await r.json();

    const results = document.getElementById("results");
    results.innerHTML = "";

    if (d.mode === "redirect") {
        window.location.href = d.url;
        return;
    }

    d.results.forEach(x => {
        const div = document.createElement("div");
        div.className = "result";

        div.innerHTML = `
            <img src="${x.favicon}">
            <div>
                <b>${x.title}</b><br>
                <span style="font-size:12px;opacity:0.8">${x.snippet}</span>
            </div>
        `;

        div.onclick = () => {
            fetch("/click?url=" + encodeURIComponent(x.url));
            window.open(x.url, "_blank");
        };

        results.appendChild(div);
    });
}

document.getElementById("q").addEventListener("keypress", e => {
    if (e.key === "Enter") search(e.target.value);
});

loadHome();
loadFeed();

</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================

@app.route("/")
def ui():
    return render_template_string(HTML)

@app.route("/home")
def home():
    return jsonify({"quick_links": QUICK_LINKS})

@app.route("/search")
def search_route():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "empty"})

    decision = route_query(q)

    if decision["type"] == "redirect":
        return jsonify({"mode": "redirect", "url": decision["url"]})

    return jsonify({
        "mode": "search",
        "results": search(q)
    })

@app.route("/feed")
def feed_route():
    return jsonify(feed())

@app.route("/click")
def click():
    url = request.args.get("url")
    if url:
        track_click(url)
    return jsonify({"ok": True})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v8 PERSONALIZED ONLINE")
    app.run(host="0.0.0.0", port=8080)
