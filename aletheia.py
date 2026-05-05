@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    encoded = urllib.parse.quote(q)
    ql = q.lower()

    results = []

    def score(base, match_strength, type_bonus):
        return base + match_strength + type_bonus

    def add(title, url, snippet, base, match, typ):
        results.append({
            "title": title,
            "link": f"/go?url={urllib.parse.quote(url, safe='')}",
            "snippet": snippet,
            "score": score(base, match, typ)
        })

    # -----------------------------
    # INTELIGENCIA LIGERA (SIN MEMORIA)
    # -----------------------------

    def match(q, keyword):
        return 3 if keyword in q else 0

    # Python
    add(
        "Python oficial",
        "https://www.python.org",
        "Lenguaje de programación de alto nivel.",
        3,
        match(ql, "python"),
        2
    )

    if "tutorial" in ql or "aprender" in ql:
        add(
            "Python tutorial YouTube",
            f"https://www.youtube.com/results?search_query=python+tutorial",
            "Aprende Python paso a paso.",
            2,
            match(ql, "python"),
            2
        )

    # YouTube
    if "youtube" in ql or "video" in ql:
        add(
            "YouTube",
            f"https://www.youtube.com/results?search_query={encoded}",
            "Plataforma de vídeos.",
            2,
            match(ql, "youtube"),
            1
        )

    # Wikipedia
    if "wikipedia" in ql or "que es" in ql:
        add(
            "Wikipedia",
            f"https://es.wikipedia.org/wiki/Special:Search?search={encoded}",
            "Enciclopedia libre.",
            3,
            match(ql, "wikipedia"),
            2
        )

    # Amazon
    if "amazon" in ql or "comprar" in ql:
        add(
            "Amazon",
            f"https://www.amazon.es/s?k={encoded}",
            "Tienda online.",
            3,
            match(ql, "amazon"),
            2
        )

    # Noticias (RSS en vivo, sin guardar)
    if "noticias" in ql:
        import feedparser
        feed = feedparser.parse(
            f"https://news.google.com/rss/search?q={encoded}&hl=es&gl=ES&ceid=ES:es"
        )

        for e in feed.entries[:5]:
            results.append({
                "title": e.title,
                "link": f"/go?url={urllib.parse.quote(e.link, safe='')}",
                "snippet": "Noticia en tiempo real",
                "score": 3
            })

    # fallback
    if not results:
        add(
            "Google",
            f"https://www.google.com/search?q={encoded}",
            "Búsqueda general.",
            1,
            0,
            0
        )

    # -----------------------------
    # DEDUPLICACIÓN
    # -----------------------------
    seen = set()
    unique = []

    for r in results:
        if r["link"] not in seen:
            unique.append(r)
            seen.add(r["link"])

    # -----------------------------
    # RANKING FINAL
    # -----------------------------
    unique.sort(key=lambda x: x["score"], reverse=True)

    # -----------------------------
    # HTML
    # -----------------------------
    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <hr>
    """

    for r in unique:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['link']}" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="font-size:13px;color:gray;">
                {r['snippet']} (score: {r['score']})
            </div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html
