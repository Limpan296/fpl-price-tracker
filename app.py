from flask import Flask, jsonify, send_from_directory, make_response
import pandas as pd
import re
import os
import json

app = Flask(__name__, static_folder="static")

# GitHub repo (för referens, används inte längre för lokala CSV)
GITHUB_REPO = "Limpan296/fpl-price-tracker"

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# Price predictions-sida
@app.route("/api/predictions")
def predictions_api():
    df = pd.read_csv("static/predictions.csv")
    df_up = df[df["direction"] == "up"]
    df_down = df[df["direction"] == "down"]

    data = {
        "up": df_up.to_dict(orient="records"),
        "down": df_down.to_dict(orient="records")
    }

    # Skapa svar + no-cache headers
    response = make_response(jsonify(data))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


Varför kommer det funka med din nya kod?