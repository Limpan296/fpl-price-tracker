from flask import Flask, jsonify, send_from_directory, make_response
import pandas as pd
import re
import os
import requests

app = Flask(__name__, static_folder="static")

# URL till din CSV på GitHub (raw link!)
CSV_URL = "https://raw.githubusercontent.com/Limpan296/fpl-price-tracker/main/static/predictions.csv"
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# Price predictions-sida (hämtar alltid färsk CSV från GitHub)
@app.route("/api/predictions")
def predictions_api():
    try:
        # Hämta CSV från GitHub raw varje gång
        CSV_URL = "https://raw.githubusercontent.com/Limpan296/fpl-price-tracker/main/static/predictions.csv"
        df = pd.read_csv(CSV_URL)

        df_up = df[df["direction"] == "up"].head(10)
        df_down = df[df["direction"] == "down"].head(10)

        data = {
            "up": df_up.to_dict(orient="records"),
            "down": df_down.to_dict(orient="records")
        }

        response = make_response(jsonify(data))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    except Exception as e:
        response = make_response(jsonify({"error": str(e), "up": [], "down": []}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response
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