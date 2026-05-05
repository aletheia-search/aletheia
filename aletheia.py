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
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aletheia</title>
    </head>

    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia</h1>

        <form action="/search">
            <input name="q" placeholder="Buscar..." style="padding:10px;width:80%;">
            <br><br>
            <button type="submit">Buscar</button>
        </form>
    </body>
    </html>
    """


# -----------------------------
# SEARCH (SERP)
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)

    results = []

    # -----------------------------
    # MOTOR DE RESULTADOS
    # -----------------------------

    if "python" in q.lower():
        results.append(("Python oficial", "https://www.python.org"))
        results.append(("Tutorial YouTube Python", f"https://www.youtube.com/results?search_query=python+tutorial"))

    if "youtube" in q.lower():
        results.append(("YouTube", f"https://www.youtube.com/results?search_query={encoded}"))

    if "wikipedia" in q.lower() or "que es" in q.lower():
        results.append(("Wikipedia ES", f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}"))

    if "amazon" in q.lower() or "comprar" in q.lower():
        results.append(("Amazon", f"https://www.amazon.es/s?k={encoded}"))

    if "noticias" in q.lower():
        results.append(("Google News", f"https://www.google.com/search?q={encoded}"))

    # fallback
    if not results:
        results.append(("Google", f"https://www.google.com/search?q={encoded}"))

    # -----------------------------
    # HTML SERP
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

    for title, link in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{link}" target="_blank" style="font-size:18px;">
                {title}
            </a>
            <div style="font-size:12px;color:gray;">
                {link}
            </div>
        </div>
        """

    html += """
        <br><br>
        <a href="/">← Volver</a>
    </body>
    </html>
    """

    return html


# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
