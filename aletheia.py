import os
from flask import Flask, request
import PyPDF2

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

INDEX = []


def read_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except:
        return ""


def read_pdf(path):
    text = ""
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or "")
    except Exception as e:
        print("PDF error:", path, e)
    return text.lower()


def build_index():
    global INDEX
    INDEX = []

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            path = os.path.join(root, file)

            if file.endswith(".txt"):
                content = read_txt(path)

            elif file.endswith(".pdf"):
                content = read_pdf(path)

            else:
                continue

            INDEX.append({
                "file": file,
                "path": path,
                "content": content
            })

    print(f"[OK] Indexados: {len(INDEX)}")


@app.route("/")
def home():
    return """
    <h1>Aletheia</h1>
    <form action="/search">
        <input name="q">
        <button>Buscar</button>
    </form>
    """


@app.route("/search")
def search():
    q = request.args.get("q", "").lower()

    if not INDEX:
        build_index()

    results = []

    for doc in INDEX:
        if q in doc["content"]:
            results.append(doc)

    return {
        "query": q,
        "results": results
    }


if __name__ == "__main__":
    print("Aletheia iniciando...")
    app.run(host="0.0.0.0", port=8080)
