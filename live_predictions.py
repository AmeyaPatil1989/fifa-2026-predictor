# -*- coding: utf-8 -*-
"""
Live win-probability re-estimation for in-progress matches.

Approach: take each team's PRE-MATCH expected goals for the full 90 minutes
(already computed by poisson_model.py and stored in match_predictions.csv),
scale them down proportionally to the time remaining, then run a fresh
Poisson calculation for ADDITIONAL goals from this point forward. Combine
that with the current actual score to get updated win/draw/loss probabilities.

This intentionally does NOT account for game-state effects (a team leading
3-0 tends to sit back and concede possession, lowering both teams' true
scoring rates relative to a flat time-based scaling). That's a known,
disclosed simplification — capturing it properly would need play-by-play
features (possession, shots, cards) we don't have. The model still correctly
captures the two dominant effects: less time left = less chance to come
back, and the current score is the actual current score.

No historical dataset or model retraining required — this only needs the
pre-match expected goals (already shipped in match_predictions.csv) plus
the live score/clock from ESPN.
"""
import re
from scipy.stats import poisson

MAX_GOALS = 10


def parse_minutes_elapsed(clock_display: str) -> float:
    """
    Parses ESPN's displayClock format into elapsed minutes.
    Examples: "23'" -> 23, "45'+5'" -> 50, "90'+7'" -> 97 (treated as full-time)
    Returns None if unparseable (e.g. "Scheduled", "HT").
    """
    if not clock_display:
        return None
    clock_display = clock_display.strip()

    # Halftime / pre-match / other non-numeric statuses
    if not any(ch.isdigit() for ch in clock_display):
        return None

    match = re.match(r"(\d+)'?(?:\+(\d+)'?)?", clock_display)
    if not match:
        return None
    base = int(match.group(1))
    stoppage = int(match.group(2)) if match.group(2) else 0
    return base + stoppage


def live_win_probability(
    exp_home_goals_full: float,
    exp_away_goals_full: float,
    current_home_score: int,
    current_away_score: int,
    minutes_elapsed: float,
    match_length: float = 90.0,
) -> dict:
    """
    Returns updated win/draw/loss probabilities for the rest of the match,
    combined with the current score.

    If minutes_elapsed >= match_length (or very close to it), returns the
    current score as a near-certain result rather than running the model
    on ~0 remaining minutes (which would be numerically unstable / meaningless).
    """
    minutes_remaining = max(match_length - minutes_elapsed, 0)

    # Match is effectively over — just reflect the actual score
    if minutes_remaining < 1:
        if current_home_score > current_away_score:
            return {"p_home_win": 1.0, "p_draw": 0.0, "p_away_win": 0.0,
                    "exp_additional_home_goals": 0.0, "exp_additional_away_goals": 0.0}
        elif current_home_score < current_away_score:
            return {"p_home_win": 0.0, "p_draw": 0.0, "p_away_win": 1.0,
                    "exp_additional_home_goals": 0.0, "exp_additional_away_goals": 0.0}
        else:
            return {"p_home_win": 0.0, "p_draw": 1.0, "p_away_win": 0.0,
                    "exp_additional_home_goals": 0.0, "exp_additional_away_goals": 0.0}

    time_fraction = minutes_remaining / match_length
    lambda_home_remaining = exp_home_goals_full * time_fraction
    lambda_away_remaining = exp_away_goals_full * time_fraction

    # Floor to avoid a fully-zero Poisson distribution edge case
    lambda_home_remaining = max(lambda_home_remaining, 0.05)
    lambda_away_remaining = max(lambda_away_remaining, 0.05)

    home_probs = [poisson.pmf(i, lambda_home_remaining) for i in range(MAX_GOALS + 1)]
    away_probs = [poisson.pmf(i, lambda_away_remaining) for i in range(MAX_GOALS + 1)]

    p_home_win = p_draw = p_away_win = 0.0

    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = home_probs[i] * away_probs[j]
            final_home = current_home_score + i
            final_away = current_away_score + j
            if final_home > final_away:
                p_home_win += p
            elif final_home == final_away:
                p_draw += p
            else:
                p_away_win += p

    total = p_home_win + p_draw + p_away_win
    if total > 0:
        p_home_win /= total
        p_draw /= total
        p_away_win /= total

    return {
        "p_home_win": round(p_home_win, 4),
        "p_draw": round(p_draw, 4),
        "p_away_win": round(p_away_win, 4),
        "exp_additional_home_goals": round(lambda_home_remaining, 2),
        "exp_additional_away_goals": round(lambda_away_remaining, 2),
    }
