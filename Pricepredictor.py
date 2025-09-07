import requests
import pandas as pd
import numpy as np

# =========================
#  HYPERPARAMETERS
# =========================
RISE_ABS_THRESHOLD = 90000
FALL_OWNERS_PCT = 0.08
CHIP_DOWNWEIGHT = 0.88
MIN_OWNERS_PCT = 0.75     # minst 0,75% ägande
MIN_ABS_NET_TRANSFERS = 1500

FLAG_MULTIPLIER_RISE = {"a":1.00,"d":1.20,"i":1.35,"s":1.35,"u":1.35}
FLAG_MULTIPLIER_FALL = {"a":1.00,"d":1.20,"i":1.40,"s":1.40,"u":1.40}

# =========================
#  FETCH DATA
# =========================
URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
data = requests.get(URL).json()

df = pd.DataFrame(data["elements"])
teams = {t["id"]: t["name"] for t in data["teams"]}
df["team_name"] = df["team"].map(teams)
df["price"] = df["now_cost"] / 10.0
df["selected_by_percent"] = pd.to_numeric(df["selected_by_percent"], errors="coerce").fillna(0.0)
df["owners"] = (df["selected_by_percent"] / 100.0) * data.get("total_players", 10000000)

df["net_transfers"] = df["transfers_in_event"] - df["transfers_out_event"]
df["effective_net"] = df["net_transfers"] * CHIP_DOWNWEIGHT

status = df["status"].fillna("a").str.lower()
rise_mult = status.map(FLAG_MULTIPLIER_RISE).fillna(1.0)
fall_mult = status.map(FLAG_MULTIPLIER_FALL).fillna(1.0)

df["rise_threshold"] = RISE_ABS_THRESHOLD * rise_mult
df["fall_threshold"] = (df["owners"] * FALL_OWNERS_PCT) * fall_mult

df["net_in"] = df["effective_net"].clip(lower=0)
df["net_out"] = (-df["effective_net"]).clip(lower=0)

df["progress_rise"] = np.where(df["rise_threshold"] > 0, df["net_in"] / df["rise_threshold"], 0.0)
df["progress_fall"] = np.where(df["fall_threshold"] > 0, df["net_out"] / df["fall_threshold"], 0.0)

# =========================
#  FILTER & EXCLUDE
# =========================
mask = (df["selected_by_percent"] >= MIN_OWNERS_PCT) & (df["net_transfers"].abs() >= MIN_ABS_NET_TRANSFERS)
df_filt = df.loc[mask].copy()

# =========================
#  SCORE LOGIC
# =========================
df_filt["adjusted_progress_rise"] = df_filt["progress_rise"] * (df_filt["selected_by_percent"]/10)
df_filt["adjusted_progress_fall"] = df_filt["progress_fall"] * (df_filt["selected_by_percent"]/10)

df_filt["score_rise"] = df_filt["progress_rise"]*0.6 + df_filt["adjusted_progress_rise"]/100*0.4
df_filt["score_fall"] = -(df_filt["progress_fall"]*0.6 + df_filt["adjusted_progress_fall"]/100*0.4)  # NEGATIV score

# =========================
#  FORMAT ALL PLAYERS
# =========================
def format_players(df):
    return df.assign(
        Pris=lambda x: x["price"].round(1),
        Ägd=lambda x: x["selected_by_percent"].round(2),
        EffNet=lambda x: x["effective_net"].astype(int),
        Score=lambda x: np.where(
            x["score_rise"] > 0, (100*x["score_rise"]).round(1),
            (100*x["score_fall"]).round(1)
        )
    ).rename(columns={
        "web_name":"Spelare","team_name":"Lag",
        "net_transfers":"Net transfers (GW)"
    })[["Spelare","Lag","Pris","Ägd","Net transfers (GW)","EffNet","Score"]]

df_all = format_players(df_filt)

# =========================
#  SAVE CSV
# =========================
output_file = "static/predictions.csv"
df_all.to_csv(output_file, index=False, encoding="utf-8")
print(f"\n✅ Predictions sparade till {output_file}")
