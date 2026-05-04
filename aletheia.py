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

        <style>
            body {
                margin: 0;
                font-family: Arial;
                background: #f2f2f2;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }

            .box {
                background: white;
                padding: 25px;
                border-radius: 12px;
                width: 90%;
                max-width: 420px;
                text-align: center;
                box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            }

            input {
                width: 100%;
                padding: 12px;
                font-size: 16px;
                margin-bottom: 10px;
            }

            button {
                width: 100%;
                padding: 12px;
                font-size: 16px;
                background: black;
                color: white;
                border: none;
                border-radius: 6px;
            }
        </style>
    </head>

    <body>
        <div class="box">
            <h1>Aletheia</h1>
            <form action="/search">
                <input name="q" placeholder="Buscar en la web...">
                <button type="submit">Buscar</button>
            </form>
        </div>
    </body>
    </html>
    """


# -----------------------------
# INTENT ENGINE (REDIRECCIÓN DIRECTA)
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()

    if not q:
        return redirect("/")

    # -------------------------
    # ATAJOS DIRECTOS
    # -------------------------
    if q == "python":
        return redirect("https://www.python.org")

    if q == "wikipedia":
        return redirect("https://www.wikipedia.org")

    if q == "google":
        return redirect("https://www.google.com")

    if q == "bing":
        return redirect("https://www.bing.com")

    if q == "amazon":
        return redirect("https://www.amazon.es")

    # -------------------------
    # DEFAULT: GOOGLE SEARCH
    # -------------------------
    encoded = urllib.parse.quote(q)
    return redirect(f"https://www.google.com/search?q={encoded}")


# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    print("Aletheia FINAL MODE ONLINE")
    app.run(host="0.0.0.0", port=8080)
