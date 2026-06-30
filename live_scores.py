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


def fetch_match_events(event_id: str, timeout=8) -> list:
    """
    Fetches the full play-by-play commentary feed for a match (kickoff, goals,
    cards, substitutions, delays, halftime, etc.) using ESPN's summary endpoint.
    Returns a list of dicts in chronological order (oldest first):
        [{"minute": str, "type": str, "team": str, "text": str, "is_goal": bool}, ...]

    Returns an empty list on any failure.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    events = []
    try:
        for ev in data.get("keyEvents", []):
            team_name = ev.get("team", {}).get("displayName", "")
            events.append({
                "minute": ev.get("clock", {}).get("displayValue", ""),
                "type": ev.get("type", {}).get("text", ""),
                "team": normalise_espn_team(team_name) if team_name else "",
                "text": ev.get("text") or ev.get("shortText", ""),
                "is_goal": ev.get("scoringPlay", False),
            })
    except Exception:
        return []

    return events


def fetch_match_scorers(event_id: str, home_team: str = None, away_team: str = None, timeout=8) -> list:
    """
    Fetches goal-scorer details for a specific match using ESPN's summary
    endpoint. Returns a list of dicts:
        [{"team": str, "scorer": str, "minute": str, "own_goal": bool, "penalty": bool}, ...]

    Returns an empty list on any failure.

    Own goal attribution: standard football convention credits an own goal to
    the team that BENEFITS (i.e. the team whose score increments), with the
    own-goal scorer's name tagged "(OG)". We assume ESPN's `ev["team"]` field
    follows this same convention, consistent with how it behaved for regular
    goals and penalties in testing — but this has NOT been verified against
    an actual own-goal event yet (none has occurred in matches checked so
    far). If an own goal appears credited to the wrong team once live, this
    assumption is the first place to check.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    known_teams = {t for t in (home_team, away_team) if t}

    scorers = []
    try:
        key_events = data.get("keyEvents", [])
        for ev in key_events:
            # scoringPlay is the reliable flag for "this event put the ball in
            # the net" — covers regular goals, penalties ("Penalty - Scored"),
            # and own goals alike. Matching on type.text alone is fragile since
            # ESPN uses different labels (e.g. "Penalty - Scored" has no "goal"
            # substring) for different goal types.
            if not ev.get("scoringPlay", False):
                continue
            ev_type = ev.get("type", {}).get("text", "")

            participants = ev.get("participants", [])
            scorer_name = None
            if participants:
                scorer_name = participants[0].get("athlete", {}).get("displayName")
            if not scorer_name:
                scorer_name = ev.get("shortText", ev.get("text", "Unknown"))

            team_name = normalise_espn_team(ev.get("team", {}).get("displayName", ""))
            full_text = (ev.get("text", "") + " " + ev.get("shortText", "")).lower()
            is_own_goal = "own goal" in full_text

            # Sanity check: if we know the two real team names and ESPN's
            # reported team isn't either of them, something's off (renamed
            # team, alias gap) — keep the raw name rather than silently drop it.
            if known_teams and team_name not in known_teams:
                pass  # leave team_name as-is; caller can decide how to handle an unmatched team

            scorers.append({
                "team": team_name,
                "scorer": scorer_name,
                "minute": ev.get("clock", {}).get("displayValue", ""),
                "own_goal": is_own_goal,
                "penalty": "penalty" in ev_type.lower() or "penalty" in full_text or "(pen" in full_text,
            })
    except Exception:
        return []

    return scorers


def fetch_match_winner(event_id: str, timeout=8) -> dict:
    """
    Fetches the confirmed winner of a match using ESPN's summary endpoint,
    including matches decided by a penalty shootout (where the 90-minute
    scoreline alone is a draw and doesn't reflect who actually advanced).

    Returns:
        {
            "winner": str or None (normalized team name of the winner, or
                      None if no winner field is set / not yet decided),
            "went_to_pens": bool,
            "detail": str (e.g. "FT-Pens", "FT", "AET")
        }
    Returns {"winner": None, "went_to_pens": False, "detail": ""} on any failure.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}"
    fallback = {"winner": None, "went_to_pens": False, "detail": ""}
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return fallback

    try:
        comp = data.get("header", {}).get("competitions", [{}])[0]
        status_type = comp.get("status", {}).get("type", {})
        detail = status_type.get("shortDetail", "")
        went_to_pens = status_type.get("name", "") == "STATUS_FINAL_PEN"

        winner_name = None
        for c in comp.get("competitors", []):
            if c.get("winner") is True:
                winner_name = normalise_espn_team(c.get("team", {}).get("displayName", ""))
                break

        return {"winner": winner_name, "went_to_pens": went_to_pens, "detail": detail}
    except Exception:
        return fallback


def fetch_live_scores(timeout=8, dates=None) -> dict:
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

    `dates`: optional string to query a specific date or range, in ESPN's
    format. Examples:
        "20260618"            -> just that one day
        "20260611-20260719"   -> the full tournament window
    If omitted, ESPN returns only today's matches (default scoreboard behavior).
    """
    url = ESPN_SCOREBOARD_URL
    params = {"limit": 200}
    if dates:
        params["dates"] = dates

    try:
        resp = requests.get(url, params=params, timeout=timeout)
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
                "event_id": event.get("id"),
            }
    except Exception:
        return {}

    return out


# Full 2026 World Cup date range (group stage through final). Used to fetch
# ALL tournament results in one call — covers cases where our own
# match_predictions.csv is stale for a match that's no longer "today" but
# also hasn't been synced by the daily pipeline yet (e.g. checking yesterday's
# results before today's daily_update.bat run has happened).
WC_2026_DATE_RANGE = "20260611-20260719"


def fetch_tournament_scores(timeout=10) -> dict:
    """Fetches results for the entire 2026 World Cup window in one call."""
    return fetch_live_scores(timeout=timeout, dates=WC_2026_DATE_RANGE)
