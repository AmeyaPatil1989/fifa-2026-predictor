# -*- coding: utf-8 -*-
"""
Fetches live 2026 FIFA World Cup scores from ESPN's public (no-auth) scoreboard
endpoint and normalizes team names to match our existing dataset's naming
convention (from data_prep.py's normalise_team / MANUAL_ALIASES).

ESPN endpoint (undocumented, no API key required):
    https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard

NOTE: This is a reverse-engineered public endpoint, not an officially
supported ESPN product. It could change or stop working without notice.
Treat failures gracefully (return empty / fall back to predictions-only).
"""
import requests

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# ESPN team names -> our normalized team names (only includes cases where
# they differ; everything else is assumed to match as-is)
ESPN_TEAM_ALIASES = {
    "USA": "United States",
    "South Korea": "South Korea",  # ESPN sometimes uses "Korea Republic"
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Ivory Coast": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Czech Republic": "Czech Republic",
    "Czechia": "Czech Republic",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Cape Verde": "Cape Verde",
    "Curacao": "Curaçao",
    "United States of America": "United States",
}


def normalise_espn_team(name: str) -> str:
    return ESPN_TEAM_ALIASES.get(name, name)


def fetch_live_scores(timeout=5) -> dict:
    """
    Returns a dict keyed by (home_team, away_team) normalized tuple, with values:
        {
            "status": "pre" | "in" | "post",
            "status_detail": str (e.g. "FT", "HT", "67'", "Scheduled"),
            "home_score": int or None,
            "away_score": int or None,
            "clock": str or None (e.g. "67'"),
        }
    Returns an empty dict on any failure (network error, unexpected shape) so
    the caller can fall back to predictions-only display without crashing.
    """
    try:
        resp = requests.get(ESPN_SCOREBOARD_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    out = {}
    try:
        for event in data.get("events", []):
            competitions = event.get("competitions", [])
            if not competitions:
                continue
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                continue

            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue

            home_name = normalise_espn_team(home.get("team", {}).get("displayName", ""))
            away_name = normalise_espn_team(away.get("team", {}).get("displayName", ""))

            status = event.get("status", {})
            status_type = status.get("type", {})
            state = status_type.get("state", "pre")  # 'pre', 'in', 'post'
            detail = status_type.get("shortDetail", "")

            home_score = home.get("score")
            away_score = away.get("score")

            out[(home_name, away_name)] = {
                "status": state,
                "status_detail": detail,
                "home_score": int(home_score) if home_score not in (None, "") else None,
                "away_score": int(away_score) if away_score not in (None, "") else None,
                "clock": status.get("displayClock"),
                "kickoff_time": event.get("date"),  # ISO timestamp, e.g. "2026-06-18T16:00Z"
            }
    except Exception:
        return {}

    return out
