from flask import Flask, jsonify, send_from_directory, make_response
import pandas as pd
import re
import os
import requests
#test
app = Flask(__name__, static_folder="static")

# URL till din CSV på GitHub (raw link!)
CSV_URL = "https://raw.githubusercontent.com/Limpan296/fpl-price-tracker/main/static/predictions.csv"

# Lägg in token via Render env vars
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# Price predictions-sida (hämtar alltid färsk CSV från GitHub)
@app.route("/api/predictions")
def predictions_api():
    try:
        # Hämta CSV från GitHub raw varje gång
        df = pd.read_csv(CSV_URL)

        # Mappa kolumner som tidigare
        columnMap = {
            "Spelare": "Player",
            "Lag": "Team",
            "Pris": "Price",
            "Ägd": "Owned",
            "Net transfers (GW)": "Transfers",
            "EffNet": "EffNet",
            "Score": "Score"
        }

        data = []
        for _, row in df.iterrows():
            obj = {}
            for k, v in row.items():
                mappedKey = columnMap.get(k, k)
                val = v
                if mappedKey in ["Price", "Owned", "Transfers", "EffNet", "Score"]:
                    try:
                        val = float(str(val).replace(",", "."))
                    except:
                        val = 0
                obj[mappedKey] = val
            data.append(obj)

        response = make_response(jsonify(data))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    except Exception as e:
        response = make_response(jsonify({"error": str(e), "data": []}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response


@app.route("/api/changes")
def changes_api():
    try:
        repo_api = "https://api.github.com/repos/Limpan296/fpl-price-tracker/contents/changes"
        r = requests.get(repo_api, headers=HEADERS)
        r.raise_for_status()
        files = r.json()

        # filtrera ut alla price_changes_YYYY-MM-DD.csv
        csv_files = [f["name"] for f in files if f["name"].startswith("price_changes_") and f["name"].endswith(".csv")]
        csv_files.sort(reverse=True)  # senaste först

        days = []
        for fname in csv_files[:7]:  # t.ex. hämta senaste 7 dagarna
            raw_url = f"https://raw.githubusercontent.com/Limpan296/fpl-price-tracker/main/changes/{fname}"
            try:
                df = pd.read_csv(raw_url)

                up = df[df["direction"] == "up"].to_dict(orient="records")
                down = df[df["direction"] == "down"].to_dict(orient="records")

                days.append({
                    "date": fname.replace("price_changes_", "").replace(".csv", ""),
                    "up": up,
                    "down": down
                })
            except Exception as e:
                print(f"Misslyckades läsa {raw_url}: {e}")

        # Se till att inget cacheas
        response = make_response(jsonify({"days": days}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    except Exception as e:
        return jsonify({"error": str(e), "days": []})


# Price changes-sida (oförändrad)
@app.route("/changes")
def price_changes():
    return send_from_directory("static", "pricechanges.html")


@app.route("/predictions")
def predictions():
    return send_from_directory("static", "predictions.html")


# Din gamla /api/changes-rutt kan ligga kvar om du vill
# ...

if __name__ == "__main__":
    app.run(debug=True)
