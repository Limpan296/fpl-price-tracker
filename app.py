from flask import Flask, jsonify, send_from_directory
import pandas as pd
import requests
import re

app = Flask(__name__, static_folder="static")

# GitHub repo
GITHUB_REPO = "Limpan296/fpl-price-tracker"

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/changes")
def get_changes():
    try:
        # 1. Hämta lista på filer i changes-mappen via GitHub API
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/changes"
        r = requests.get(url)
        files = r.json()

        # 2. Filtrera fram CSV-filer
        csv_files = [f["name"] for f in files if f["name"].endswith(".csv")]
        if not csv_files:
            return jsonify({})

        # 3. Sortera efter datum i filnamnet (YYYY-MM-DD) → nyaste först
        csv_files.sort(key=lambda x: re.search(r"\d{4}-\d{2}-\d{2}", x).group(), reverse=True)

        result = {}
        for file in csv_files:
            # Bygg raw-länk
            csv_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/changes/{file}"

            # Läs CSV
            df = pd.read_csv(csv_url)

            if "direction" not in df.columns:
                continue

            up = df[df["direction"] == "up"].to_dict(orient="records")
            down = df[df["direction"] == "down"].to_dict(orient="records")

            # extrahera datum
            date = re.search(r"\d{4}-\d{2}-\d{2}", file).group()
            result[date] = {"up": up, "down": down}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)