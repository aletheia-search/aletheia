from flask import Flask, request, jsonify, render_template
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import os

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

INDEX_FILE = "store/index.json"

# =========================
# LOAD DATA
# =========================
def load_data():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data()

# =========================
# EMBEDDINGS
# =========================
def build_embeddings():
    texts = [d["text"] for d in data]
    if not texts:
        return np.array([])
    return model.encode(texts, normalize_embeddings=True)

embs = build_embeddings()

# =========================
# LANGUAGE DETECTION SIMPLE
# =========================
def detect_lang(q):
    if any(x in q.lower() for x in ["qué", "cómo", "comprar"]):
        return "es"
    return "en"

# =========================
# SEARCH
# =========================
def search(query):
    if len(data) == 0:
        return []

    q_emb = model.encode([query], normalize_embeddings=True)[0]

    sims = np.dot(embs, q_emb)
    idx = np.argsort(-sims)[:12]

    results = []

    for i in idx:
        d = data[i]
        results.append({
            "title": d.get("title", ""),
            "url": d["url"],
            "desc": d["text"][:160],
            "score": float(sims[i])
        })

    return results

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api")
def api():
    q = request.args.get("q", "")

    return jsonify({
        "query": q,
        "lang": detect_lang(q),
        "results": search(q)
    })

# =========================
if __name__ == "__main__":
    print("Aletheia LIVE")
    app.run(host="0.0.0.0", port=8080)
