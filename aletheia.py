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
# INDEX LOAD
# =========================
def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# =========================
# EMBEDDING + SIMILARITY
# =========================
def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def embed(text):
    v = model.encode([text])[0]
    return (v / (np.linalg.norm(v) + 1e-9)).tolist()

# =========================
# SEARCH ENGINE
# =========================
def search(query, top_k=5):
    index = load_index()

    if not index:
        return []

    q_emb = embed(query)
    results = []

    for item in index:
        try:
            score = cosine(q_emb, item["emb"])
        except:
            continue

        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "score": score,
            "text": item.get("text", "")[:250]
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return "Aletheia ONLINE"

@app.route("/search")
def search_route():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "empty query"})

    results = search(q)

    return jsonify({
        "query": q,
        "results": results
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
    print("Aletheia ONLINE")
    app.run(host="0.0.0.0", port=8080)
