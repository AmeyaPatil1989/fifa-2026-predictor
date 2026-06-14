import pandas as pd
import numpy as np
from data_prep import load_all

INITIAL_ELO = 1500
K_BASE = 32
HOME_ADVANTAGE = 100
RECENCY_CUTOFF = "2010-01-01"


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def match_result_score(home_score: float, away_score: float) -> tuple:
    if home_score > away_score:
        return 1.0, 0.0
    elif home_score == away_score:
        return 0.5, 0.5
    else:
        return 0.0, 1.0


def goal_index(goal_diff: int) -> float:
    gd = abs(goal_diff)
    if gd == 1:
        return 1.0
    elif gd == 2:
        return 1.5
    else:
        return (11 + gd) / 8


def build_elo_ratings(results: pd.DataFrame) -> dict:
    elo = {}
    completed = results[results["completed"]].sort_values("date").copy()

    for _, row in completed.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        is_neutral = row["neutral"]
        t_weight = row["tournament_weight"]
        recency_w = 1.0 if row["date"] >= pd.Timestamp(RECENCY_CUTOFF) else 0.3

        if home not in elo:
            elo[home] = INITIAL_ELO
        if away not in elo:
            elo[away] = INITIAL_ELO

        home_elo_adj = elo[home] + (0 if is_neutral else HOME_ADVANTAGE)
        exp_home = expected_score(home_elo_adj, elo[away])
        exp_away = 1 - exp_home

        actual_home, actual_away = match_result_score(row["home_score"], row["away_score"])
        gd = abs(row["home_score"] - row["away_score"])
        gi = goal_index(gd)
        k = K_BASE * t_weight * recency_w * gi

        elo[home] = elo[home] + k * (actual_home - exp_home)
        elo[away] = elo[away] + k * (actual_away - exp_away)

    return elo


def get_elo_dataframe(elo: dict) -> pd.DataFrame:
    df = pd.DataFrame(list(elo.items()), columns=["team", "elo"])
    df = df.sort_values("elo", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def get_team_elo(elo: dict, team: str) -> float:
    return elo.get(team, 1300)


if __name__ == "__main__":
    results, shootouts, goalscorers, squads, fixtures_2026, wc_teams = load_all()
    elo = build_elo_ratings(results)
    elo_df = get_elo_dataframe(elo)

    print("\nTop 20 teams by Elo rating:")
    print(elo_df.head(20).to_string(index=False))

    print("\nWC 2026 team Elo ratings:")
    wc_elo = elo_df[elo_df["team"].isin(wc_teams)].reset_index(drop=True)
    print(wc_elo.to_string(index=False))
