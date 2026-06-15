import pandas as pd
from pathlib import Path
from data_prep import load_all, BASE_DIR
from elo_model import build_elo_ratings, get_elo_dataframe
from poisson_model import build_training_data, compute_attack_defense_ratings, predict_all_fixtures
from monte_carlo import run_monte_carlo, WC_GROUPS

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def compute_group_standings(fixtures_2026: pd.DataFrame) -> pd.DataFrame:
    """
    Compute actual group stage standings from completed WC matches.
    Returns one row per team with full stats.
    """
    # Only group stage = matches where both teams are in same group
    # and match is completed
    group_lookup = {}
    for group, teams in WC_GROUPS.items():
        for team in teams:
            group_lookup[team] = group

    records = {}
    for group, teams in WC_GROUPS.items():
        for team in teams:
            records[team] = {
                "team": team,
                "group": group,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0,
                "pts": 0,
                "qualified": None,   # True / False / None (undecided)
            }

    completed = fixtures_2026[
        fixtures_2026["completed"] &
        (fixtures_2026["tournament"] == "FIFA World Cup")
    ].copy()

    for _, row in completed.iterrows():
        home = row["home_team"]
        away = row["away_team"]

        # Only process if both teams are WC group teams
        if home not in records or away not in records:
            continue
        # Only group stage matches (same group)
        if group_lookup.get(home) != group_lookup.get(away):
            continue

        hs = int(row["home_score"])
        as_ = int(row["away_score"])

        records[home]["played"] += 1
        records[away]["played"] += 1
        records[home]["gf"] += hs
        records[home]["ga"] += as_
        records[away]["gf"] += as_
        records[away]["ga"] += hs
        records[home]["gd"] += hs - as_
        records[away]["gd"] += as_ - hs

        if hs > as_:
            records[home]["won"] += 1
            records[home]["pts"] += 3
            records[away]["lost"] += 1
        elif hs == as_:
            records[home]["drawn"] += 1
            records[home]["pts"] += 1
            records[away]["drawn"] += 1
            records[away]["pts"] += 1
        else:
            records[away]["won"] += 1
            records[away]["pts"] += 3
            records[home]["lost"] += 1

    df = pd.DataFrame(list(records.values()))

    # Sort within each group: pts desc, gd desc, gf desc
    df = df.sort_values(
        ["group", "pts", "gd", "gf"],
        ascending=[True, False, False, False]
    ).reset_index(drop=True)

    # Add position within group
    df["position"] = df.groupby("group").cumcount() + 1

    # Mark qualified / eliminated (simplified: top 2 qualify automatically)
    # Full qualification (best 8 third place) determined after all group games
    total_group_matches = 6  # each group plays 6 matches (4 teams, C(4,2)=6)

    for group in WC_GROUPS:
        group_df = df[df["group"] == group]
        total_played = group_df["played"].sum() // 2  # each match counted twice
        if total_played == total_group_matches:
            # Group complete — mark qualified/eliminated
            for pos in group_df["position"].values:
                team = group_df[group_df["position"] == pos]["team"].values[0]
                if pos <= 2:
                    df.loc[df["team"] == team, "qualified"] = "Q"
                elif pos == 3:
                    df.loc[df["team"] == team, "qualified"] = "M"  # maybe
                else:
                    df.loc[df["team"] == team, "qualified"] = "E"  # eliminated

    return df


def compute_2026_scorers(goalscorers: pd.DataFrame, fixtures_2026: pd.DataFrame) -> pd.DataFrame:
    """
    Extract goal scorers for completed 2026 WC matches only.
    Returns one row per (team, scorer) with total goals and penalties scored
    in the tournament so far. Own goals are excluded from scorer credit.
    """
    completed = fixtures_2026[fixtures_2026["completed"]][["date", "home_team", "away_team"]]
    cols = ["team", "scorer", "goals", "penalties"]

    if len(completed) == 0:
        return pd.DataFrame(columns=cols)

    # Keep only goalscorer rows that belong to a completed 2026 WC fixture
    merged = goalscorers.merge(
        completed, on=["date", "home_team", "away_team"], how="inner"
    )
    merged = merged[~merged["own_goal"]]

    if len(merged) == 0:
        return pd.DataFrame(columns=cols)

    grouped = merged.groupby(["team", "scorer"]).agg(
        goals=("scorer", "count"),
        penalties=("penalty", "sum"),
    ).reset_index()

    grouped = grouped.sort_values(["team", "goals"], ascending=[True, False]).reset_index(drop=True)
    return grouped[cols]


def main():
    print("=" * 60)
    print("2026 FIFA WORLD CUP PREDICTOR")
    print("=" * 60)

    # 1. Load data
    print("\n[1/5] Loading data...")
    results, shootouts, goalscorers, squads, fixtures_2026, wc_teams = load_all()

    # 2. Elo ratings
    print("\n[2/5] Building Elo ratings...")
    elo = build_elo_ratings(results)
    elo_df = get_elo_dataframe(elo)
    elo_df.to_csv(OUTPUT_DIR / "elo_ratings.csv", index=False)
    print(f"  Elo ratings computed for {len(elo_df)} teams")

    # 3. Poisson model
    print("\n[3/5] Training Poisson model...")
    training = build_training_data(results)
    attack_rating, defense_rating, global_avg = compute_attack_defense_ratings(training)
    print(f"  Training on {len(training):,} matches")
    print(f"  Global avg goals per match: {global_avg:.3f}")

    # 4. Predict all WC fixtures
    print("\n[4/5] Predicting all 2026 WC fixtures...")
    predictions = predict_all_fixtures(
        fixtures_2026, elo, attack_rating, defense_rating, global_avg
    )

    save_cols = [
        "date", "home_team", "away_team", "city", "country",
        "home_elo", "away_elo",
        "p_home_win", "p_draw", "p_away_win",
        "exp_home_goals", "exp_away_goals",
        "predicted_result", "completed",
        "actual_home_score", "actual_away_score", "actual_result",
    ]
    predictions[save_cols].to_csv(OUTPUT_DIR / "match_predictions.csv", index=False)
    print(f"  Predictions saved for {len(predictions)} matches")

    # Group standings
    standings = compute_group_standings(fixtures_2026)
    standings.to_csv(OUTPUT_DIR / "group_standings.csv", index=False)
    print(f"  Group standings saved")

    # 2026 WC goal scorers (completed matches only)
    scorers = compute_2026_scorers(goalscorers, fixtures_2026)
    scorers.to_csv(OUTPUT_DIR / "wc2026_scorers.csv", index=False)
    print(f"  Goal scorers saved ({len(scorers)} player rows from completed matches)")

    # Accuracy on completed matches
    completed = predictions[predictions["completed"]]
    if len(completed) > 0:
        correct = (completed["predicted_result"] == completed["actual_result"]).sum()
        accuracy = correct / len(completed) * 100
        print(f"\n  Accuracy on completed WC matches: {correct}/{len(completed)} ({accuracy:.1f}%)")

    # 5. Monte Carlo
    print("\n[5/5] Running Monte Carlo simulation...")
    mc_results = run_monte_carlo(
        results, fixtures_2026, elo,
        attack_rating, defense_rating, global_avg,
        shootouts, n_sims=10_000
    )
    mc_results.to_csv(OUTPUT_DIR / "tournament_probabilities.csv", index=False)

    print("\n  Top 15 teams to win the 2026 World Cup:")
    print(f"  {'Rank':<5} {'Team':<25} {'Group':<7} {'Elo':<8} {'Win %'}")
    print("  " + "-" * 55)
    for _, row in mc_results.head(15).iterrows():
        print(
            f"  {int(row['rank']):<5} {row['team']:<25} {row['group']:<7} "
            f"{row['elo']:<8.0f} {row['win_pct']:.2f}%"
        )

    print("\n" + "=" * 60)
    print("OUTPUT FILES SAVED TO:", OUTPUT_DIR)
    print("  - elo_ratings.csv")
    print("  - match_predictions.csv")
    print("  - group_standings.csv")
    print("  - tournament_probabilities.csv")
    print("  - wc2026_scorers.csv")
    print("=" * 60)
    print("\nNow run the dashboard:")
    print("  streamlit run app.py")


if __name__ == "__main__":
    main()
