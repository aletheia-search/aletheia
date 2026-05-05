import os
import json
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer

# =========================
# CONFIG
# =========================
INDEX_FILE = "data/index.json"
USERS_FILE = "data/users.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# UTILIDADES JSON
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
# USUARIOS
# =========================
def get_user(user_id):
    users = load_json(USERS_FILE, {})
    if user_id not in users:
        users[user_id] = {
            "clicks": {},
            "history": []
        }
        save_json(USERS_FILE, users)
    return users[user_id], users

def update_user(user_id, user_data, all_users):
    all_users[user_id] = user_data
    save_json(USERS_FILE, all_users)

# =========================
# INDEX
# =========================
def load_index():
    return load_json(INDEX_FILE, [])

# =========================
# EMBEDDINGS
# =========================
def embed(text):
    v = model.encode([text])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def cosine(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# =========================
# ROUTER (INTENCIÓN)
# =========================
def route(query):
    q = query.lower()

    if any(x in q for x in ["github", "chatgpt", "google"]):
        return "redirect"

    if any(x in q for x in ["imagen", "fotos", "ver"]):
        return "visual"

    return "search"

# =========================
# BUSCADOR
# =========================
def search(query, user):
    index = load_index()

    if not index:
        return []

    q_emb = embed(query)
    results = []

    for item in index:
        try:
            score = cosine(q_emb, item.get("emb", []))
        except:
            continue

        # personalización simple
        clicks = user.get("clicks", {}).get(item["url"], 0)
        score += clicks * 0.05

        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("text", "")[:160],
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:8]

# =========================
# APP
# =========================
@app.route("/")
def home():
    return "Aletheia v9.1 ONLINE"

@app.route("/search")
def search_route():
    q = request.args.get("q", "")
    user_id = request.args.get("user", "default")

    user, all_users = get_user(user_id)

    mode = route(q)

    if mode == "redirect":
        return jsonify({"mode": "redirect"})

    results = search(q, user)

    return jsonify({
        "mode": "search",
        "results": results
    })

@app.route("/click")
def click():
    user_id = request.args.get("user", "default")
    url = request.args.get("url")

    user, all_users = get_user(user_id)

    user["clicks"][url] = user["clicks"].get(url, 0) + 1
    user["history"].append(url)

    update_user(user_id, user, all_users)

    return jsonify({"ok": True})

# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v9.1 RUNNING")
    app.run(host="0.0.0.0", port=8080)
