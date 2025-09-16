import requests
import pandas as pd
import numpy as np

# =========================
#  HYPERPARAMETERS
# =========================
RISE_ABS_THRESHOLD = 90000
FALL_OWNERS_PCT = 0.08
CHIP_DOWNWEIGHT_DEFAULT = 0.88
GW_CHIP_DOWNWEIGHT = {1: 0.95, 2: 0.70, 3: 0.80, 4: 0.85}

MIN_OWNERS_PCT = 0.75     # minst 0,75% ägande
MIN_ABS_NET_TRANSFERS = 1500

FLAG_MULTIPLIER_RISE = {"a":1.00,"d":1.20,"i":1.35,"s":1.35,"u":1.35}
FLAG_MULTIPLIER_FALL = {"a":1.00,"d":1.20,"i":1.40,"s":1.40,"u":1.40}

GW_DECAY = 0.85

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
df["cost_change_event"] = df["cost_change_event"].fillna(0)  # GW-prisändring

current_gw = data.get("events", [{}])[0].get("id", 1)
chip_weight = GW_CHIP_DOWNWEIGHT.get(current_gw, CHIP_DOWNWEIGHT_DEFAULT)
df["effective_net"] = df["net_transfers"] * chip_weight * GW_DECAY

# =========================
#  MULTIPLIERS & ADJUSTMENTS
# =========================
status = df["status"].fillna("a").str.lower()
rise_mult = status.map(FLAG_MULTIPLIER_RISE).fillna(1.0)
fall_mult = status.map(FLAG_MULTIPLIER_FALL).fillna(1.0)

df["rise_threshold"] = RISE_ABS_THRESHOLD * rise_mult
df["fall_threshold"] = (df["owners"] * FALL_OWNERS_PCT) * fall_mult
df["owners"] = df["owners"].clip(lower=1)

df["net_in"] = df["effective_net"].clip(lower=0)
df["net_out"] = (-df["effective_net"]).clip(lower=0)

df["progress_rise"] = np.where(df["rise_threshold"]>0, df["net_in"]/df["rise_threshold"],0.0)
df["progress_fall"] = np.where(df["fall_threshold"]>0, df["net_out"]/df["fall_threshold"],0.0)

# =========================
#  RISERS
# =========================
mask_rise = (df["selected_by_percent"] >= MIN_OWNERS_PCT) & (df["net_transfers"] >= MIN_ABS_NET_TRANSFERS)
df_risers = df.loc[mask_rise].copy()

# Lägg till GW-prisändring: större prisstegring → mindre chans att öka mer
df_risers["price_factor"] = np.clip(1 - df_risers["cost_change_event"]/2, 0.5, 1.0)
df_risers["score_rise"] = (df_risers["progress_rise"] * df_risers["price_factor"] * 0.6 +
                           (df_risers["selected_by_percent"]/100)*0.4)
df_risers["score_rise"] = np.clip(df_risers["score_rise"], 0, 1.0)

# =========================
#  FALLERS (originallogik)
# =========================
mask = (df["selected_by_percent"] >= MIN_OWNERS_PCT) & (df["net_transfers"].abs() >= MIN_ABS_NET_TRANSFERS)
df_filt = df.loc[mask].copy()

df_filt["net_in"] = df_filt["effective_net"].clip(lower=0)
df_filt["net_out"] = (-df_filt["effective_net"]).clip(lower=0)

df_filt["progress_fall"] = np.where(df_filt["fall_threshold"] > 0, df_filt["net_out"]/df_filt["fall_threshold"], 0.0)
df_filt["adjusted_progress_fall"] = df_filt["progress_fall"] * (df_filt["selected_by_percent"]/10)
df_filt["score_fall"] = -(df_filt["progress_fall"]*0.6 + df_filt["adjusted_progress_fall"]/100*0.4)

df_fallers = df_filt[df_filt["net_transfers"] < 0].copy()

# =========================
#  FORMAT PLAYERS
# =========================
def format_players(df, score_col):
    return df.assign(
        Pris=lambda x: x["price"].round(1),
        Ägd=lambda x: x["selected_by_percent"].round(2),
        EffNet=lambda x: x["effective_net"].astype(int),
        Score=lambda x: (100*x[score_col]).round(1)
    ).rename(columns={
        "web_name":"Spelare","team_name":"Lag",
        "net_transfers":"Net transfers (GW)"
    })[["Spelare","Lag","Pris","Ägd","Net transfers (GW)","EffNet","Score"]]

df_all_risers = format_players(df_risers, "score_rise")
df_all_fallers = format_players(df_fallers, "score_fall")

df_all = pd.concat([df_all_risers, df_all_fallers], ignore_index=True)
output_file = "static/predictions.csv"
df_all.to_csv(output_file, index=False, encoding="utf-8")
print(f"\n✅ Predictions sparade till {output_file}")

# =========================
#  PRINT TOP 10
# =========================
top_risers = df_all_risers.sort_values("Score", ascending=False).head(10)
top_fallers = df_all_fallers.sort_values("Score").head(10)

print("\n🔼 Top 10 Risers:")
print(top_risers[["Spelare","Lag","Score","Pris","Ägd"]])

print("\n🔽 Top 10 Fallers:")
print(top_fallers[["Spelare","Lag","Score","Pris","Ägd"]])
