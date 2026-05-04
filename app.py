from flask import Flask, request, jsonify
import re

app = Flask(__name__)

# =========================
# DATASET BASE (inicio)
# =========================
documents = [
    {"id": 1, "text": "hospital con inteligencia artificial y diagnóstico médico"},
    {"id": 2, "text": "sistema de seguridad informática y control de accesos"},
    {"id": 3, "text": "navegador sin rastreo ni cookies ni seguimiento"},
    {"id": 4, "text": "plataforma de salud y biotecnología aplicada"},
    {"id": 5, "text": "infraestructura de servidores y computación distribuida"},
]

# =========================
# UTILIDAD
# =========================
def tokenize(text):
    return re.findall(r'\w+', text.lower())

# =========================
# BUSQUEDA REAL
# =========================
def search_engine(query):

    query_tokens = tokenize(query)

    results = []

    for doc in documents:

        doc_tokens = tokenize(doc["text"])

        score = sum(1 for t in query_tokens if t in doc_tokens)

        if score > 0:
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results

# =========================
# API
# =========================
@app.route("/api/search")
def search():

    q = request.args.get("q", "")

    results = search_engine(q)

    return jsonify({
        "query": q,
        "results": results
    })

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(debug=True)