import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import datetime

st.set_page_config(
    page_title="2026 FIFA World Cup Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Team Colors ────────────────────────────────────────────────────────────────
TEAM_COLORS = {
    "Argentina":              {"primary": "#74ACDF", "text": "#FFFFFF"},
    "Australia":              {"primary": "#FFCD00", "text": "#006400"},
    "Austria":                {"primary": "#ED2939", "text": "#FFFFFF"},
    "Belgium":                {"primary": "#1A1A1A", "text": "#FFD700"},
    "Bosnia and Herzegovina": {"primary": "#002395", "text": "#FFCD00"},
    "Brazil":                 {"primary": "#009C3B", "text": "#FFDF00"},
    "Canada":                 {"primary": "#FF0000", "text": "#FFFFFF"},
    "Cape Verde":             {"primary": "#003893", "text": "#FFFFFF"},
    "Colombia":               {"primary": "#FCD116", "text": "#003087"},
    "Croatia":                {"primary": "#CC0000", "text": "#FFFFFF"},
    "Curaçao":                {"primary": "#002B7F", "text": "#F9E814"},
    "Czech Republic":         {"primary": "#D7141A", "text": "#FFFFFF"},
    "DR Congo":               {"primary": "#007FFF", "text": "#F7D618"},
    "Ecuador":                {"primary": "#FFD100", "text": "#003087"},
    "Egypt":                  {"primary": "#CE1126", "text": "#FFFFFF"},
    "England":                {"primary": "#CF081F", "text": "#FFFFFF"},
    "France":                 {"primary": "#002395", "text": "#FFFFFF"},
    "Germany":                {"primary": "#DD0000", "text": "#FFFFFF"},
    "Ghana":                  {"primary": "#006B3F", "text": "#FCD116"},
    "Haiti":                  {"primary": "#00209F", "text": "#FFFFFF"},
    "Iran":                   {"primary": "#239F40", "text": "#FFFFFF"},
    "Iraq":                   {"primary": "#007A3D", "text": "#FFFFFF"},
    "Ivory Coast":            {"primary": "#F77F00", "text": "#FFFFFF"},
    "Japan":                  {"primary": "#BC002D", "text": "#FFFFFF"},
    "Jordan":                 {"primary": "#007A3D", "text": "#FFFFFF"},
    "Mexico":                 {"primary": "#006847", "text": "#FFFFFF"},
    "Morocco":                {"primary": "#C1272D", "text": "#FFFFFF"},
    "Netherlands":            {"primary": "#FF6600", "text": "#FFFFFF"},
    "New Zealand":            {"primary": "#00247D", "text": "#FFFFFF"},
    "Norway":                 {"primary": "#EF2B2D", "text": "#FFFFFF"},
    "Panama":                 {"primary": "#DA121A", "text": "#FFFFFF"},
    "Paraguay":               {"primary": "#D52B1E", "text": "#FFFFFF"},
    "Portugal":               {"primary": "#006600", "text": "#FFFFFF"},
    "Qatar":                  {"primary": "#8D153A", "text": "#FFFFFF"},
    "Saudi Arabia":           {"primary": "#006C35", "text": "#FFFFFF"},
    "Scotland":               {"primary": "#003366", "text": "#FFFFFF"},
    "Senegal":                {"primary": "#00853F", "text": "#FDEF42"},
    "South Africa":           {"primary": "#007A4D", "text": "#FFB81C"},
    "South Korea":            {"primary": "#CD2E3A", "text": "#FFFFFF"},
    "Spain":                  {"primary": "#AA151B", "text": "#F1BF00"},
    "Sweden":                 {"primary": "#006AA7", "text": "#FECC02"},
    "Switzerland":            {"primary": "#FF0000", "text": "#FFFFFF"},
    "Tunisia":                {"primary": "#E70013", "text": "#FFFFFF"},
    "Turkey":                 {"primary": "#E30A17", "text": "#FFFFFF"},
    "United States":          {"primary": "#002868", "text": "#FFFFFF"},
    "Uruguay":                {"primary": "#75AADB", "text": "#FFFFFF"},
    "Uzbekistan":             {"primary": "#1EB53A", "text": "#FFFFFF"},
    "Algeria":                {"primary": "#006233", "text": "#FFFFFF"},
}
DEFAULT_COLOR = {"primary": "#1a1a2e", "text": "#FFFFFF"}


def gc(team):
    return TEAM_COLORS.get(team, DEFAULT_COLOR)


# ── CSS — only simple rules, no grid ──────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #060b18; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%);
        border-right: 2px solid #FFD700;
    }
    h1, h2, h3 { color: #FFD700 !important; }
    .team-box {
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .team-name-big {
        font-size: 22px;
        font-weight: 900;
        line-height: 1.2;
        font-family: Arial Black, sans-serif;
    }
    .elo-small {
        font-size: 12px;
        margin-top: 6px;
        opacity: 0.8;
        font-weight: bold;
    }
    .center-box {
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        background: rgba(0,0,0,0.4);
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 4px;
    }
    .vs-label {
        font-size: 28px;
        font-weight: 900;
        color: #FFD700;
    }
    .score-label {
        font-size: 44px;
        font-weight: 900;
        color: #00ff88;
        line-height: 1;
    }
    .xg-label {
        font-size: 13px;
        color: #FFD700;
        font-weight: bold;
    }
    .venue-label {
        font-size: 11px;
        color: rgba(255,255,255,0.5);
    }
    .divider {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.07);
        margin: 20px 0;
    }
    .match-label {
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.4);
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


@st.cache_data(ttl=3600)
def load_predictions():
    return pd.read_csv(OUTPUT_DIR / "match_predictions.csv", parse_dates=["date"])

@st.cache_data(ttl=3600)
def load_mc():
    return pd.read_csv(OUTPUT_DIR / "tournament_probabilities.csv")

@st.cache_data(ttl=3600)
def load_elo():
    return pd.read_csv(OUTPUT_DIR / "elo_ratings.csv")


def prob_bar(p_home, p_draw, p_away, home, away, key):
    hcolor = gc(home)["primary"]
    acolor = gc(away)["primary"]
    if hcolor == acolor:
        acolor = "#cc3333"
    fig = go.Figure()
    for val, color, label in [
        (p_home * 100, hcolor, f"{home}  {p_home:.0%}"),
        (p_draw * 100, "#555555", f"Draw  {p_draw:.0%}"),
        (p_away * 100, acolor, f"{away}  {p_away:.0%}"),
    ]:
        fig.add_trace(go.Bar(
            x=[val], y=[""], orientation="h",
            marker_color=color,
            marker_line_width=0,
            text=f"{val:.0f}%",
            textposition="inside" if val > 12 else "none",
            textfont=dict(size=13, color="white", family="Arial Black"),
            name=label,
            showlegend=True,
        ))
    fig.update_layout(
        barmode="stack", height=60,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.1,
            xanchor="center", x=0.5,
            font=dict(color="white", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(showticklabels=False, showgrid=False, range=[0, 100]),
        yaxis=dict(showticklabels=False),
    )
    return fig


def render_match_card(row):
    home, away = row["home_team"], row["away_team"]
    hc, ac = gc(home), gc(away)
    done = row["completed"]

    # Match label
    st.markdown(
        f"<div class='match-label'>⚽ FIFA WORLD CUP 2026 &nbsp;·&nbsp; {str(row['date'])[:10]}</div>",
        unsafe_allow_html=True
    )

    # Three columns: home | center | away
    col1, col2, col3 = st.columns([2, 1.5, 2])

    with col1:
        st.markdown(
            f"<div class='team-box' style='background:linear-gradient(135deg,{hc['primary']}dd,{hc['primary']}77)'>"
            f"<div class='team-name-big' style='color:{hc['text']}'>{home}</div>"
            f"<div class='elo-small' style='color:{hc['text']}'>Elo {row['home_elo']:.0f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    with col2:
        if done:
            st.markdown(
                f"<div class='center-box'>"
                f"<div class='score-label'>{int(row['actual_home_score'])} — {int(row['actual_away_score'])}</div>"
                f"<div style='color:rgba(255,255,255,0.4);font-size:10px;letter-spacing:1px'>FULL TIME</div>"
                f"<div class='venue-label'>📍 {row['city']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='center-box'>"
                f"<div class='vs-label'>VS</div>"
                f"<div class='xg-label'>xG {row['exp_home_goals']:.2f} — {row['exp_away_goals']:.2f}</div>"
                f"<div class='venue-label'>📍 {row['city']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    with col3:
        st.markdown(
            f"<div class='team-box' style='background:linear-gradient(225deg,{ac['primary']}dd,{ac['primary']}77);text-align:right'>"
            f"<div class='team-name-big' style='color:{ac['text']}'>{away}</div>"
            f"<div class='elo-small' style='color:{ac['text']}'>Elo {row['away_elo']:.0f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Probability bar
    st.plotly_chart(
        prob_bar(row["p_home_win"], row["p_draw"], row["p_away_win"],
                 home, away, key=f"pb_{home}_{away}_{row['date']}"),
        use_container_width=True,
        key=f"pb_{home}_{away}_{row['date']}",
    )

    # Metrics row
    c1, c2, c3 = st.columns(3)
    c1.metric(f"🟢 {home}", f"{row['p_home_win']:.1%}")
    c2.metric("⚪ Draw", f"{row['p_draw']:.1%}")
    c3.metric(f"🔴 {away}", f"{row['p_away_win']:.1%}")

    # Prediction / result badges
    bc1, bc2 = st.columns(2)
    with bc1:
        st.info(f"🤖 Predicted: **{row['predicted_result']}**")
    if done:
        with bc2:
            ok = row["predicted_result"] == row["actual_result"]
            if ok:
                st.success(f"✅ Actual: **{row['actual_result']}**")
            else:
                st.error(f"❌ Actual: **{row['actual_result']}**")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ 2026 WC PREDICTOR")
    st.markdown("*Elo · Poisson · Monte Carlo*")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📅 Today's Matches",
        "📊 All Predictions",
        "🏆 Tournament Odds",
        "📈 Elo Rankings",
        "🔍 Head to Head",
    ])
    st.markdown("---")
    st.markdown(f"**Updated:** {datetime.date.today().strftime('%b %d, %Y')}")
    st.markdown("**Matches:** 49,478 historical")
    st.markdown("**Simulations:** 10,000 Monte Carlo")
    st.markdown("**Model:** Elo + Poisson")


# ── Load data ──────────────────────────────────────────────────────────────────
try:
    predictions = load_predictions()
    mc = load_mc()
    elo_df = load_elo()
except FileNotFoundError:
    st.error("⚠️ Run `python main.py` first to generate output files.")
    st.stop()


# ══ PAGE 1: TODAY'S MATCHES ═══════════════════════════════════════════════════
if page == "📅 Today's Matches":
    st.title("⚽ 2026 FIFA World Cup Predictions")
    st.caption("AI-powered match predictions · Elo + Poisson model · 49,478 historical matches")

    all_dates = sorted(predictions["date"].dt.date.unique())
    selected_date = st.date_input(
        "Select match date",
        value=datetime.date.today(),
        min_value=min(all_dates),
        max_value=max(all_dates),
    )
    day_matches = predictions[predictions["date"].dt.date == selected_date]

    if len(day_matches) == 0:
        st.info("No matches on this date. Use the date picker to find match days.")
    else:
        st.markdown(f"**{selected_date.strftime('%A, %B %d, %Y')} · {len(day_matches)} match(es)**")
        st.markdown("---")
        for _, row in day_matches.iterrows():
            render_match_card(row)


# ══ PAGE 2: ALL PREDICTIONS ═══════════════════════════════════════════════════
elif page == "📊 All Predictions":
    st.title("📊 All 2026 WC Match Predictions")
    tab1, tab2 = st.tabs(["📅 Upcoming", "✅ Completed"])

    with tab1:
        up = predictions[~predictions["completed"]].copy()
        up["date"] = up["date"].dt.strftime("%Y-%m-%d")
        up["Home Win %"] = up["p_home_win"].apply(lambda x: f"{x:.1%}")
        up["Draw %"] = up["p_draw"].apply(lambda x: f"{x:.1%}")
        up["Away Win %"] = up["p_away_win"].apply(lambda x: f"{x:.1%}")
        st.dataframe(
            up[["date", "home_team", "away_team", "city",
                "Home Win %", "Draw %", "Away Win %",
                "exp_home_goals", "exp_away_goals", "predicted_result"]].rename(columns={
                "home_team": "Home", "away_team": "Away",
                "exp_home_goals": "xG Home", "exp_away_goals": "xG Away",
                "predicted_result": "Prediction",
            }),
            use_container_width=True, height=600,
        )

    with tab2:
        done = predictions[predictions["completed"]].copy()
        if len(done) == 0:
            st.info("No completed matches yet.")
        else:
            correct = (done["predicted_result"] == done["actual_result"]).sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Completed", len(done))
            c2.metric("Correct Predictions", correct)
            c3.metric("Model Accuracy", f"{correct / len(done) * 100:.1f}%")
            done["Score"] = done.apply(
                lambda r: f"{int(r['actual_home_score'])} - {int(r['actual_away_score'])}", axis=1)
            done["✓"] = (done["predicted_result"] == done["actual_result"]).map(
                {True: "✅", False: "❌"})
            done["date"] = done["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                done[["date", "home_team", "away_team", "Score",
                       "predicted_result", "actual_result", "✓"]].rename(columns={
                    "home_team": "Home", "away_team": "Away",
                    "predicted_result": "Predicted", "actual_result": "Actual",
                }),
                use_container_width=True,
            )


# ══ PAGE 3: TOURNAMENT ODDS ════════════════════════════════════════════════════
elif page == "🏆 Tournament Odds":
    st.title("🏆 World Cup Win Probabilities")
    st.caption("Based on 10,000 Monte Carlo tournament simulations")

    top_n = st.slider("Show top N teams", 10, 48, 24)
    chart_data = mc.head(top_n).copy()

    fig = go.Figure()
    for _, row in chart_data.iterrows():
        color = gc(row["team"])["primary"]
        fig.add_trace(go.Bar(
            x=[row["win_pct"]], y=[row["team"]], orientation="h",
            marker_color=color,
            marker_line_color="rgba(255,255,255,0.15)",
            marker_line_width=1,
            text=f"  {row['win_pct']:.2f}%",
            textposition="outside",
            textfont=dict(color="white", size=12),
            showlegend=False,
        ))

    fig.update_layout(
        height=max(500, top_n * 30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(6,11,24,1)",
        font=dict(color="white", family="Arial"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12, color="white")),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.05)",
            tickfont=dict(color="rgba(255,255,255,0.4)"),
            title=dict(text="Win Probability (%)", font=dict(color="#FFD700")),
        ),
        title=dict(text="2026 FIFA World Cup — Tournament Win Probability",
                   font=dict(color="#FFD700", size=16)),
        margin=dict(l=10, r=80, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Full Rankings")
        disp = mc[["rank", "team", "group", "win_pct", "elo"]].copy()
        disp["win_pct"] = disp["win_pct"].apply(lambda x: f"{x:.2f}%")
        disp["elo"] = disp["elo"].apply(lambda x: f"{x:.0f}")
        st.dataframe(disp.rename(columns={
            "rank": "#", "team": "Team", "group": "Group",
            "win_pct": "Win %", "elo": "Elo"
        }), use_container_width=True, height=500)

    with col2:
        st.markdown("### Group Favorites")
        for grp in sorted(mc["group"].unique()):
            top = mc[mc["group"] == grp].iloc[0]
            color = gc(top["team"])["primary"]
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:6px 14px;"
                f"margin:5px 0;border-radius:4px;background:rgba(255,255,255,0.03)'>"
                f"<b style='color:#FFD700'>Group {grp}:</b> "
                f"<span style='color:white'>{top['team']}</span> "
                f"<span style='color:rgba(255,255,255,0.5)'>{top['win_pct']:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True
            )


# ══ PAGE 4: ELO RANKINGS ══════════════════════════════════════════════════════
elif page == "📈 Elo Rankings":
    st.title("📈 Team Elo Ratings")
    st.caption("49,478 international matches weighted by recency and tournament importance")

    wc_list = mc["team"].tolist()
    wc_only = st.checkbox("WC 2026 teams only", value=True)
    disp_elo = elo_df[elo_df["team"].isin(wc_list)].copy() if wc_only else elo_df.copy()
    top_n = st.slider("Top N teams", 10, len(disp_elo), min(32, len(disp_elo)))
    cd = disp_elo.head(top_n).copy()

    fig = go.Figure()
    for _, row in cd.iterrows():
        color = gc(row["team"])["primary"]
        fig.add_trace(go.Bar(
            x=[row["elo"]], y=[row["team"]], orientation="h",
            marker_color=color,
            marker_line_color="rgba(255,255,255,0.15)",
            marker_line_width=1,
            text=f"  {row['elo']:.0f}",
            textposition="outside",
            textfont=dict(color="white", size=12),
            showlegend=False,
        ))

    fig.update_layout(
        height=max(500, top_n * 30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(6,11,24,1)",
        font=dict(color="white"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12, color="white")),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.05)",
            range=[cd["elo"].min() - 100, cd["elo"].max() + 150],
            tickfont=dict(color="rgba(255,255,255,0.4)"),
            title=dict(text="Elo Rating", font=dict(color="#FFD700")),
        ),
        title=dict(text="Team Elo Ratings — 2026 FIFA World Cup",
                   font=dict(color="#FFD700", size=16)),
        margin=dict(l=10, r=80, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ══ PAGE 5: HEAD TO HEAD ══════════════════════════════════════════════════════
elif page == "🔍 Head to Head":
    st.title("🔍 Head-to-Head Predictor")
    st.caption("Select any two teams for a predicted match outcome")

    all_teams = sorted(mc["team"].tolist())
    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", all_teams,
                              index=all_teams.index("Brazil") if "Brazil" in all_teams else 0)
    with col2:
        team_b = st.selectbox("Team B", all_teams,
                              index=all_teams.index("Argentina") if "Argentina" in all_teams else 1)

    is_neutral = st.checkbox("Neutral venue", value=True)

    if team_a == team_b:
        st.warning("Select two different teams.")
    else:
        match = predictions[
            ((predictions["home_team"] == team_a) & (predictions["away_team"] == team_b)) |
            ((predictions["home_team"] == team_b) & (predictions["away_team"] == team_a))
        ]

        if len(match) > 0:
            row = match.iloc[0]
            if row["home_team"] == team_a:
                p_home, p_draw, p_away = row["p_home_win"], row["p_draw"], row["p_away_win"]
                xg_home, xg_away = row["exp_home_goals"], row["exp_away_goals"]
                elo_a, elo_b = row["home_elo"], row["away_elo"]
            else:
                p_home, p_draw, p_away = row["p_away_win"], row["p_draw"], row["p_home_win"]
                xg_home, xg_away = row["exp_away_goals"], row["exp_home_goals"]
                elo_a, elo_b = row["away_elo"], row["home_elo"]
        else:
            from scipy.stats import poisson as sp_poisson
            elo_a_v = elo_df[elo_df["team"] == team_a]["elo"].values
            elo_b_v = elo_df[elo_df["team"] == team_b]["elo"].values
            elo_a = float(elo_a_v[0]) if len(elo_a_v) > 0 else 1400.0
            elo_b = float(elo_b_v[0]) if len(elo_b_v) > 0 else 1400.0
            adj = (elo_a - elo_b) / 200 * 0.3
            xg_home = max(0.3, 1.3 + adj) * (1.1 if not is_neutral else 1.0)
            xg_away = max(0.3, 1.3 - adj) * (0.95 if not is_neutral else 1.0)
            p_home = p_draw = p_away = 0.0
            for i in range(11):
                for j in range(11):
                    p = sp_poisson.pmf(i, xg_home) * sp_poisson.pmf(j, xg_away)
                    if i > j: p_home += p
                    elif i == j: p_draw += p
                    else: p_away += p
            t = p_home + p_draw + p_away
            p_home /= t; p_draw /= t; p_away /= t

        hc, ac = gc(team_a), gc(team_b)

        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(
                f"<div class='team-box' style='background:linear-gradient(135deg,{hc['primary']}cc,{hc['primary']}55)'>"
                f"<div class='team-name-big' style='color:{hc['text']}'>{team_a}</div>"
                f"<div class='elo-small' style='color:{hc['text']}'>Elo {elo_a:.0f}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                "<div style='height:110px;display:flex;align-items:center;"
                "justify-content:center;font-size:28px;font-weight:900;color:#FFD700'>VS</div>",
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"<div class='team-box' style='background:linear-gradient(225deg,{ac['primary']}cc,{ac['primary']}55);text-align:right'>"
                f"<div class='team-name-big' style='color:{ac['text']}'>{team_b}</div>"
                f"<div class='elo-small' style='color:{ac['text']}'>Elo {elo_b:.0f}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.plotly_chart(
            prob_bar(p_home, p_draw, p_away, team_a, team_b, key="h2h"),
            use_container_width=True, key="h2h_bar"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric(f"🟢 {team_a}", f"{p_home:.1%}")
        c2.metric("⚪ Draw", f"{p_draw:.1%}")
        c3.metric(f"🔴 {team_b}", f"{p_away:.1%}")

        st.markdown(
            f"**Expected Goals:** {team_a} `{xg_home:.2f}` — `{xg_away:.2f}` {team_b}"
        )

        probs = {team_a: p_home, "Draw": p_draw, team_b: p_away}
        winner = max(probs, key=probs.get)
        st.success(f"🤖 Model predicts: **{winner}**")
