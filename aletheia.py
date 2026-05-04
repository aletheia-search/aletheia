import os
from flask import Flask, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def read_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except:
        return ""


def clean_filename(name):
    # elimina números iniciales tipo "4 - archivo.pdf"
    parts = name.split(" ", 1)
    if len(parts) > 1 and parts[0].replace(".", "").isdigit():
        return parts[1]
    return name


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Aletheia Search</title>
        <style>
            body {
                font-family: Arial;
                background: #f4f4f4;
                margin: 0;
                padding: 0;
                text-align: center;
            }

            .container {
                margin-top: 120px;
            }

            h1 {
                font-size: 40px;
                margin-bottom: 20px;
            }

            input {
                width: 400px;
                padding: 12px;
                font-size: 16px;
            }

            button {
                padding: 12px 20px;
                font-size: 16px;
                cursor: pointer;
            }

            .result {
                background: white;
                margin: 10px auto;
                padding: 10px;
                width: 60%;
                border-radius: 8px;
                text-align: left;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Aletheia</h1>
            <form action="/search">
                <input name="q" placeholder="Buscar documentos...">
                <button type="submit">Buscar</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/search")
def search():
    q = request.args.get("q", "").lower()

    results = []

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            path = os.path.join(root, file)

            if file.endswith(".txt"):
                content = read_txt(path)

                if q in content:
                    results.append(clean_filename(file))

    html = f"""
    <html>
    <head>
        <title>Resultados</title>
        <style>
            body {{ font-family: Arial; background: #f4f4f4; }}
            .box {{
                background: white;
                margin: 10px auto;
                padding: 15px;
                width: 70%;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <h2 style="text-align:center;">Resultados para: {q}</h2>
        <p style="text-align:center;">Total: {len(results)}</p>
    """

    for r in results:
        html += f'<div class="box">{r}</div>'

    html += """
        <div style="text-align:center; margin-top:20px;">
            <a href="/">Volver</a>
        </div>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    print("Aletheia UI READY")
    app.run(host="0.0.0.0", port=8080)
