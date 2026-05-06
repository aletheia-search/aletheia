import os
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    engine = request.args.get("engine", "google")

    if not query:
        return redirect("/")

    if engine == "google":
        return redirect(f"https://www.google.com/search?q={query}")
    elif engine == "wikipedia":
        return redirect(f"https://es.wikipedia.org/wiki/{query}")
    elif engine == "bing":
        return redirect(f"https://www.bing.com/search?q={query}")
    else:
        return redirect(f"https://www.google.com/search?q={query}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
