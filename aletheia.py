from flask import Flask, request, redirect
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
# INTENT ENGINE SIMPLE
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()

    if not q:
        return redirect("/")

    encoded = urllib.parse.quote(q)

    # -----------------------------
    # INTENCIONES DIRECTAS
    # -----------------------------

    # Python
    if "python" in q:
        if "tutorial" in q or "curso" in q:
            return redirect("https://www.youtube.com/results?search_query=python+tutorial")
        return redirect("https://www.python.org")

    # Wikipedia
    if "wikipedia" in q or "que es" in q:
        return redirect(f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}")

    # YouTube
    if "youtube" in q:
        return redirect(f"https://www.youtube.com/results?search_query={encoded}")

    # Amazon / compra
    if "comprar" in q or "precio" in q:
        return redirect(f"https://www.amazon.es/s?k={encoded}")

    # Noticias
    if "noticias" in q:
        return redirect(f"https://www.google.com/search?q={encoded}")

    # Google fallback
    return redirect(f"https://www.google.com/search?q={encoded}")


# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    print("Aletheia INTENT ENGINE v2 ONLINE")
    app.run(host="0.0.0.0", port=8080)
