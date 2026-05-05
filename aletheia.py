from flask import Flask, request
import urllib.parse
import sqlite3
import feedparser

app = Flask(__name__)

DB = "aletheia.db"


# -----------------------------
# INIT DB
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            url TEXT PRIMARY KEY,
            count INTEGER
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# CLICK TRACKING
# -----------------------------
def register_click(url):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT count FROM clicks WHERE url=?", (url,))
    row = c.fetchone()

    if row:
        c.execute("UPDATE clicks SET count=count+1 WHERE url=?", (url,))
    else:
        c.execute("INSERT INTO clicks (url, count) VALUES (?, 1)", (url,))

    conn.commit()
    conn.close()


def get_click_score(url):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT count FROM clicks WHERE url=?", (url,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


# -----------------------------
# RSS NEWS
# -----------------------------
def get_news(query):
    try:
        feed = feedparser.parse(
            f"https://news.google.com/rss/search?q={query}&hl=es&gl=ES&ceid=ES:es"
        )

        items = []

        for entry in feed.entries[:5]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "snippet": "Noticia actualizada desde Google News RSS",
                "score": 2
            })

        return items

    except:
        return []


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
            <input name="q" style="padding:10px;width:80%;">
            <br><br>
            <button>Buscar</button>
        </form>
    </body>
    </html>
    """


# -----------------------------
# REDIRECT TRACKER
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    if url:
        register_click(url)
        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
    return redirect("/")


# -----------------------------
# SEARCH ENGINE MULTI-FUENTE
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)
    ql = q.lower()

    results = []

    def add(title, link, snippet, base_score):
        results.append({
            "title": title,
            "link": f"/go?url={urllib.parse.quote(link, safe='')}",
            "snippet": snippet,
            "score": base_score + get_click_score(link)
        })

    # -----------------------------
    # WIKIPEDIA / CONOCIMIENTO
    # -----------------------------
    if "wikipedia" in ql or "que es" in ql:
        add(
            "Wikipedia",
            f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}",
            "Enciclopedia colaborativa.",
            3
        )

    if "python" in ql:
        add(
            "Python oficial",
            "https://www.python.org",
            "Lenguaje de programación.",
            3
        )

    # -----------------------------
    # VIDEO
    # -----------------------------
    if "youtube" in ql or "video" in ql:
        add(
            "YouTube",
            f"https://www.youtube.com/results?search_query={encoded}",
            "Plataforma de vídeos.",
            2
        )

    # -----------------------------
    # COMPRAS
    # -----------------------------
    if "amazon" in ql or "comprar" in ql:
        add(
            "Amazon",
            f"https://www.amazon.es/s?k={encoded}",
            "Tienda online.",
            3
        )

    # -----------------------------
    # NOTICIAS RSS (NUEVO)
    # -----------------------------
    news = get_news(q)
    results.extend(news)

    # fallback
    if not results:
        add(
            "Google",
            f"https://www.google.com/search?q={encoded}",
            "Búsqueda general.",
            1
        )

    # -----------------------------
    # RANKING
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
                {r['snippet']}
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
