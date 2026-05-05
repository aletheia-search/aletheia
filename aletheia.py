from flask import Flask, request, jsonify
import urllib.parse
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# CLICK MEMORY
# -----------------------------
CLICK_FILE = "clicks.json"

def load_clicks():
    if os.path.exists(CLICK_FILE):
        with open(CLICK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_clicks():
    with open(CLICK_FILE, "w") as f:
        json.dump(CLICK_MEMORY, f)

CLICK_MEMORY = load_clicks()


# -----------------------------
# CORPUS (MISMO QUE BUSCADOR)
# -----------------------------
CORPUS = [
    "python programacion tutorial codigo lenguaje",
    "ordenador pc lento rendimiento mejorar velocidad",
    "internet wifi conexion router red problemas",
    "comprar amazon tienda productos precio oferta",
    "youtube video musica streaming tutorial",
    "wikipedia enciclopedia definicion que es",
    "github repositorio codigo proyectos",
    "linux comandos terminal sistema operativo",
    "windows errores soluciones sistema",
    "inteligencia artificial machine learning ia"
]

EMBEDDINGS = model.encode(CORPUS, convert_to_numpy=True)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia</h1>

        <input id="q" style="padding:10px;width:60%;" placeholder="Buscar..." oninput="sug()">
        <button onclick="go()">Buscar</button>

        <div id="sug" style="margin-top:20px;color:gray;"></div>

        <script>
        async function sug(){
            let q = document.getElementById("q").value;
            let r = await fetch("/suggest?q=" + q);
            let data = await r.json();

            document.getElementById("sug").innerHTML =
                data.map(x => "<div onclick='select(\""+x+"\")'>"+x+"</div>").join("");
        }

        function select(t){
            document.getElementById("q").value = t;
        }

        function go(){
            let q = document.getElementById("q").value;
            window.location = "/search?q=" + encodeURIComponent(q);
        }
        </script>

    </body>
    </html>
    """


# -----------------------------
# CLICK TRACK
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    if url:
        CLICK_MEMORY[url] = CLICK_MEMORY.get(url, 0) + 1
        save_clicks()
        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
    return home()


# -----------------------------
# SEARCH
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)
    q_emb = model.encode([q], convert_to_numpy=True)[0]

    results = []

    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "score": score
        })

    for i, text in enumerate(CORPUS):
        sim = float(np.dot(q_emb, EMBEDDINGS[i]) /
                    (np.linalg.norm(q_emb) * np.linalg.norm(EMBEDDINGS[i])))

        if sim > 0.3:
            add(
                text.split()[0].title(),
                "https://www.google.com/search?q=" + urllib.parse.quote(text),
                "Resultado semántico",
                sim * 10
            )

    if not results:
        add("Google", "https://www.google.com/search?q=" + encoded, "Búsqueda general", 1)

    results.sort(key=lambda x: x["score"], reverse=True)

    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['link']}" style="font-size:18px;">{r['title']}</a>
            <div style="color:gray;font-size:13px;">{r['snippet']}</div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html


# -----------------------------
# SUGGEST ENGINE
# -----------------------------
@app.route("/suggest")
def suggest():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    q_emb = model.encode([q], convert_to_numpy=True)[0]

    scored = []

    for text in CORPUS:
        emb = model.encode([text], convert_to_numpy=True)[0]

        sim = float(np.dot(q_emb, emb) /
                    (np.linalg.norm(q_emb) * np.linalg.norm(emb)))

        scored.append((text, sim))

    scored.sort(key=lambda x: x[1], reverse=True)

    return jsonify([x[0] for x in scored[:5]])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
