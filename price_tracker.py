import requests
import pandas as pd
import os
from datetime import datetime

HISTORY_FILE = "fpl_price_history.csv"
CHANGES_DIR = "changes"

os.makedirs(CHANGES_DIR, exist_ok=True)

# Hämta data
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
r = requests.get(url).json()
players = r["elements"]

df = pd.DataFrame(players)[["id", "web_name", "team", "now_cost"]]
df["price"] = df["now_cost"] / 10
df = df.drop(columns=["now_cost"])

today = datetime.utcnow().strftime("%Y-%m-%d")

# Jämför med föregående snapshot
if os.path.exists(HISTORY_FILE):
    prev = pd.read_csv(HISTORY_FILE)
    merged = df.merge(prev, on="id", suffixes=("", "_prev"))

    # Hitta spelare vars pris ändrats
    changes = merged[merged["price"] != merged["price_prev"]].copy()
    changes["date"] = today
    changes["change"] = changes["price"] - changes["price_prev"]

    if not changes.empty:
        # Prisuppgång
        up = changes[changes["change"] > 0].copy()
        if not up.empty:
            out_file_up = os.path.join(CHANGES_DIR, f"price_up_{today}.csv")
            up.to_csv(out_file_up, index=False)
            print(f"{len(up)} players increased in price saved to {out_file_up}")

        # Prisnedgång
        down = changes[changes["change"] < 0].copy()
        if not down.empty:
            out_file_down = os.path.join(CHANGES_DIR, f"price_down_{today}.csv")
            down.to_csv(out_file_down, index=False)
            print(f"{len(down)} players decreased in price saved to {out_file_down}")

        # Visa alla ändringar i terminalen
        print(changes[["web_name", "price_prev", "price", "change"]])
    else:
        print("No price changes today.")

else:
    print("No history found. Creating initial snapshot.")

# Uppdatera snapshot
df.to_csv(HISTORY_FILE, index=False)
