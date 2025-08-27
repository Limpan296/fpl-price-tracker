from flask import Flask, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/changes")
def get_changes():
    # Hämta senaste CSV-filen
    files = sorted(os.listdir("changes"))
    if not files:
        return jsonify({"up": [], "down": []})

    latest = os.path.join("changes", files[-1])
    df = pd.read_csv(latest)

    # Dela upp uppgångar och nedgångar
    up = df[df["change"] == "up"].to_dict(orient="records")
    down = df[df["change"] == "down"].to_dict(orient="records")

    return jsonify({"up": up, "down": down})

if __name__ == "__main__":
    app.run(debug=True)
