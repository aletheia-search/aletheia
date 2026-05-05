@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)

    results = []

    def add(title, link, score):
        results.append({"title": title, "link": link, "score": score})

    # -----------------------------
    # EXPANSIÓN DE CONSULTA
    # -----------------------------
    def expand(query):
        variations = [query]

        if "python" in query:
            variations += [
                "python tutorial",
                "aprender python",
                "python curso",
                "python básico",
                "python rápido"
            ]

        if "youtube" in query:
            variations += [query.replace("youtube", "").strip()]

        if "comprar" in query:
            variations += ["amazon " + query]

        if "que es" in query:
            variations += ["definición " + query]

        return list(set(variations))

    queries = expand(q)

    # -----------------------------
    # GENERACIÓN DE RESULTADOS
    # -----------------------------
    for item in queries:

        enc = urllib.parse.quote(item)

        if "python" in item:
            add("Python oficial", "https://www.python.org", 3)

        if "tutorial" in item:
            add("Python tutorial YouTube", f"https://www.youtube.com/results?search_query={enc}", 3)

        if "curso" in item:
            add("Curso Python YouTube", f"https://www.youtube.com/results?search_query={enc}", 3)

        if "youtube" in item:
            add("YouTube", f"https://www.youtube.com/results?search_query={enc}", 2)

        if "wikipedia" in item or "que es" in item:
            add("Wikipedia ES", f"https://es.wikipedia.org/wiki/Special:Search?search={enc}", 3)

        if "amazon" in item or "comprar" in item:
            add("Amazon", f"https://www.amazon.es/s?k={enc}", 3)

    # fallback
    if not results:
        add("Google", f"https://www.google.com/search?q={encoded}", 1)

    # -----------------------------
    # RANKING
    # -----------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    # -----------------------------
    # HTML
    # -----------------------------
    html = f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aletheia - {q}</title>
    </head>

    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['link']}" target="_blank" style="font-size:18px;">
                {r['title']}
            </a>
        </div>
        """

    html += """
        <br><br>
        <a href="/">← Volver</a>
    </body>
    </html>
    """

    return html
