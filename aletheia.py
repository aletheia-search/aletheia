import os
import unicodedata
from flask import Flask, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


# -----------------------------
# NORMALIZACIÓN (CLAVE)
# -----------------------------
def normalize(text):
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


# -----------------------------
# LECTURA TXT
# -----------------------------
def read_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return normalize(f.read())
    except:
        return ""


# -----------------------------
# LECTURA PDF (simple y segura)
# -----------------------------
def read_pdf(path):
    try:
        import PyPDF2
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return normalize(text)
    except:
        return ""


# -----------------------------
# INTERFAZ HOME (MÓVIL OK)
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
                text-align: center;
            }

            .box {
                background: white;
                padding: 25px;
                border-radius: 12px;
                width: 90%;
                max-width: 420px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            }

            h1 {
                margin-bottom: 20px;
            }

            input {
                width: 100%;
                padding: 12px;
                margin-bottom: 10px;
                font-size: 16px;
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
                <input name="q" placeholder="Buscar documentos...">
                <button type="submit">Buscar</button>
            </form>
        </div>
    </body>
    </html>
    """


# -----------------------------
# BÚSQUEDA
# -----------------------------
@app.route("/search")
def search():
    q = normalize(request.args.get("q", "").strip())

    if not q:
        return "<h3>Escribe algo para buscar</h3><a href='/'>Volver</a>"

    results = []

    if not os.path.exists(DATA_DIR):
        return "<h3>No existe carpeta data</h3>"

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            path = os.path.join(root, file)

            content = ""

            if file.endswith(".txt"):
                content = read_txt(path)

            elif file.endswith(".pdf"):
                content = read_pdf(path)

            if q in content:
                results.append(file)

    html = f"""
    <html>
    <head>
        <title>Resultados</title>
        <style>
            body {{
                font-family: Arial;
                background: #f2f2f2;
                margin: 0;
                text-align: center;
            }}

            .box {{
                background: white;
                margin: 10px auto;
                padding: 15px;
                width: 80%;
                max-width: 600px;
                border-radius: 8px;
            }}
        </style>
    </head>

    <body>
        <h2>Resultados para: {q}</h2>
        <p>Total: {len(results)}</p>
    """

    for r in results:
        html += f'<div class="box">{r}</div>'

    html += """
        <br><a href="/">Volver</a>
    </body>
    </html>
    """

    return html


# -----------------------------
# ARRANQUE
# -----------------------------
if __name__ == "__main__":
    print("Aletheia ONLINE READY")
    app.run(host="0.0.0.0", port=8080)
