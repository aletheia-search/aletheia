from flask import Flask, request
import urllib.parse
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# -----------------------------
# MODELO IA
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
_ = model.encode(["warmup"])


# -----------------------------
# ÍNDICE EN MEMORIA
# -----------------------------
INDEX = []  # {title, url, text, embedding}


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">
        <h1>Aletheia Crawler</h1>

        <form action="/search">
            <input name="q" style="padding:10px;width:60%;" placeholder="Buscar...">
            <button>Buscar</button>
        </form>

        <br><br>

        <form action="/crawl">
            <input name="url" style="padding:10px;width:60%;" placeholder="URL a indexar">
            <button>Indexar</button>
        </form>

    </body>
    </html>
    """


# -----------------------------
# CRAWLER SIMPLE
# -----------------------------
@app.route("/crawl")
def crawl():
    url = request.args.get("url", "").strip()

    if not url:
        return "URL vacía"

    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else url
        text = " ".join([p.text for p in soup.find_all("p")])[:2000]

        emb = model.encode([text])[0]

        INDEX.append({
            "title": title,
            "url": url,
            "text": text,
            "emb": emb
        })

        return f"Indexado: {title}"

    except Exception as e:
        return f"Error: {str(e)}"


# -----------------------------
# SEARCH SEMÁNTICO EN ÍNDICE
# -----------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    q_emb = model.encode([q])[0]

    results = []

    for item in INDEX:
        sim = float(
            np.dot(q_emb, item["emb"]) /
            (np.linalg.norm(q_emb) * np.linalg.norm(item["emb"]))
        )

        if sim > 0.35:
            results.append({
                "title": item["title"],
                "url": item["url"],
                "score": sim
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['url']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="color:gray;">score: {round(r['score'],2)}</div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
