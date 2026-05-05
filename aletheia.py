import os
import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# HOME LINKS (launcher)
# =========================
QUICK_LINKS = [
    {"name": "Wikipedia", "url": "https://wikipedia.org"},
    {"name": "GitHub", "url": "https://github.com"},
    {"name": "ChatGPT", "url": "https://chat.openai.com"},
    {"name": "Google", "url": "https://google.com"},
    {"name": "Amazon", "url": "https://amazon.es"}
]

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
# INTENT ROUTER
# =========================
def route_query(q):
    q = q.lower()

    if "github" in q:
        return {"type": "redirect", "url": "https://github.com"}

    if "chatgpt" in q or "ia" in q or "openai" in q:
        return {"type": "redirect", "url": "https://chat.openai.com"}

    if "wikipedia" in q:
        return {"type": "redirect", "url": "https://wikipedia.org"}

    if "amazon" in q:
        return {"type": "redirect", "url": "https://amazon.es"}

    return {"type": "search"}

# =========================
# SEARCH ENGINE
# =========================
def search(query, top_k=6):
    index = load_index()
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

        results.append({
            "title": item.get("title", ""),
            "url": url,
            "score": float(score),
            "snippet": item.get("text", "")[:180]
        })

    results = [r for r in results if r["score"] > 0.28]
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]

# =========================
# FRONTEND (HTML INLINE)
# =========================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia</title>
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

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 15px;
    padding: 20px;
}

.card {
    background: #1c1c22;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    cursor: pointer;
    transition: 0.2s;
}

.card:hover {
    transform: scale(1.05);
    background: #2a2a33;
}

.results {
    padding: 20px;
}

.result {
    background: #1c1c22;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    cursor: pointer;
}

.result:hover {
    background: #2a2a33;
}

.title {
    font-weight: bold;
    margin-bottom: 5px;
}

.snippet {
    font-size: 13px;
    opacity: 0.8;
}
</style>
</head>

<body>

<div class="topbar">
    <input id="search" placeholder="Buscar en Aletheia..." />
</div>

<div id="home" class="grid"></div>
<div id="results" class="results"></div>

<script>

async function loadHome() {
    const res = await fetch("/");
    const data = await res.json();

    const home = document.getElementById("home");
    home.innerHTML = "";

    data.quick_links.forEach(link => {
        const div = document.createElement("div");
        div.className = "card";
        div.innerText = link.name;
        div.onclick = () => window.open(link.url, "_blank");
        home.appendChild(div);
    });
}

async function search(q) {
    const res = await fetch("/search?q=" + encodeURIComponent(q));
    const data = await res.json();

    const home = document.getElementById("home");
    const results = document.getElementById("results");

    home.style.display = "none";
    results.innerHTML = "";

    if (data.mode === "redirect") {
        window.location.href = data.url;
        return;
    }

    data.results.forEach(r => {
        const div = document.createElement("div");
        div.className = "result";

        div.innerHTML = `
            <div class="title">${r.title}</div>
            <div class="snippet">${r.snippet}</div>
        `;

        div.onclick = () => window.open(r.url, "_blank");
        results.appendChild(div);
    });
}

document.getElementById("search").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        search(this.value);
    }
});

loadHome();

</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({
        "quick_links": QUICK_LINKS
    })

@app.route("/search")
def search_route():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "empty query"})

    decision = route_query(q)

    if decision["type"] == "redirect":
        return jsonify({
            "mode": "redirect",
            "url": decision["url"]
        })

    results = search(q)

    return jsonify({
        "mode": "search",
        "results": results
    })

@app.route("/ui")
def ui():
    return render_template_string(HTML_PAGE)

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v5 FULL SYSTEM ONLINE")
    app.run(host="0.0.0.0", port=8080)
