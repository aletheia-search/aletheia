from flask import Flask, request
import urllib.parse

app = Flask(__name__)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():from flask import Flask, request
import urllib.parse

app = Flask(__name__)


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


@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    encoded = urllib.parse.quote(q)

    def go(url):
        return f"<script>window.open('{url}','_blank');window.location='/'</script>"

    if "python" in q:
        return go("https://www.python.org")

    if "youtube" in q:
        return go(f"https://www.youtube.com/results?search_query={encoded}")

    if "wikipedia" in q:
        return go(f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}")

    if "amazon" in q or "comprar" in q:
        return go(f"https://www.amazon.es/s?k={encoded}")

    return go(f"https://www.google.com/search?q={encoded}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
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
# SEARCH ENGINE
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()

    if not q:
        return home()

    encoded = urllib.parse.quote(q)

    def go(url):
        # abre en nueva pestaña y vuelve a Aletheia
        return f"""
        <html>
        <script>
            window.open("{url}", "_blank");
            window.location = "/";
        </script>
        </html>
        """

    # -----------------------------
    # INTENCIONES
    # -----------------------------

    if "python" in q:
        if "tutorial" in q or "curso" in q:
            return go("https://www.youtube.com/results?search_query=python+tutorial")
        return go("https://www.python.org")

    if "wikipedia" in q or "que es" in q:
        return go(f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}")

    if "youtube" in q:
        return go(f"https://www.youtube.com/results?search_query={encoded}")

    if "amazon" in q or "comprar" in q:
        return go(f"https://www.amazon.es/s?k={encoded}")

    if "noticias" in q:
        return go(f"https://www.google.com/search?q={encoded}")

    return go(f"https://www.google.com/search?q={encoded}")


# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    print("Aletheia INTENT ENGINE v3 ONLINE")
    app.run(host="0.0.0.0", port=8080)
