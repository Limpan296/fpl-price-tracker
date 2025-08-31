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

# Price changes-sida
@app.route("/changes")
def price_changes():
    return send_from_directory("static", "pricechanges.html")

@app.route("/predictions")
def predictions():
    return send_from_directory("static", "predictions.html")

CHANGES_FOLDER = "changes"  # mappen med dina CSV-filer

@app.route("/api/changes")
def get_changes():
    try:
        files = [f for f in os.listdir(CHANGES_FOLDER) if f.endswith(".csv")]
        print("Found CSV files:", files)  # DEBUG: vilka filer finns i mappen

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

            # DEBUG: visa kolumnerna och första raderna
            print(f"\nProcessing file: {file}")
            print("Columns:", df.columns.tolist())
            print(df.head())

            # Rensa kolumnnamn: små bokstäver och inga extra mellanslag
            df.columns = [c.strip().lower() for c in df.columns]

            if "direction" not in df.columns:
                print(f"Skipping {file}: no 'direction' column found")
                continue

            up = df[df["direction"] == "up"].to_dict(orient="records")
            down = df[df["direction"] == "down"].to_dict(orient="records")

            print(f"Rows up: {len(up)}, Rows down: {len(down)}")  # DEBUG

            date = extract_date(file)
            days.append({
                "date": date,
                "up": up,
                "down": down,
                "file": file
            })

        print(f"Returning {len(days)} days")  # DEBUG
        response = make_response(jsonify({"days": days}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    except Exception as e:
        print("Error in get_changes():", e)
        response = make_response(jsonify({"error": str(e), "days": []}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

if __name__ == "__main__":
    app.run(debug=True)