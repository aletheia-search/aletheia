from flask import Flask, request, jsonify
import os
from datetime import datetime
import json

app = Flask(__name__)

BASE = os.getcwd()
MEMORY_FILE = "aletheia_memory.json"


# =========================
# MEMORY
# =========================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "queries": [],
        "stats": {}
    }


def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


memory = load_memory()


def log_query(q):
    memory["queries"].append({
        "q": q,
        "time": datetime.now().isoformat()
    })

    memory["queries"] = memory["queries"][-200:]

    memory["stats"][q] = memory["stats"].get(q, 0) + 1

    save_memory()


# =========================
# CONTEXT
# =========================
def context():
    h = datetime.now().hour
    return "mañana" if h < 14 else "tarde" if h < 20 else "noche"


# =========================
# SEARCH ENGINE
# =========================
def search_files(q):

    results = []

    for root, _, files in os.walk(BASE):
        for f in files:

            if q.lower() in f.lower():
                results.append({
                    "name": f,
                    "path": os.path.join(root, f)
                })

                if len(results) >= 10:
                    return results

    return results


# =========================
# ENGINE
# =========================
def engine(q):

    q = q.lower().strip()

    log_query(q)

    return {
        "query": q,
        "context": context(),
        "results": search_files(q),
        "stats": memory["stats"]
    }


# =========================
# API
# =========================
@app.route("/ask")
def ask():

    q = request.args.get("q", "")

    if not q:
        return jsonify({
            "status": "ok",
            "context": context(),
            "total_queries": len(memory["queries"])
        })

    return jsonify(engine(q))


# =========================
# UI SIMPLE
# =========================
@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Aletheia</title>

<style>
body{
    margin:0;
    background:#0a0f1f;
    color:white;
    font-family:system-ui;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}

.wrapper{ width:800px; }

.title{
    font-size:48px;
    text-align:center;
    color:#38bdf8;
    margin-bottom:20px;
}

input{
    width:100%;
    padding:15px;
    border:none;
    border-radius:10px;
    background:#111827;
    color:white;
    font-size:16px;
}

.item{
    margin-top:6px;
    padding:10px;
    background:#0b1220;
    border-radius:8px;
}
</style>
</head>

<body>

<div class="wrapper">

<div class="title">Aletheia</div>

<input id="q" placeholder="buscar..." oninput="run()">

<div id="out"></div>

</div>

<script>
function run(){

 let q = document.getElementById("q").value;

 fetch("/ask?q=" + encodeURIComponent(q))
 .then(r=>r.json())
 .then(d=>{

     let o = document.getElementById("out");
     o.innerHTML = "";

     d.results.forEach(x=>{
         let div = document.createElement("div");
         div.className = "item";
         div.innerText = x.name + " — " + x.path;
         o.appendChild(div);
     });

 });
}
</script>

</body>
</html>
"""
# =========================
# START
# =========================
if __name__ == "__main__":
    print("Aletheia v11 ONLINE READY")
    app.run(host="0.0.0.0", port=5000)