import os
import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "index.json"
USAGE_FILE = "usage.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# LINKS BASE
# =========================
QUICK_LINKS = [
    {"name": "Wikipedia", "url": "https://wikipedia.org"},
    {"name": "GitHub", "url": "https://github.com"},
    {"name": "ChatGPT", "url": "https://chat.openai.com"},
    {"name": "Google", "url": "https://google.com"},
    {"name": "Amazon", "url": "https://amazon.es"}
]

# =========================
# USAGE MEMORY
# =========================
def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_usage(data):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def bump_usage(url):
    data = load_usage()
    data[url] = data.get(url, 0) + 1
    save_usage(data)

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
# ROUTER
# =========================
def route_query(q):
    q = q.lower()

    if "github" in q:
        return {"type": "redirect", "url": "https://github.com"}

    if "chatgpt" in q or "ia" in q:
        return {"type": "redirect", "url": "https://chat.openai.com"}

    if "amazon" in q:
        return {"type": "redirect", "url": "https://amazon.es"}

    return {"type": "search"}

# =========================
# SEARCH
# =========================
def search(query, top_k=6):
    index = load_index()
    usage = load_usage()

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

        boost = usage.get(url, 0) * 0.02
        final_score = score + boost

        results.append({
            "title": item.get("title", ""),
            "url": url,
            "snippet": item.get("text", "")[:160],
            "score": final_score,
            "favicon": "https://www.google.com/s2/favicons?sz=64&domain=" + url
        })

    results = [r for r in results if r["score"] > 0.28]
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]

# =========================
# FRONTEND
# =========================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v6</title>

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
}

.card:hover {
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
    display: flex;
    gap: 10px;
    align-items: center;
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
    <input id="search" placeholder="Buscar en Aletheia..." />
</div>

<div id="home" class="grid"></div>
<div id="results" class="results"></div>

<script>

async function loadHome() {
    const res = await fetch("/home");
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
            <img src="${r.favicon}">
            <div>
                <div><b>${r.title}</b></div>
                <div style="font-size:12px;opacity:0.8">${r.snippet}</div>
            </div>
        `;

        div.onclick = () => {
            fetch("/track?url=" + encodeURIComponent(r.url));
            window.open(r.url, "_blank");
        };

        results.appendChild(div);
    });
}

document.getElementById("search").addEventListener("keypress", function(e) {
    if (e.key === "Enter") search(this.value);
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
def ui():
    return render_template_string(HTML_PAGE)

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

    results = search(q)

    return jsonify({
        "mode": "search",
        "results": results
    })

@app.route("/track")
def track():
    url = request.args.get("url")
    if url:
        bump_usage(url)
    return jsonify({"ok": True})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v6 FULL RUNNING")
    app.run(host="0.0.0.0", port=8080)
