# 🏆 2026 FIFA World Cup Predictor

A live, daily-updated prediction dashboard for the 2026 FIFA World Cup — built with statistical modeling on 49,000+ historical international matches, covering all 48 teams across the tournament.

**🔗 Live app:** [fifa-2026-predictor-cettrbrndfachzrhogw3ue.streamlit.app](https://fifa-2026-predictor-cettrbrndfachzrhogw3ue.streamlit.app/)

---

## Overview

This project predicts match outcomes, group standings, and tournament-wide win probabilities for the 2026 World Cup, and tracks prediction accuracy against real results as the tournament progresses. The dashboard refreshes daily as new match results become available.

## Features

- **Today's Matches** — live match cards with win probabilities, expected goals, and results for completed games
- **All Predictions** — full schedule of all 72 matches with model predictions and outcomes
- **Tournament Odds** — win probability rankings for all 48 teams, with an interactive chart
- **Group Standings** — live W/D/L/GF/GA/GD/Pts tables for all 12 groups, with qualification status
- **Knockout Bracket** — predicted bracket from Round of 16 through the Final, seeded by tournament win probability
- **Squads** — full 26-player rosters for every team, including club affiliations, players to watch, fixtures, goals scored in the tournament, and each team's tournament outlook
- **Head to Head** — custom matchup predictor for any two teams
- Cross-linked navigation — click any team name to jump straight to its squad and stats

## Methodology

- **Elo rating system** — built from 49,000+ international results dating back to 1872, weighted by competition tier (World Cup, continental championships, qualifiers, friendlies)
- **Poisson regression** — models each team's attacking and defensive strength to estimate expected goals per match
- **Monte Carlo simulation** — 10,000 full-tournament simulations to estimate each team's probability of advancing through every knockout round, including the final

## Tech Stack

- **Python** — data pipeline and modeling
- **pandas / NumPy / SciPy** — data processing and statistical models
- **Streamlit** — interactive web dashboard
- **Plotly** — charts and visualizations
- **GitHub + Streamlit Community Cloud** — version control and hosting

## Data Pipeline & Automation

The underlying dataset (historical match results, goal scorers, shootouts) is pulled daily from a continuously-updated open dataset. A scheduled pipeline:

1. Pulls the latest match results
2. Retrains the Elo and Poisson models on the updated data
3. Re-runs the Monte Carlo simulation
4. Recomputes group standings, fixtures, and goal-scorer stats for all 48 teams
5. Pushes updated predictions live — the dashboard reflects new results automatically

## Running Locally (Dashboard Only)

The dashboard runs standalone using the pre-generated predictions already included in this repo — no dataset download needed.

```bash
git clone https://github.com/AmeyaPatil1989/fifa-2026-predictor.git
cd fifa-2026-predictor
pip install -r requirements.txt
streamlit run app.py
```

## Full Pipeline (Regenerating Predictions)

`main.py` and the model modules (`elo_model.py`, `poisson_model.py`, `monte_carlo.py`, `data_prep.py`) are included for reference and show how predictions are generated end to end. Running `main.py` requires the full historical match dataset (~49,000 rows of results, goal scorers, and shootouts), which isn't included in this repo due to size.

To run the full pipeline:

1. Clone the historical dataset into `international_results/`:
   ```bash
   git clone https://github.com/martj42/international_results.git international_results
   ```
2. Run the pipeline:
   ```bash
   python main.py
   ```
   This rebuilds Elo ratings, trains the Poisson model, predicts all 72 fixtures, computes group standings and goal scorers, runs the 10,000-simulation Monte Carlo tournament model, and writes everything to `output/`.
3. Re-run the dashboard to see the updated predictions:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
fifa-2026-predictor/
├── app.py                  # Streamlit dashboard
├── main.py                 # Full pipeline entry point (reference)
├── data_prep.py            # Data loading and cleaning
├── elo_model.py             # Elo rating system
├── poisson_model.py          # Expected goals model
├── monte_carlo.py           # Tournament simulation
├── requirements.txt
├── output/                   # Generated predictions and stats
└── international_results/    # Squad/club data (full dataset not included)
```

---

Built by Ameya Patil — [LinkedIn](https://www.linkedin.com/in/ameya-patil-10102a181/) · [Live Demo](https://fifa-2026-predictor-cettrbrndfachzrhogw3ue.streamlit.app/)

Background image via Vecteezy
