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


@app.route("/")
def home():
    return """
    <h1>Aletheia</h1>
    <form action="/search">
        <input name="q" placeholder="Buscar...">
        <button>Buscar</button>
    </form>
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
            else:
                continue

            if q in content:
                results.append({
                    "file": file,
                    "path": path
                })

    return {
        "query": q,
        "results": results
    }


if __name__ == "__main__":
    print("Aletheia ONLINE")
    app.run(host="0.0.0.0", port=8080)
