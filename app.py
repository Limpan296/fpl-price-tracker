from flask import Flask, jsonify, send_from_directory
import pandas as pd
import requests

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/changes")
def get_changes():
    # Hämta lista över filer i changes-mappen via GitHub API
    repo_api_url = "https://api.github.com/repos/Limpan296/fpl-price-tracker/contents/changes"
    r = requests.get(repo_api_url)
    files = r.json()

    # Filtrera ut CSV-filer
    csv_files = [f for f in files if f["name"].endswith(".csv")]
    if not csv_files:
        return jsonify({"up": [], "down": []})

    # Sortera på filnamn (där datumet är med i namnet)
    latest_file = sorted(csv_files, key=lambda x: x["name"])[-1]

    # Hämta raw-länken
    csv_url = latest_file["download_url"]

    # Läs CSV
    df = pd.read_csv(csv_url)

    # Använd rätt kolumnnamn
    up = df[df["direction"] == "up"].to_dict(orient="records")
    down = df[df["direction"] == "down"].to_dict(orient="records")

    return jsonify({"up": up, "down": down})

if __name__ == "__main__":
    app.run(debug=True)