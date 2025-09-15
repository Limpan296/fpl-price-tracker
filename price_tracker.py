import requests
import pandas as pd
import os
from datetime import datetime
import tweepy

HISTORY_FILE = "fpl_price_history.csv"
CHANGES_DIR = "changes"

os.makedirs(CHANGES_DIR, exist_ok=True)

# ---- Twitter API credentials ----
ACCESS_TOKEN = '1967616675978625024-n2YIL5W6AQ3nObeQKYLb6AvAwPtYed'
ACCESS_TOKEN_SECRET = 'ph0Trht9Q8D9hTmTsqnv4prfmlfXGs83GrGNWwZJt4dpX'
BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAALnY4AEAAAAAR%2FFRM3qaHxEhDFRya8QlJVl%2Fjuc%3D99ltkGVVX7U0KjDLFBj98k9VV3wWRLZg0j1AOjtaPCQiyeMraJ'
API_KEY = 'wtVHDjccS0IgPP0d9HkabiK9j'
API_SECRET = 'U42Htoz4EcwRkXSFhZTIRQBJBrfp4gcevy9qJ0BIlMlvGX0UtH'

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# ---- Hämta FPL-data ----
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
r = requests.get(url).json()
players = r["elements"]
teams = {t["id"]: t["name"] for t in r["teams"]}  # team id → namn

df = pd.DataFrame(players)[["id", "web_name", "team", "now_cost"]]
df["price"] = df["now_cost"] / 10.0  # säkerställ float
df["team"] = df["team"].map(teams)
df = df.drop(columns=["now_cost"])

today = datetime.utcnow().strftime("%Y-%m-%d")

# ---- Jämför med föregående snapshot ----
if os.path.exists(HISTORY_FILE):
    prev = pd.read_csv(HISTORY_FILE)
    merged = df.merge(prev, on="id", suffixes=("", "_prev"))

    # Hitta ändringar
    changes = merged[merged["price"] != merged["price_prev"]].copy()
    if not changes.empty:
        changes["new_price"] = changes["price"].values  # korrekt new_price
        changes["direction"] = changes.apply(
            lambda row: "up" if row["new_price"] > row["price_prev"] else "down", axis=1
        )
        changes["date"] = today

        # välj relevanta kolumner
        changes = changes[["date", "web_name", "team", "price_prev", "new_price", "direction"]]

        # spara CSV
        out_file = os.path.join(CHANGES_DIR, f"price_changes_{today}.csv")
        changes.to_csv(out_file, index=False)
        print(f"{len(changes)} price changes saved to {out_file}")

        print("Preview changes:")
        print(changes.head())  # kontrollera att new_price ser korrekt ut

        # ---- Skapa tweets ----
        risers = changes[changes["direction"] == "up"]
        fallers = changes[changes["direction"] == "down"]

        # Risers
        if not risers.empty:
            riser_text = f"Price Risers! 💹 ({len(risers)})\n"
            for _, row in risers.iterrows():
                riser_text += f"🟢 {row['web_name']} ({row['team']}) - £{row['new_price']:.1f}\n"
            try:
                client.create_tweet(text=riser_text.strip())
                print("Skapade tweet för Risers")
            except Exception as e:
                print("Kunde inte skapa tweet för Risers:", e)

        # Fallers
        if not fallers.empty:
            faller_text = f"Price Fallers! 🔻 ({len(fallers)})\n"
            for _, row in fallers.iterrows():
                faller_text += f"🔴 {row['web_name']} ({row['team']}) - £{row['new_price']:.1f}\n"
            try:
                client.create_tweet(text=faller_text.strip())
                print("Skapade tweet för Fallers")
            except Exception as e:
                print("Kunde inte skapa tweet för Fallers:", e)

    else:
        print("No price changes today.")
        # Skapa en tom fil med rubriker
        out_file = os.path.join(CHANGES_DIR, f"price_changes_{today}_no_changes.csv")
        empty_df = pd.DataFrame(columns=["date", "web_name", "team", "price_prev", "new_price", "direction"])
        empty_df.to_csv(out_file, index=False)
        print(f"No changes file saved to {out_file}")

        # Tweet om inga ändringar
        try:
            client.create_tweet(text=f"No price changes today: {today}")
            print("Tweet: No price changes posted")
        except Exception as e:
            print("Kunde inte skapa tweet:", e)
else:
    print("No history found. Creating initial snapshot.")

# ---- Uppdatera snapshot ----
df.to_csv(HISTORY_FILE, index=False)
print("Uppdaterade history-filen")
