from flask import Flask, request
import urllib.parse
import math

app = Flask(__name__)

from flask import Flask, request
import urllib.parse
import numpy as np
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# -----------------------------
# MODELO IA LIGERO LOCAL
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


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
# SIMILITUD VECTORIAL REAL
# -----------------------------
def similarity(a, b):
    emb_a = model.encode([a])[0]
    emb_b = model.encode([b])[0]

    return float(
        np.dot(emb_a, emb_b) /
        (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
    )


# -----------------------------
# BASE DE CONOCIMIENTO
# -----------------------------
CORPUS = [
    ("python programacion tutorial codigo lenguaje", "https://www.python.org", "Lenguaje de programación Python"),
    ("ordenador pc lento rendimiento mejorar velocidad", "https://www.google.com/search?q=optimizar+pc", "Mejorar rendimiento del ordenador"),
    ("internet wifi conexion router red problemas", "https://www.google.com/search?q=wifi+problemas", "Problemas de red"),
    ("comprar amazon tienda productos precio oferta", "https://www.amazon.es", "Compras online"),
    ("youtube video musica streaming tutorial", "https://www.youtube.com", "Plataforma de vídeo"),
    ("wikipedia enciclopedia definicion que es", "https://es.wikipedia.org", "Enciclopedia libre")
]


# pre-embedding (IMPORTANTE: optimiza rendimiento)
TEXTS = [c[0] for c in CORPUS]
EMBEDDINGS = model.encode(TEXTS)


# -----------------------------
# SEARCH
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)

    results = []

    q_emb = model.encode([q])[0]

    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "score": score
        })

    # -----------------------------
    # MATCH SEMÁNTICO REAL
    # -----------------------------
    for i, (text, link, snippet) in enumerate(CORPUS):

        emb = EMBEDDINGS[i]

        sim = float(
            np.dot(q_emb, emb) /
            (np.linalg.norm(q_emb) * np.linalg.norm(emb))
        )

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
# EMBEDDING LIGERO (heurístico)
# -----------------------------
VECTOR_SPACE = {
    "ordenador": ["pc", "computadora", "lento", "rendimiento", "hardware"],
    "internet": ["wifi", "red", "conexion", "router", "caido"],
    "python": ["programacion", "codigo", "script", "lenguaje"],
    "comprar": ["precio", "amazon", "tienda", "producto", "oferta"],
    "video": ["youtube", "musica", "ver", "streaming"],
    "definicion": ["que", "es", "significado", "explicacion"]
}


def tokenize(text):
    return text.lower().split()


def vectorize(text):
    tokens = tokenize(text)
    vec = set(tokens)

    for k, v in VECTOR_SPACE.items():
        if k in tokens:
            vec.update(v)

    return vec


def similarity(a, b):
    a_vec = vectorize(a)
    b_vec = vectorize(b)

    if not a_vec or not b_vec:
        return 0

    inter = len(a_vec & b_vec)
    union = len(a_vec | b_vec)

    return inter / union


# -----------------------------
# MOTOR
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)

    results = []

    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "score": score
        })

    # -----------------------------
    # BASE DE CONOCIMIENTO
    # -----------------------------
    corpus = [
        ("Python programación código tutorial", "https://www.python.org", "Lenguaje de programación Python"),
        ("ordenador pc lento rendimiento hardware", "https://www.google.com/search?q=optimizar+pc", "Mejorar rendimiento del PC"),
        ("internet wifi red conexion router", "https://www.google.com/search?q=wifi+problemas", "Solución de red"),
        ("comprar amazon precio oferta tienda", "https://www.amazon.es", "Compras online"),
        ("youtube video musica streaming", "https://www.youtube.com", "Plataforma de vídeo"),
        ("wikipedia que es definicion explicacion", "https://es.wikipedia.org", "Enciclopedia libre")
    ]

    # -----------------------------
    # MATCH SEMÁNTICO
    # -----------------------------
    for text, link, snippet in corpus:
        sim = similarity(q, text)

        if sim > 0.12:
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
            "Búsqueda general en la web.",
            1
        )

    # -----------------------------
    # ORDENAR
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
