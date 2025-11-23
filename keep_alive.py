# keep_alive.py
from flask import Flask, render_template_string
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot activo"

@app.route("/wiki")
def wiki():
    try:
        with open("public/html/wiki.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Wiki no encontrada</h1>"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

