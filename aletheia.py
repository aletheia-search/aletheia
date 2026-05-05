import json
import numpy as np
from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer

INDEX_FILE = "store/index.json"
USERS_FILE = "store/users.json"
CACHE_FILE = "store/cache.json"

app = Flask(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

# =========================
# IO
# =========================
def load(path, default):
    try:
        return json.load(open(path,"r",encoding="utf-8"))
    except:
        return default

def save(path, data):
    json.dump(data, open(path,"w",encoding="utf-8"), indent=2)

# =========================
# EMBEDDING
# =========================
def embed(t):
    v = model.encode([t])[0]
    return v / (np.linalg.norm(v) + 1e-9)

def cosine(a,b):
    a=np.array(a); b=np.array(b)
    return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))

# =========================
# USER MODEL (MEJORADO)
# =========================
def get_user(uid):
    users = load(USERS_FILE, {})
    if uid not in users:
        users[uid] = {
            "clicks": {},
            "domains": {},
            "types": {}
        }
    return users[uid], users

def update_user(uid,user,users):
    users[uid]=user
    save(USERS_FILE,users)

# =========================
# RANKING INTELIGENTE
# =========================
def rerank(results, user):
    for r in results:
        url = r["url"]

        domain = url.split("/")[2] if "://" in url else url

        # señales de usuario
        domain_pref = user["domains"].get(domain, 0)
        click_pref = user["clicks"].get(url, 0)

        # boost compuesto
        r["score"] += domain_pref * 0.08
        r["score"] += click_pref * 0.05

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# CLUSTER SIMPLE
# =========================
def cluster(results):
    clusters = []

    for r in results:
        placed = False

        for c in clusters:
            if cosine(r["emb"], c[0]["emb"]) > 0.85:
                c.append(r)
                placed = True
                break

        if not placed:
            clusters.append([r])

    # flatten (manteniendo mejor de cada cluster)
    out = []
    for c in clusters:
        best = max(c, key=lambda x: x["score"])
        out.append(best)

    return out

# =========================
# SEARCH
# =========================
def search(q,user):
    index = load(INDEX_FILE, [])
    qv = embed(q)

    results=[]

    for i in index:
        score = cosine(qv,i["emb"])

        results.append({
            "title": i["title"],
            "url": i["url"],
            "desc": i["text"][:120],
            "score": score,
            "emb": i["emb"]
        })

    # fase 1: clustering
    results = cluster(results)

    # fase 2: rerank personalizado
    results = rerank(results,user)

    return results[:10]

# =========================
# FRONTEND
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aletheia v16</title>
<style>
body{background:#0f0f12;color:white;font-family:Arial}
input{width:60%;padding:14px;margin:20px}
.card{background:#1c1c22;margin:10px;padding:10px;cursor:pointer;border-radius:10px}
</style>
</head>
<body>

<input id="q" placeholder="Buscar..." />
<div id="r"></div>

<script>
async function go(q){
    const r=await fetch("/search?q="+q);
    const d=await r.json();

    let box=document.getElementById("r");
    box.innerHTML="";

    d.results.forEach(x=>{
        let div=document.createElement("div");
        div.className="card";
        div.innerHTML="<b>"+x.title+"</b><br>"+x.desc;
        div.onclick=()=>window.open(x.url);
        box.appendChild(div);
    });
}

document.getElementById("q").onkeydown=e=>{
    if(e.key==="Enter") go(e.target.value);
}
</script>

</body>
</html>
"""

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return HTML

@app.route("/search")
def search_route():
    q=request.args.get("q","")
    uid=request.args.get("user","default")

    user, users = get_user(uid)

    return jsonify({
        "results": search(q,user)
    })

@app.route("/click")
def click():
    uid=request.args.get("user","default")
    url=request.args.get("url")

    user, users = get_user(uid)

    domain = url.split("/")[2] if "://" in url else url

    user["clicks"][url]=user["clicks"].get(url,0)+1
    user["domains"][domain]=user["domains"].get(domain,0)+1

    update_user(uid,user,users)

    return jsonify({"ok":True})

if __name__=="__main__":
    print("Aletheia v16 RANKING+CLUSTER ONLINE")
    app.run(host="0.0.0.0",port=8080)
