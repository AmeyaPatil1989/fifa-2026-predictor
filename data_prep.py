import pandas as pd
import numpy as np
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "international_results"

MANUAL_ALIASES = {
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Korea DPR": "North Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "China PR": "China",
    "Türkiye": "Turkey",
    "USA": "United States",
    "Czechia": "Czech Republic",
    "Republic of Korea": "South Korea",
    "Democratic Republic of the Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "United States of America": "United States",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "FYR Macedonia": "North Macedonia",
    "The Gambia": "Gambia",
    "Cape Verde Islands": "Cape Verde",
}


def load_former_names() -> dict:
    df = pd.read_csv(DATA_DIR / "former_names.csv")
    return {row["former"]: row["current"] for _, row in df.iterrows()}


def fix_mojibake(value):
    """
    Repairs UTF-8 text that was misread as Windows-1252 then re-saved as UTF-8
    (e.g. 'CuraÃ§ao' -> 'Curaçao', 'Ã©' -> 'é'). Safe no-op on already-correct
    strings: the round-trip raises an error for those, which we catch and
    return the original value unchanged.
    """
    if not isinstance(value, str):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


def normalise_team(name: str, alias_map: dict) -> str:
    if not isinstance(name, str):
        return name
    name = name.strip()
    name = MANUAL_ALIASES.get(name, name)
    name = alias_map.get(name, name)
    return name


def load_results(alias_map: dict) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "results.csv", parse_dates=["date"])
    df["home_team"] = df["home_team"].apply(lambda x: normalise_team(x, alias_map))
    df["away_team"] = df["away_team"].apply(lambda x: normalise_team(x, alias_map))
    df["neutral"] = df["neutral"].astype(str).str.upper() == "TRUE"
    df["completed"] = df["home_score"].notna() & df["away_score"].notna()
    df.loc[df["completed"], "home_score"] = df.loc[df["completed"], "home_score"].astype(float)
    df.loc[df["completed"], "away_score"] = df.loc[df["completed"], "away_score"].astype(float)

    weight_map = {
        "FIFA World Cup": 4.0,
        "FIFA World Cup qualification": 3.0,
        "UEFA Euro": 3.5,
        "Copa América": 3.5,
        "AFC Asian Cup": 3.0,
        "Africa Cup of Nations": 3.0,
        "CONCACAF Gold Cup": 2.5,
        "UEFA Nations League": 2.0,
        "Friendly": 1.0,
    }
    df["tournament_weight"] = df["tournament"].apply(
        lambda t: next((v for k, v in weight_map.items() if k in str(t)), 1.5)
    )
    return df


def load_shootouts(alias_map: dict) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "shootouts.csv", parse_dates=["date"])
    df["home_team"] = df["home_team"].apply(lambda x: normalise_team(x, alias_map))
    df["away_team"] = df["away_team"].apply(lambda x: normalise_team(x, alias_map))
    df["winner"] = df["winner"].apply(lambda x: normalise_team(x, alias_map))
    return df


def load_goalscorers(alias_map: dict) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "goalscorers.csv", parse_dates=["date"])
    df["team"] = df["team"].apply(fix_mojibake)
    df["scorer"] = df["scorer"].apply(fix_mojibake)
    df["home_team"] = df["home_team"].apply(lambda x: normalise_team(x, alias_map))
    df["away_team"] = df["away_team"].apply(lambda x: normalise_team(x, alias_map))
    df["team"] = df["team"].apply(lambda x: normalise_team(x, alias_map))
    df["own_goal"] = df["own_goal"].astype(str).str.upper() == "TRUE"
    df["penalty"] = df["penalty"].astype(str).str.upper() == "TRUE"
    return df


def load_squads() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "squads.csv")


def get_wc_2026_fixtures(results: pd.DataFrame) -> pd.DataFrame:
    wc = results[
        (results["tournament"] == "FIFA World Cup") &
        (results["date"].dt.year == 2026)
    ].copy().reset_index(drop=True)

    # ── Merge ESPN knockout results ────────────────────────────────────────────
    # espn_sync.py writes knockout_results.csv with confirmed scores and
    # upcoming fixtures that the international_results repo may be missing.
    ko_path = BASE_DIR / "knockout_results.csv"
    if ko_path.exists():
        try:
            ko = pd.read_csv(ko_path, parse_dates=["date"])

            # For each ESPN fixture, check if it already exists in wc.
            # If yes: update scores/completed. If no: append as new row.
            for _, kr in ko.iterrows():
                mask = (
                    (wc["home_team"] == kr["home_team"]) &
                    (wc["away_team"] == kr["away_team"]) &
                    (wc["date"].dt.date == kr["date"].date())
                )
                if mask.any():
                    # Update existing row with ESPN scores if available
                    if pd.notna(kr.get("home_score")) and pd.notna(kr.get("away_score")):
                        wc.loc[mask, "home_score"] = float(kr["home_score"])
                        wc.loc[mask, "away_score"] = float(kr["away_score"])
                        wc.loc[mask, "completed"] = True
                else:
                    # New fixture not in repo — append it
                    new_row = {
                        "date": kr["date"],
                        "home_team": kr["home_team"],
                        "away_team": kr["away_team"],
                        "home_score": float(kr["home_score"]) if pd.notna(kr.get("home_score")) else None,
                        "away_score": float(kr["away_score"]) if pd.notna(kr.get("away_score")) else None,
                        "tournament": "FIFA World Cup",
                        "city": kr.get("city", ""),
                        "country": kr.get("country", ""),
                        "neutral": True,
                        "completed": pd.notna(kr.get("home_score")) and pd.notna(kr.get("away_score")),
                        "tournament_weight": 4.0,
                    }
                    wc = pd.concat(
                        [wc, pd.DataFrame([new_row])],
                        ignore_index=True
                    )

            wc = wc.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"Warning: could not merge knockout_results.csv: {e}")

    return wc


def get_wc_teams(fixtures: pd.DataFrame) -> list:
    teams = set(fixtures["home_team"].tolist() + fixtures["away_team"].tolist())
    return sorted(teams)


def get_squad_attacking_strength(goalscorers: pd.DataFrame, squads: pd.DataFrame) -> pd.DataFrame:
    """
    For each WC team, calculate goals scored by current squad players
    in last 3 years. Used as supplementary attacking strength feature.
    """
    cutoff = pd.Timestamp("2023-01-01")
    gs = goalscorers[
        (goalscorers["date"] >= cutoff) &
        (~goalscorers["own_goal"])
    ].copy()

    records = []
    for team in squads["team"].unique():
        players = set(squads[squads["team"] == team]["player"].tolist())
        team_goals = gs[
            (gs["team"] == team) &
            (gs["scorer"].isin(players))
        ]
        # matches played by this team in window
        matches = goalscorers[
            (goalscorers["date"] >= cutoff) &
            ((goalscorers["home_team"] == team) | (goalscorers["away_team"] == team))
        ][["date", "home_team", "away_team"]].drop_duplicates()

        n_matches = len(matches)
        n_goals = len(team_goals)
        goals_per_match = n_goals / n_matches if n_matches > 0 else 0

        records.append({
            "team": team,
            "squad_goals": n_goals,
            "squad_matches": n_matches,
            "squad_goals_per_match": round(goals_per_match, 3),
        })

    return pd.DataFrame(records)


def load_all():
    alias_map = load_former_names()
    results = load_results(alias_map)
    shootouts = load_shootouts(alias_map)
    goalscorers = load_goalscorers(alias_map)
    squads = load_squads()
    fixtures_2026 = get_wc_2026_fixtures(results)
    wc_teams = get_wc_teams(fixtures_2026)

    print(f"Results loaded:      {len(results):,} rows")
    print(f"Shootouts loaded:    {len(shootouts):,} rows")
    print(f"Goalscorers loaded:  {len(goalscorers):,} rows")
    print(f"Squads loaded:       {len(squads):,} players")
    print(f"WC 2026 fixtures:    {len(fixtures_2026):,} matches")
    print(f"WC 2026 teams:       {len(wc_teams)} teams")

    return results, shootouts, goalscorers, squads, fixtures_2026, wc_teams


if __name__ == "__main__":
    load_all()
