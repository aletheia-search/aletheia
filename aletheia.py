import os
import json
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "index.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# HOME (launcher visual)
# =========================
QUICK_LINKS = [
    {
        "name": "Wikipedia",
        "url": "https://wikipedia.org",
        "icon": "wiki"
    },
    {
        "name": "GitHub",
        "url": "https://github.com",
        "icon": "code"
    },
    {
        "name": "ChatGPT",
        "url": "https://chat.openai.com",
        "icon": "ai"
    },
    {
        "name": "Google",
        "url": "https://google.com",
        "icon": "search"
    },
    {
        "name": "Amazon",
        "url": "https://amazon.es",
        "icon": "shop"
    }
]

# =========================
# LOAD INDEX
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
# INTENT ENGINE
# =========================
def route_query(q):
    q = q.lower()

    if "github" in q:
        return {"type": "redirect", "url": "https://github.com"}

    if "chatgpt" in q or "ia" in q:
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
            "snippet": item.get("text", "")[:180],
            "image": item.get("image", "")  # preparado para futuro
        })

    results = [r for r in results if r["score"] > 0.28]
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]

# =========================
# ENDPOINTS
# =========================

@app.route("/")
def home():
    return jsonify({
        "mode": "home",
        "quick_links": QUICK_LINKS
    })

@app.route("/search")
def search_route():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "empty query"})

    decision = route_query(q)

    # 🔴 redirección directa
    if decision["type"] == "redirect":
        return jsonify({
            "mode": "redirect",
            "url": decision["url"]
        })

    # 🔎 búsqueda visual
    results = search(q)

    return jsonify({
        "mode": "visual_search",
        "query": q,
        "results": results,
        "quick_links": QUICK_LINKS
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "index_size": len(load_index())
    })

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v4 VISUAL READY")
    app.run(host="0.0.0.0", port=8080)
