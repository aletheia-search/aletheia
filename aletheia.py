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

    c.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            query TEXT PRIMARY KEY,
            count INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS index_table (
            query TEXT,
            title TEXT,
            url TEXT,
            snippet TEXT,
            score REAL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# INDEX OPERATIONS
# -----------------------------
def search_index(q):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT title, url, snippet, score FROM index_table WHERE query=?", (q,))
    rows = c.fetchall()
    conn.close()

    return rows


def save_index(q, results):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM index_table WHERE query=?", (q,))

    for r in results:
        c.execute("""
            INSERT INTO index_table (query, title, url, snippet, score)
            VALUES (?, ?, ?, ?, ?)
        """, (q, r["title"], r["url"], r["snippet"], r["score"]))

    conn.commit()
    conn.close()


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
# SEARCH MEMORY
# -----------------------------
def register_search(q):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT count FROM searches WHERE query=?", (q,))
    row = c.fetchone()

    if row:
        c.execute("UPDATE searches SET count=count+1 WHERE query=?", (q,))
    else:
        c.execute("INSERT INTO searches (query, count) VALUES (?, 1)", (q,))

    conn.commit()
    conn.close()


def get_search_score(q):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT count FROM searches WHERE query=?", (q,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


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
# SEARCH ENGINE + INDEX
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    register_search(q)

    encoded = urllib.parse.quote(q)
    ql = q.lower()

    results = []

    # -----------------------------
    # 1. BUSCAR EN ÍNDICE
    # -----------------------------
    indexed = search_index(ql)

    if indexed:
        for t, url, snip, score in indexed:
            results.append({
                "title": t,
                "link": f"/go?url={urllib.parse.quote(url, safe='')}",
                "snippet": snip,
                "score": score + get_click_score(url)
            })

    # -----------------------------
    # 2. SI NO HAY ÍNDICE → GENERAR
    # -----------------------------
    if not results:

        def add(title, url, snippet, base_score):
            score = base_score + get_click_score(url) + get_search_score(q) * 0.5

            results.append({
                "title": title,
                "link": f"/go?url={urllib.parse.quote(url, safe='')}",
                "snippet": snippet,
                "score": score,
                "raw_url": url
            })

        # INTENCIONES
        if "python" in ql:
            add("Python oficial", "https://www.python.org", "Lenguaje de programación.", 3)

        if "youtube" in ql:
            add("YouTube", f"https://www.youtube.com/results?search_query={encoded}", "Vídeos.", 2)

        if "wikipedia" in ql or "que es" in ql:
            add("Wikipedia", f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}", "Enciclopedia.", 3)

        if "amazon" in ql or "comprar" in ql:
            add("Amazon", f"https://www.amazon.es/s?k={encoded}", "Tienda online.", 3)

        if not results:
            add("Google", f"https://www.google.com/search?q={encoded}", "Búsqueda general.", 1)

        # guardar en índice
        save_index(ql, results)

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


# -----------------------------
# TRACK CLICK
# -----------------------------
@app.route("/go")
def go():
    url = request.args.get("url")
    if url:
        register_click(url)
        return f'<script>window.open("{url}", "_blank"); window.location="/";</script>'
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
