import pandas as pd
import numpy as np
from data_prep import load_all
from elo_model import build_elo_ratings, get_team_elo
from poisson_model import build_training_data, compute_attack_defense_ratings, predict_goals

N_SIMULATIONS = 10_000

WC_GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}


def build_shootout_rates(shootouts: pd.DataFrame) -> dict:
    rates = {}
    all_teams = set(shootouts["home_team"]).union(set(shootouts["away_team"]))
    for team in all_teams:
        team_matches = shootouts[
            (shootouts["home_team"] == team) | (shootouts["away_team"] == team)
        ]
        wins = (team_matches["winner"] == team).sum()
        total = len(team_matches)
        rates[team] = wins / total if total >= 3 else 0.5
    return rates


def simulate_match(
    team_a, team_b, elo,
    attack_rating, defense_rating,
    global_avg, is_neutral=True
) -> tuple:
    la, lb = predict_goals(
        team_a, team_b, elo,
        attack_rating, defense_rating, global_avg, is_neutral
    )
    return np.random.poisson(la), np.random.poisson(lb)


def simulate_shootout(team_a: str, team_b: str, shootout_rates: dict) -> str:
    rate_a = shootout_rates.get(team_a, 0.5)
    rate_b = shootout_rates.get(team_b, 0.5)
    p_a = rate_a / (rate_a + rate_b)
    return team_a if np.random.random() < p_a else team_b


def simulate_group_stage(
    groups, completed_results, elo,
    attack_rating, defense_rating, global_avg
) -> dict:
    standings = {}
    for group, teams in groups.items():
        standings[group] = {t: {"pts": 0, "gf": 0, "ga": 0, "gd": 0} for t in teams}

    for group, teams in groups.items():
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                team_a, team_b = teams[i], teams[j]

                if (team_a, team_b) in completed_results:
                    ga, gb = completed_results[(team_a, team_b)]
                elif (team_b, team_a) in completed_results:
                    gb, ga = completed_results[(team_b, team_a)]
                else:
                    ga, gb = simulate_match(
                        team_a, team_b, elo,
                        attack_rating, defense_rating, global_avg
                    )

                standings[group][team_a]["gf"] += ga
                standings[group][team_a]["ga"] += gb
                standings[group][team_b]["gf"] += gb
                standings[group][team_b]["ga"] += ga
                standings[group][team_a]["gd"] += ga - gb
                standings[group][team_b]["gd"] += gb - ga

                if ga > gb:
                    standings[group][team_a]["pts"] += 3
                elif ga == gb:
                    standings[group][team_a]["pts"] += 1
                    standings[group][team_b]["pts"] += 1
                else:
                    standings[group][team_b]["pts"] += 3

    return standings


def get_group_qualifiers(standings: dict) -> tuple:
    group_results = {}
    third_place_teams = []

    for group, table in standings.items():
        sorted_teams = sorted(
            table.items(),
            key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]),
            reverse=True,
        )
        group_results[group] = [t[0] for t in sorted_teams]
        third_place_teams.append((sorted_teams[2][0], sorted_teams[2][1]))

    third_place_teams.sort(
        key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]),
        reverse=True,
    )
    third_place_qualifiers = [t[0] for t in third_place_teams[:8]]
    return group_results, third_place_qualifiers


def simulate_knockout_match(
    team_a, team_b, elo,
    attack_rating, defense_rating,
    global_avg, shootout_rates
) -> str:
    ga, gb = simulate_match(
        team_a, team_b, elo,
        attack_rating, defense_rating, global_avg, is_neutral=True
    )
    if ga > gb:
        return team_a
    elif gb > ga:
        return team_b
    else:
        return simulate_shootout(team_a, team_b, shootout_rates)


def simulate_tournament(
    groups, completed_results, elo,
    attack_rating, defense_rating,
    global_avg, shootout_rates
) -> str:
    standings = simulate_group_stage(
        groups, completed_results, elo,
        attack_rating, defense_rating, global_avg
    )
    group_results, third_qualifiers = get_group_qualifiers(standings)

    bracket = []
    for gk in group_results:
        bracket.append((group_results[gk][0], group_results[gk][1]))

    np.random.shuffle(third_qualifiers)
    for i in range(0, len(third_qualifiers), 2):
        if i + 1 < len(third_qualifiers):
            bracket.append((third_qualifiers[i], third_qualifiers[i + 1]))

    remaining = []
    for match in bracket:
        winner = simulate_knockout_match(
            match[0], match[1], elo,
            attack_rating, defense_rating, global_avg, shootout_rates
        )
        remaining.append(winner)

    while len(remaining) > 1:
        next_round = []
        for i in range(0, len(remaining) - 1, 2):
            winner = simulate_knockout_match(
                remaining[i], remaining[i + 1], elo,
                attack_rating, defense_rating, global_avg, shootout_rates
            )
            next_round.append(winner)
        if len(remaining) % 2 == 1:
            next_round.append(remaining[-1])
        remaining = next_round

    return remaining[0]


def run_monte_carlo(
    results, fixtures_2026, elo,
    attack_rating, defense_rating,
    global_avg, shootouts,
    n_sims=N_SIMULATIONS
) -> pd.DataFrame:
    shootout_rates = build_shootout_rates(shootouts)

    completed = fixtures_2026[fixtures_2026["completed"]].copy()
    completed_results = {}
    for _, row in completed.iterrows():
        completed_results[(row["home_team"], row["away_team"])] = (
            int(row["home_score"]), int(row["away_score"])
        )

    win_counts = {}
    for teams in WC_GROUPS.values():
        for t in teams:
            win_counts[t] = 0

    print(f"Running {n_sims:,} tournament simulations...")
    for i in range(n_sims):
        if (i + 1) % 2000 == 0:
            print(f"  Completed {i + 1:,} simulations...")
        winner = simulate_tournament(
            WC_GROUPS, completed_results, elo,
            attack_rating, defense_rating, global_avg, shootout_rates
        )
        if winner in win_counts:
            win_counts[winner] += 1

    records = []
    for team, wins in win_counts.items():
        group = next((g for g, teams in WC_GROUPS.items() if team in teams), "?")
        records.append({
            "team": team,
            "group": group,
            "win_probability": round(wins / n_sims, 4),
            "win_pct": round(wins / n_sims * 100, 2),
            "simulated_wins": wins,
            "elo": round(get_team_elo(elo, team), 1),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("win_probability", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


if __name__ == "__main__":
    results, shootouts, goalscorers, squads, fixtures_2026, wc_teams = load_all()
    elo = build_elo_ratings(results)
    training = build_training_data(results)
    attack_rating, defense_rating, global_avg = compute_attack_defense_ratings(training)

    mc_results = run_monte_carlo(
        results, fixtures_2026, elo,
        attack_rating, defense_rating, global_avg,
        shootouts, n_sims=N_SIMULATIONS
    )

    print("\n2026 FIFA World Cup Win Probabilities:")
    print(mc_results[["rank", "team", "group", "elo", "win_pct"]].to_string(index=False))
