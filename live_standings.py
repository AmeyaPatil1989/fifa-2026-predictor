# -*- coding: utf-8 -*-
"""
Recomputes group standings live by overlaying ESPN-confirmed results (live
in-progress scores AND finished-but-not-yet-synced results) on top of the
existing match_predictions.csv data, then reusing the exact same standings
logic from main.py's compute_group_standings().

This does NOT touch results.csv or any file on disk — it's a pure in-memory
overlay computed fresh on each page load, using whatever live_data dict
Today's Matches already fetched from ESPN this session.

Design choice: live IN-PROGRESS matches are treated as already decided at
their current score for standings purposes (e.g. a team currently winning
2-0 at minute 60 is shown with that result counted). This is a deliberate
simplification — standings will fluctuate live as scores change, similar to
how live scoreboards on other sites work, and will self-correct once the
match actually finishes and your daily pipeline syncs the final result.
"""
import pandas as pd
from main import compute_group_standings


def build_live_fixtures(predictions: pd.DataFrame, live_data: dict) -> pd.DataFrame:
    """
    Returns a fixtures-shaped DataFrame (same shape compute_group_standings
    expects) with ESPN live/finished results overlaid on top of whatever
    predictions already has, for matches ESPN currently reports a score for.

    NOTE: match_predictions.csv does not include a 'tournament' column (it's
    computed during prediction but dropped before saving in main.py's
    save_cols) — every row in this file IS a 2026 World Cup fixture already,
    so we just inject a constant value to satisfy compute_group_standings'
    internal tournament filter.
    """
    fixtures = predictions[[
        "date", "home_team", "away_team",
        "completed", "actual_home_score", "actual_away_score",
    ]].copy()
    fixtures["tournament"] = "FIFA World Cup"
    fixtures = fixtures.rename(columns={
        "actual_home_score": "home_score",
        "actual_away_score": "away_score",
    })

    if not live_data:
        return fixtures

    for idx, row in fixtures.iterrows():
        key = (row["home_team"], row["away_team"])
        live = live_data.get(key)
        if live is None:
            continue
        # ESPN reports a score for this match (live in-progress OR finished)
        # and we have actual numbers to use
        if live["home_score"] is not None and live["away_score"] is not None:
            if live["status"] in ("in", "post"):
                fixtures.at[idx, "home_score"] = live["home_score"]
                fixtures.at[idx, "away_score"] = live["away_score"]
                fixtures.at[idx, "completed"] = True

    return fixtures


def compute_live_group_standings(predictions: pd.DataFrame, live_data: dict) -> pd.DataFrame:
    """
    Drop-in replacement for reading group_standings.csv — computes standings
    using live ESPN data overlaid on the existing predictions, via the same
    logic main.py uses for the daily-batch version.
    """
    fixtures = build_live_fixtures(predictions, live_data)
    return compute_group_standings(fixtures)
