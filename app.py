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

# Price predictions-sida
@app.route("/pricepredictions")
def price_predictions():
    return send_from_directory("static", "predictions.html")

@app.route("/changes")
def price_changes():
    return send_from_directory("static", "pricechanges.html")

CHANGES_FOLDER = "changes"  # mappen med dina CSV-filer

@app.route("/api/changes")
def get_changes():
    try:
        files = [f for f in os.listdir(CHANGES_FOLDER) if f.endswith(".csv")]
        if not files:
            return jsonify({"days": []})

        # Sortera datum (YYYY-MM-DD) → nyast först
        def extract_date(name):
            m = re.search(r"\d{4}-\d{2}-\d{2}", name)
            return m.group() if m else ""

        files.sort(key=lambda x: extract_date(x), reverse=True)

        days = []
        for file in files:
            csv_path = os.path.join(CHANGES_FOLDER, file)
            df = pd.read_csv(csv_path)

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
