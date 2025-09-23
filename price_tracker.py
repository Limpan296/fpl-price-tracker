import requests
import pandas as pd
import os
from datetime import datetime
import tweepy


HISTORY_FILE = "fpl_price_history.csv"
CHANGES_DIR = "changes"

os.makedirs(CHANGES_DIR, exist_ok=True)

# ---- Twitter API credentials ----
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")

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

# ---- Funktion för att posta tweets ----
def post_tweets(df, title, header_emoji, line_emoji):
    if df.empty:
        return

    header_base = f"Price {title}! {header_emoji} ({len(df)}) #FPL"
    rows = [f"{line_emoji} {row['web_name']} ({row['team']}) - £{row['new_price']:.1f}\n"
            for _, row in df.iterrows()]

    # Bygg tweets (lägg rader tills max längd nås)
    tweets = []
    current = ""
    for line in rows:
        if len(current) + len(line) <= 250 - len(header_base) - 6:  # plats för (X/n)
            current += line
        else:
            tweets.append(current.strip())
            current = line
    if current:
        tweets.append(current.strip())

    total = len(tweets)

    # Skicka tweets
    for i, body in enumerate(tweets, start=1):
        if total > 1:
            header = f"{header_base} ({i}/{total})"
        else:
            header = header_base
        text = f"{header}\n{body}".strip()

        try:
            #client.create_tweet(text=text)
            print(text)
            print(f"Skapade tweet {i}/{total} för {title}")
        except Exception as e:
            print(f"Kunde inte skapa tweet {i}/{total} för {title}:", e)

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

        post_tweets(risers, "Risers", "📈", "🟢")
        post_tweets(fallers, "Fallers", "📉", "🔴")

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