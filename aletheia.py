from flask import Flask, render_template, request, jsonify
import os
import json

app = Flask(__name__)

# -------------------------
# CARGA DE DATOS
# -------------------------
DATA_FILE = "index.json"
DATA_FOLDER = "data"

def load_index():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"files": []}

index_data = load_index()

# -------------------------
# FUNCIÓN DE BÚSQUEDA SIMPLE
# -------------------------
def search_files(query):
    results = []
    query = query.lower()

    for item in index_data.get("files", []):
        name = item.get("file", "").lower()
        path = item.get("path", "")

        if query in name:
            results.append({
                "file": item.get("file"),
                "path": path
            })

    return results

# -------------------------
# RUTA PRINCIPAL (WEB)
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------
# RUTA DE BÚSQUEDA (API JSON)
# -------------------------
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "query": query,
            "results": []
        })

    results = search_files(query)

    return jsonify({
        "query": query,
        "results": results
    })

# -------------------------
# EJECUCIÓN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
