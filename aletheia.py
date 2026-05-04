import urllib.parse
from flask import Flask, request

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
# SEARCH WEB ONLY
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()

    if not q:
        return "<a href='/'>Volver</a>"

    encoded = urllib.parse.quote(q)

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultados</title>
    </head>

    <body style="font-family:Arial;text-align:center;margin-top:60px;">

        <h2>Buscar: {q}</h2>

        <a href="https://www.google.com/search?q={encoded}" target="_blank">
            🔎 Google
        </a>
        <br><br>

        <a href="https://es.wikipedia.org/wiki/Special:Search?search={encoded}" target="_blank">
            📚 Wikipedia
        </a>
        <br><br>

        <a href="https://www.bing.com/search?q={encoded}" target="_blank">
            🌐 Bing
        </a>

        <br><br>
        <a href="/">Volver</a>

    </body>
    </html>
    """


# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    print("Aletheia WEB MODE ONLINE")
    app.run(host="0.0.0.0", port=8080)
