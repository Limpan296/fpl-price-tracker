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
        # 1) Lista filer i changes/ via GitHub API
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/changes"
        r = requests.get(url)
        r.raise_for_status()
        files = r.json()

        # 2) Endast CSV
        csv_files = [f["name"] for f in files if f["name"].endswith(".csv")]
        if not csv_files:
            return jsonify({"days": []})

        # 3) Sortera datum i filnamn (YYYY-MM-DD) → NYAST FÖRST
        def extract_date(name):
            m = re.search(r"\d{4}-\d{2}-\d{2}", name)
            return m.group() if m else ""
        csv_files.sort(key=lambda x: extract_date(x), reverse=True)

        # 4) Bygg en ordnad lista
        days = []
        for file in csv_files:
            csv_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/changes/{file}"
            df = pd.read_csv(csv_url)

            if "direction" not in df.columns:
                continue

            up = df[df["direction"] == "up"].to_dict(orient="records")
            down = df[df["direction"] == "down"].to_dict(orient="records")

            date = extract_date(file)
            days.append({
                "date": date,
                "up": up,
                "down": down,
                "file": file
            })

        return jsonify({"days": days})

    except Exception as e:
        return jsonify({"error": str(e), "days": []})

if __name__ == "__main__":
    app.run(debug=True)