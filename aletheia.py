import os
from flask import Flask, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def read_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except Exception as e:
        print("Error leyendo:", path, e)
        return ""


@app.route("/")
def home():
    return """
    <h1>Aletheia</h1>
    <form action="/search" method="get">
        <input name="q" placeholder="Buscar...">
        <button type="submit">Buscar</button>
    </form>
    """


@app.route("/search")
def search():
    try:
        q = request.args.get("q", "").lower()

        if not q:
            return "<h3>Escribe algo para buscar</h3>"

        results = []

        if not os.path.exists(DATA_DIR):
            return "<h3>No existe carpeta /data</h3>"

        for root, _, files in os.walk(DATA_DIR):
            for file in files:
                path = os.path.join(root, file)

                if file.endswith(".txt"):
                    content = read_txt(path)
                else:
                    continue

                if q in content:
                    results.append(file)

        html = f"<h2>Resultados para: {q}</h2>"
        html += f"<p>Total: {len(results)}</p><ul>"

        for r in results:
            html += f"<li>{r}</li>"

        html += "</ul><a href='/'>Volver</a>"

        return html

    except Exception as e:
        return f"<h3>Error interno: {e}</h3>"


if __name__ == "__main__":
    print("Aletheia ONLINE")
    app.run(host="0.0.0.0", port=8080)
