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


def read_pdf(path):
    try:
        import PyPDF2
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or "")
        return text.lower()
    except:
        return ""


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Aletheia Search</title>
        <style>
            body { font-family: Arial; text-align: center; margin-top: 80px; }
            input { width: 300px; padding: 10px; }
            button { padding: 10px; }
        </style>
    </head>
    <body>
        <h1>Aletheia</h1>
        <form action="/search">
            <input name="q" placeholder="Buscar documentos...">
            <button>Buscar</button>
        </form>
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

            content = ""

            if file.endswith(".txt"):
                content = read_txt(path)

            elif file.endswith(".pdf"):
                content = read_pdf(path)

            if q in content:
                results.append(file)

    html = f"""
    <h2>Resultados para: {q}</h2>
    <p>Total: {len(results)}</p>
    <ul>
    """

    for r in results:
        html += f"<li>{r}</li>"

    html += "</ul><br><a href='/'>Volver</a>"

    return html


if __name__ == "__main__":
    print("Aletheia ONLINE READY")
    app.run(host="0.0.0.0", port=8080)
