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
teams = {t["id"]: t["name"] for t in r["teams"]}  # team id → namn

df = pd.DataFrame(players)[["id", "web_name", "team", "now_cost"]]
df["price"] = df["now_cost"] / 10
df["team"] = df["team"].map(teams)  # byt team-id till namn
df = df.drop(columns=["now_cost"])

today = datetime.utcnow().strftime("%Y-%m-%d")

# Jämför med föregående snapshot
if os.path.exists(HISTORY_FILE):
    prev = pd.read_csv(HISTORY_FILE)
    merged = df.merge(prev, on="id", suffixes=("", "_prev"))

    # hitta ändringar
    changes = merged[merged["price"] != merged["price_prev"]].copy()
    if not changes.empty:
        changes["new_price"] = changes["price"]
        changes["direction"] = changes.apply(
            lambda row: "up" if row["new_price"] > row["price_prev"] else "down",
            axis=1
        )
        changes["date"] = today

        # välj bara relevanta kolumner
        changes = changes[["date", "web_name", "team", "price_prev", "new_price", "direction"]]

        out_file = os.path.join(CHANGES_DIR, f"price_changes_{today}.csv")
        changes.to_csv(out_file, index=False)
        print(f"{len(changes)} price changes saved to {out_file}")
    else:
        print("No price changes today.")
else:
    print("No history found. Creating initial snapshot.")

# Uppdatera snapshot
df.to_csv(HISTORY_FILE, index=False)
