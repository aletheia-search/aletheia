from flask import Flask, request
import urllib.parse
import numpy as np
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# -----------------------------
# MODELO (SOLO UNA VEZ)
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# CORPUS BASE
# -----------------------------
CORPUS = [
    ("python programacion tutorial codigo lenguaje", "https://www.python.org", "Lenguaje de programación Python"),
    ("ordenador pc lento rendimiento mejorar velocidad", "https://www.google.com/search?q=optimizar+pc", "Mejorar rendimiento del ordenador"),
    ("internet wifi conexion router red problemas", "https://www.google.com/search?q=wifi+problemas", "Problemas de red"),
    ("comprar amazon tienda productos precio oferta", "https://www.amazon.es", "Compras online"),
    ("youtube video musica streaming tutorial", "https://www.youtube.com", "Plataforma de vídeo"),
    ("wikipedia enciclopedia definicion que es", "https://es.wikipedia.org", "Enciclopedia libre")
]


# -----------------------------
# PRECOMPUTO (CLAVE)
# -----------------------------
TEXTS = [c[0] for c in CORPUS]
EMBEDDINGS = model.encode(TEXTS, convert_to_numpy=True)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia</h1>
        <form action="/search">
            <input name="q" style="padding:10px;width:80%;" placeholder="Buscar...">
            <br><br>
            <button>Buscar</button>
        </form>
    </body>
    </html>
    """


# -----------------------------
# SIMILITUD RÁPIDA
# -----------------------------
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


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

    # -----------------------------
    # MATCH SEMÁNTICO (RÁPIDO)
    # -----------------------------
    for i, (text, link, snippet) in enumerate(CORPUS):
        sim = cosine(q_emb, EMBEDDINGS[i])

        if sim > 0.35:
            add(
                text.split()[0].title(),
                link,
                snippet,
                sim * 10
            )

    # -----------------------------
    # FALLBACK
    # -----------------------------
    if not results:
        add(
            "Google",
            f"https://www.google.com/search?q={encoded}",
            "Búsqueda general.",
            1
        )

    # -----------------------------
    # ORDER
    # -----------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    # -----------------------------
    # HTML
    # -----------------------------
    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['link']}" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="font-size:13px;color:gray;">
                {r['snippet']} (score: {round(r['score'],2)})
            </div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
