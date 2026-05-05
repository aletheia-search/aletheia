@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return home()

    import urllib.parse
    encoded = urllib.parse.quote(q)
    ql = q.lower()

    results = []

    # -----------------------------
    # REESCRITURA DE CONSULTA
    # -----------------------------
    def rewrite(query):
        q = query.lower()

        rules = [
            (["pc lento", "ordenador lento", "va lento"], "optimizar rendimiento ordenador"),
            (["internet no funciona", "sin internet", "wifi no va"], "solucionar problemas internet"),
            (["como", "cómo", "tutorial"], "guía explicativa"),
            (["arreglar", "solucionar"], "solución problema"),
            (["python"], "python programación tutorial"),
            (["comprar"], "mejores ofertas comprar"),
        ]

        for keys, replacement in rules:
            if any(k in q for k in keys):
                return replacement

        return query

    rq = rewrite(q)
    rq_encoded = urllib.parse.quote(rq)

    # -----------------------------
    # INTENCIÓN SIMPLE
    # -----------------------------
    def intent(query):
        if any(x in query for x in ["cómo", "como", "tutorial", "guía"]):
            return "educational"
        if any(x in query for x in ["comprar", "ofertas"]):
            return "commercial"
        if any(x in query for x in ["qué es", "que es"]):
            return "informational"
        return "general"

    t = intent(ql)

    # -----------------------------
    # BUILDER
    # -----------------------------
    def add(title, link, snippet, score):
        results.append({
            "title": title,
            "link": f"/go?url={urllib.parse.quote(link, safe='')}",
            "snippet": snippet,
            "score": score
        })

    # -----------------------------
    # RESULTADOS BASADOS EN CONSULTA REESCRITA
    # -----------------------------

    if t == "educational":
        add(
            "YouTube tutorial",
            f"https://www.youtube.com/results?search_query={rq_encoded}",
            f"Aprende sobre: {rq}",
            4
        )
        add(
            "Google cursos",
            f"https://www.google.com/search?q={rq_encoded}+curso",
            "Recursos educativos.",
            2
        )

    elif t == "commercial":
        add(
            "Amazon",
            f"https://www.amazon.es/s?k={rq_encoded}",
            f"Resultados para: {rq}",
            4
        )

    elif t == "informational":
        add(
            "Wikipedia",
            f"https://es.wikipedia.org/wiki/Special:Search?search={rq_encoded}",
            f"Información sobre: {rq}",
            4
        )

    else:
        add(
            "Google",
            f"https://www.google.com/search?q={rq_encoded}",
            f"Búsqueda: {rq}",
            2
        )

    # -----------------------------
    # ORDENAR
    # -----------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    # -----------------------------
    # HTML
    # -----------------------------
    html = f"""
    <html>
    <body style="font-family:Arial;margin:40px;">
        <h2>Resultados para: {q}</h2>
        <p style="color:gray;">Consulta reinterpretada: {rq}</p>
        <hr>
    """

    for r in results:
        html += f"""
        <div style="margin:20px 0;">
            <a href="{r['link']}" style="font-size:18px;">
                {r['title']}
            </a>
            <div style="font-size:13px;color:gray;">
                {r['snippet']}
            </div>
        </div>
        """

    html += """
        <br><a href="/">← Volver</a>
    </body>
    </html>
    """

    return html
