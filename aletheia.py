from flask import Flask, request
import urllib.parse
import sqlite3
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

DB = "aletheia.db"


# -----------------------------
# INIT DB
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            query TEXT PRIMARY KEY,
            result TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# -----------------------------
# CACHE GET
# -----------------------------
def get_cache(q):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT result FROM cache WHERE query=?", (q,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


# -----------------------------
# CACHE SET
# -----------------------------
def set_cache(q, result):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("REPLACE INTO cache (query, result) VALUES (?, ?)", (q, result))
    conn.commit()
    conn.close()


# -----------------------------
# WIKIPEDIA SCRAPER
# -----------------------------
def wiki_snippet(query):
    try:
        url = f"https://es.wikipedia.org/wiki/{query.replace(' ', '_')}"
        r = requests.get(url, timeout=3)

        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        p = soup.find("p")

        if p:
            return p.text.strip()[:300]

    except:
        pass

    return None


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aletheia</title>
    </head>

    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:80%;">
            <br><br>
            <button>Buscar</button>
        </form>
    </body>
    </html>
    """


# -----------------------------
# SEARCH ENGINE CON MEMORIA
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)
    ql = q.lower()

    # -----------------------------
    # CACHE HIT
    # -----------------------------
    cached = get_cache(ql)
    if cached:
        return cached

    results = []

    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "score": score
        })

    # -----------------------------
    # INTENCIONES
    # -----------------------------
    if "wikipedia" in ql or "que es" in ql:
        snippet = wiki_snippet(q) or "Definición en Wikipedia."
        add("Wikipedia", f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}", snippet, 3)

    if "python" in ql:
        snippet = wiki_snippet("Python (programming language)") or "Lenguaje de programación."
        add("Python", "https://www.python.org", snippet, 3)
        add("Python YouTube", f"https://www.youtube.com/results?search_query=python+tutorial", "Tutoriales de Python.", 2)

    if "youtube" in ql:
        add("YouTube", f"https://www.youtube.com/results?search_query={encoded}", "Vídeos.", 2)

    if "amazon" in ql or "comprar" in ql:
        add("Amazon", f"https://www.amazon.es/s?k={encoded}", "Tienda online.", 3)

    if "noticias" in ql:
        add("Google News", f"https://www.google.com/search?q={encoded}", "Noticias.", 2)

    if not results:
        add("Google", f"https://www.google.com/search?q={encoded}", "Búsqueda general.", 1)

    # -----------------------------
    # ORDENAR
    # -----------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    # -----------------------------
    # HTML
    # -----------------------------
    html = f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aletheia - {q}</title>
    </head>

    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:25px 0;">
            <a href="{r['link']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="font-size:13px;color:gray;margin-top:5px;">
                {r['snippet']}
            </div>
        </div>
        """

    html += """
        <br><br>
        <a href="/">← Volver</a>
    </body>
    </html>
    """

    # -----------------------------
    # GUARDAR EN CACHE
    # -----------------------------
    set_cache(ql, html)

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
