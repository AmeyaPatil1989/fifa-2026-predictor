import pandas as pd
import numpy as np
from scipy.stats import poisson
from data_prep import load_all
from elo_model import build_elo_ratings, get_team_elo

TRAINING_CUTOFF = "2018-01-01"
MAX_GOALS = 10


def build_training_data(results: pd.DataFrame) -> pd.DataFrame:
    return results[
        results["completed"] &
        (results["date"] >= TRAINING_CUTOFF)
    ].copy()


def compute_attack_defense_ratings(training: pd.DataFrame) -> tuple:
    attack, defense, counts = {}, {}, {}

    for _, row in training.iterrows():
        h, a = row["home_team"], row["away_team"]
        hs, as_ = row["home_score"], row["away_score"]

        attack[h] = attack.get(h, 0) + hs
        defense[h] = defense.get(h, 0) + as_
        counts[h] = counts.get(h, 0) + 1
        attack[a] = attack.get(a, 0) + as_
        defense[a] = defense.get(a, 0) + hs
        counts[a] = counts.get(a, 0) + 1

    global_avg = sum(attack.values()) / max(sum(counts.values()), 1)

    attack_rating, defense_rating = {}, {}
    for team in counts:
        n = counts[team]
        if n >= 5:
            attack_rating[team] = attack[team] / n
            defense_rating[team] = defense[team] / n
        else:
            w = n / (n + 5)
            attack_rating[team] = w * (attack[team] / n) + (1 - w) * global_avg
            defense_rating[team] = w * (defense[team] / n) + (1 - w) * global_avg

    return attack_rating, defense_rating, global_avg


def predict_goals(
    home_team, away_team, elo,
    attack_rating, defense_rating,
    global_avg, is_neutral=True
) -> tuple:
    home_elo = get_team_elo(elo, home_team)
    away_elo = get_team_elo(elo, away_team)
    elo_diff = home_elo - away_elo
    elo_goal_adj = elo_diff / 200 * 0.3

    home_attack = attack_rating.get(home_team, global_avg)
    home_defense = defense_rating.get(home_team, global_avg)
    away_attack = attack_rating.get(away_team, global_avg)
    away_defense = defense_rating.get(away_team, global_avg)

    lambda_home = (home_attack * away_defense / global_avg)
    lambda_away = (away_attack * home_defense / global_avg)

    lambda_home = 0.4 * lambda_home + 0.6 * (global_avg + elo_goal_adj)
    lambda_away = 0.4 * lambda_away + 0.6 * (global_avg - elo_goal_adj)

    if not is_neutral:
        lambda_home *= 1.15
        lambda_away *= 0.90

    lambda_home = max(0.3, min(lambda_home, 5.0))
    lambda_away = max(0.3, min(lambda_away, 5.0))

    return lambda_home, lambda_away


def predict_match_probabilities(
    home_team, away_team, elo,
    attack_rating, defense_rating,
    global_avg, is_neutral=True
) -> dict:
    lh, la = predict_goals(
        home_team, away_team, elo,
        attack_rating, defense_rating, global_avg, is_neutral
    )

    home_probs = [poisson.pmf(i, lh) for i in range(MAX_GOALS + 1)]
    away_probs = [poisson.pmf(i, la) for i in range(MAX_GOALS + 1)]

    p_home_win = p_draw = p_away_win = 0.0

    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = home_probs[i] * away_probs[j]
            if i > j:
                p_home_win += p
            elif i == j:
                p_draw += p
            else:
                p_away_win += p

    total = p_home_win + p_draw + p_away_win
    p_home_win /= total
    p_draw /= total
    p_away_win /= total

    return {
        "home_team": home_team,
        "away_team": away_team,
        "p_home_win": round(p_home_win, 4),
        "p_draw": round(p_draw, 4),
        "p_away_win": round(p_away_win, 4),
        "exp_home_goals": round(lh, 2),
        "exp_away_goals": round(la, 2),
        "home_elo": round(get_team_elo(elo, home_team), 1),
        "away_elo": round(get_team_elo(elo, away_team), 1),
    }


def predict_all_fixtures(
    fixtures, elo, attack_rating, defense_rating, global_avg
) -> pd.DataFrame:
    records = []

    for _, row in fixtures.iterrows():
        result = predict_match_probabilities(
            home_team=row["home_team"],
            away_team=row["away_team"],
            elo=elo,
            attack_rating=attack_rating,
            defense_rating=defense_rating,
            global_avg=global_avg,
            is_neutral=row["neutral"],
        )

        result["date"] = row["date"]
        result["tournament"] = row["tournament"]
        result["city"] = row["city"]
        result["country"] = row["country"]
        result["completed"] = row["completed"]

        if row["completed"]:
            result["actual_home_score"] = int(row["home_score"])
            result["actual_away_score"] = int(row["away_score"])
            if row["home_score"] > row["away_score"]:
                result["actual_result"] = "Home Win"
            elif row["home_score"] == row["away_score"]:
                result["actual_result"] = "Draw"
            else:
                result["actual_result"] = "Away Win"
        else:
            result["actual_home_score"] = None
            result["actual_away_score"] = None
            result["actual_result"] = "Upcoming"

        probs = {
            "Home Win": result["p_home_win"],
            "Draw": result["p_draw"],
            "Away Win": result["p_away_win"],
        }
        result["predicted_result"] = max(probs, key=probs.get)
        records.append(result)

    df = pd.DataFrame(records)
    df = df.sort_values("date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    results, shootouts, goalscorers, squads, fixtures_2026, wc_teams = load_all()
    elo = build_elo_ratings(results)
    training = build_training_data(results)
    attack_rating, defense_rating, global_avg = compute_attack_defense_ratings(training)
    predictions = predict_all_fixtures(
        fixtures_2026, elo, attack_rating, defense_rating, global_avg
    )

    cols = ["date", "home_team", "away_team",
            "p_home_win", "p_draw", "p_away_win",
            "exp_home_goals", "exp_away_goals",
            "predicted_result", "completed", "actual_result"]
    print(predictions[cols].to_string(index=False))
