from flask import Flask, request
import urllib.parse

app = Flask(__name__)


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
# SEARCH
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)
    ql = q.lower()

    results = []

    STOPWORDS = {"el", "la", "de", "mi", "no", "que", "como", "por", "un", "una", "es", "va"}

    def normalize(text):
        return [w for w in text.lower().split() if w not in STOPWORDS]

    def similarity(a, b):
        a_set = set(normalize(a))
        b_set = set(normalize(b))
        if not a_set or not b_set:
            return 0
        return len(a_set & b_set) / len(a_set | b_set)

    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "score": score
        })

    # -----------------------------
    # CONCEPTOS BASE
    # -----------------------------
    concepts = [
        ("ordenador lento pc rendimiento", "https://www.google.com/search?q=optimizar+pc", "Mejorar rendimiento del ordenador"),
        ("internet wifi conexion red", "https://www.google.com/search?q=problemas+wifi", "Solucionar problemas de red"),
        ("python programacion codigo tutorial", "https://www.python.org", "Lenguaje de programación Python"),
        ("comprar precio amazon tienda ofertas", "https://www.amazon.es", "Tienda online de productos"),
        ("youtube video musica tutorial", "https://www.youtube.com", "Plataforma de vídeos"),
        ("wikipedia que es definicion", "https://es.wikipedia.org", "Enciclopedia libre"),
    ]

    # -----------------------------
    # MATCH SEMÁNTICO
    # -----------------------------
    for keywords, link, snippet in concepts:
        sim = similarity(ql, keywords)
        if sim > 0.15:
            add(keywords.split()[0].title(), link, snippet, sim * 10)

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
