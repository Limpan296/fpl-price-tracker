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

df_filt_up = df_filt[df_filt["cost_change_event"] <= 0].copy()
df_filt_down = df_filt[df_filt["cost_change_event"] >= 0].copy()

df_filt_up["adjusted_progress_rise"] = df_filt_up["progress_rise"] * (df_filt_up["selected_by_percent"]/10)
df_filt_down["adjusted_progress_fall"] = df_filt_down["progress_fall"] * (df_filt_down["selected_by_percent"]/10)

# =========================
#  SCORE (kombinerad logik)
# =========================
df_filt_up["score_rise"] = df_filt_up["progress_rise"]*0.6 + df_filt_up["adjusted_progress_rise"]/100*0.4
df_filt_down["score_fall"] = df_filt_down["progress_fall"]*0.6 + df_filt_down["adjusted_progress_fall"]/100*0.4

# =========================
#  RANKA TOP 10
# =========================
top_up = (df_filt_up.sort_values(["score_rise","progress_rise"], ascending=[False,False])
          .head(10)[["web_name","team_name","price","selected_by_percent",
                      "net_transfers","effective_net","rise_threshold","progress_rise",
                      "adjusted_progress_rise","score_rise"]])

top_down = (df_filt_down.sort_values(["score_fall","progress_fall"], ascending=[False,False])
            .head(10)[["web_name","team_name","price","selected_by_percent",
                        "net_transfers","effective_net","fall_threshold","progress_fall",
                        "adjusted_progress_fall","score_fall"]])

# =========================
#  FORMAT FUNCTIONS
# =========================
def format_up(df):
    return df.assign(
        price=lambda x: x["price"].round(1),
        selected_by_percent=lambda x: x["selected_by_percent"].round(2),
        effective_net=lambda x: x["effective_net"].astype(int),
        rise_threshold=lambda x: x["rise_threshold"].astype(int),
        progress_rise=lambda x: (100*x["progress_rise"]).round(1),
        adjusted_progress_rise=lambda x: (100*x["adjusted_progress_rise"]).round(1),
        score_rise=lambda x: (100*x["score_rise"]).round(1),
        direction="up"
    ).rename(columns={
        "web_name":"Player","team_name":"Team","price":"Price (£m)",
        "selected_by_percent":"Ägd (%)","net_transfers":"Net transfers (GW)",
        "effective_net":"Eff. net","rise_threshold":"Threshold",
        "progress_rise":"Progress (%)","adjusted_progress_rise":"Adj. Progress (%)",
        "score_rise":"Score (%)"
    })

def format_down(df):
    return df.assign(
        price=lambda x: x["price"].round(1),
        selected_by_percent=lambda x: x["selected_by_percent"].round(2),
        effective_net=lambda x: x["effective_net"].astype(int),
        fall_threshold=lambda x: x["fall_threshold"].astype(int),
        progress_fall=lambda x: (100*x["progress_fall"]).round(1),
        adjusted_progress_fall=lambda x: (100*x["adjusted_progress_fall"]).round(1),
        score_fall=lambda x: (100*x["score_fall"]).round(1),
        direction="down"
    ).rename(columns={
        "web_name":"Spelare","team_name":"Lag","price":"Pris (£m)",
        "selected_by_percent":"Ägd (%)","net_transfers":"Net transfers (GW)",
        "effective_net":"Eff. net","fall_threshold":"Threshold",
        "progress_fall":"Progress (%)","adjusted_progress_fall":"Adj. Progress (%)",
        "score_fall":"Score (%)"
    })

# =========================
#  FORMAT & PRINT
# =========================
df_top_up = format_up(top_up)
df_top_down = format_down(top_down)

# Slå ihop för CSV
df_all = pd.concat([df_top_up, df_top_down], ignore_index=True)

print("\n🔼 Top 10 kandidater för prisuppgång:\n")
print(df_top_up)

print("\n🔽 Top 10 kandidater för prisnedgång:\n")
print(df_top_down)

# =========================
#  SPARA RESULTAT (för webben)
# =========================
output_file = "static/predictions.csv"
df_all.to_csv(output_file, index=False, encoding="utf-8")
print(f"\n✅ Predictions sparade till {output_file}")
