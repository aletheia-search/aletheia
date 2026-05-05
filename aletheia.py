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
    # INTENCIONES CON PESO
    # -----------------------------

    if "python" in q:
        add("Python oficial", "https://www.python.org", 3)

        if "tutorial" in q or "curso" in q:
            add("Python tutorial YouTube", f"https://www.youtube.com/results?search_query=python+tutorial", 3)
        else:
            add("Python YouTube", f"https://www.youtube.com/results?search_query=python", 2)

    if "youtube" in q:
        add("YouTube", f"https://www.youtube.com/results?search_query={encoded}", 3)

    if "wikipedia" in q or "que es" in q:
        add("Wikipedia ES", f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}", 3)

    if "amazon" in q or "comprar" in q:
        add("Amazon", f"https://www.amazon.es/s?k={encoded}", 3)

    if "noticias" in q:
        add("Google News", f"https://www.google.com/search?q={encoded}", 2)

    # fallback
    if not results:
        add("Google", f"https://www.google.com/search?q={encoded}", 1)

    # -----------------------------
    # ORDENAR POR SCORE
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
            <div style="font-size:12px;color:gray;">
                score: {r['score']}
            </div>
        </div>
        """

    html += """
        <br><br>
        <a href="/">← Volver</a>
    </body>
    </html>
    """

    return html
