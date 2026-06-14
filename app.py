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

# ── Flag image URLs (via flagcdn.com) ─────────────────────────────────────────
FLAG_CODES = {
    "Argentina": "ar", "Australia": "au", "Austria": "at",
    "Belgium": "be", "Bosnia and Herzegovina": "ba", "Brazil": "br",
    "Canada": "ca", "Cape Verde": "cv", "Colombia": "co",
    "Croatia": "hr", "Curaçao": "cw", "Czech Republic": "cz",
    "DR Congo": "cd", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de",
    "Ghana": "gh", "Haiti": "ht", "Iran": "ir",
    "Iraq": "iq", "Ivory Coast": "ci", "Japan": "jp",
    "Jordan": "jo", "Mexico": "mx", "Morocco": "ma",
    "Netherlands": "nl", "New Zealand": "nz", "Norway": "no",
    "Panama": "pa", "Paraguay": "py", "Portugal": "pt",
    "Qatar": "qa", "Saudi Arabia": "sa", "Scotland": "gb-sct",
    "Senegal": "sn", "South Africa": "za", "South Korea": "kr",
    "Spain": "es", "Sweden": "se", "Switzerland": "ch",
    "Tunisia": "tn", "Turkey": "tr", "United States": "us",
    "Uruguay": "uy", "Uzbekistan": "uz", "Algeria": "dz",
}


def flag_url(team):
    code = FLAG_CODES.get(team, "")
    if not code:
        return ""
    # Use flagcdn for standard codes, different URL for GB subdivisions
    if code.startswith("gb-"):
        return f"https://flagcdn.com/16x12/{code}.png"
    return f"https://flagcdn.com/16x12/{code}.png"


def flag_img(team, height=16):
    url = flag_url(team)
    if not url:
        return ""
    return f"<img src='{url}' height='{height}' style='vertical-align:middle;margin-right:5px;border-radius:2px;display:inline'>"


def flag(team):
    """For text contexts — returns img tag."""
    return flag_img(team)


def gc(team):
    return TEAM_COLORS.get(team, DEFAULT_COLOR)


def team_display(team, size=14):
    return f"{flag_img(team)}{team}" if team else "TBD"


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #060b18; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%);
        border-right: 2px solid #FFD700;
    }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; opacity: 1 !important; }
    section[data-testid="stSidebar"] .stRadio label p {
        color: #FFFFFF !important; font-size: 15px !important; font-weight: 600 !important;
    }
    h1, h2, h3 { color: #FFD700 !important; }
    .stApp p, .stApp span, .stApp label { color: #FFFFFF !important; }
    .stDateInput label p { color: #FFFFFF !important; }
    .stDateInput input { color: #111111 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 26px !important; }
    [data-testid="stMetricLabel"] { color: #CCCCCC !important; }
    .stMarkdown p { color: #FFFFFF !important; }
    .stApp strong { color: #FFD700 !important; }
    .team-box {
        border-radius: 12px; padding: 20px 16px; text-align: center;
        min-height: 110px; display: flex; flex-direction: column; justify-content: center;
    }
    .team-name-big { font-size: 22px; font-weight: 900; line-height: 1.2; font-family: Arial Black, sans-serif; }
    .elo-small { font-size: 12px; margin-top: 6px; opacity: 0.8; font-weight: bold; }
    .center-box {
        border-radius: 12px; padding: 16px; text-align: center;
        background: rgba(0,0,0,0.4); min-height: 110px;
        display: flex; flex-direction: column; justify-content: center; gap: 4px;
    }
    .vs-label { font-size: 28px; font-weight: 900; color: #FFD700; }
    .score-label { font-size: 44px; font-weight: 900; color: #00ff88; line-height: 1; }
    .xg-label { font-size: 13px; color: #FFD700; font-weight: bold; }
    .venue-label { font-size: 11px; color: rgba(255,255,255,0.5); }
    .match-label {
        font-size: 11px; font-weight: bold; letter-spacing: 2px;
        text-transform: uppercase; color: rgba(255,255,255,0.4); margin-bottom: 8px;
    }
    .divider { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 20px 0; }
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

@st.cache_data(ttl=3600)
def load_standings():
    try:
        return pd.read_csv(OUTPUT_DIR / "group_standings.csv")
    except FileNotFoundError:
        return None

@st.cache_data(ttl=3600)
def load_squads():
    try:
        return pd.read_csv(BASE_DIR / "international_results" / "squads_clubs.csv")
    except FileNotFoundError:
        return None


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
            marker_color=color, marker_line_width=0,
            text=f"{val:.0f}%",
            textposition="inside" if val > 12 else "none",
            textfont=dict(size=13, color="white", family="Arial Black"),
            name=label, showlegend=True,
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

    st.markdown(
        f"<div class='match-label'>⚽ FIFA WORLD CUP 2026 &nbsp;·&nbsp; {str(row['date'])[:10]}</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([2, 1.5, 2])

    with col1:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{hc['primary']}dd,{hc['primary']}77);"
            f"border-radius:12px;padding:20px 16px;text-align:center;min-height:110px;"
            f"display:flex;flex-direction:column;justify-content:center'>"
            f"<div style='font-size:22px;font-weight:900;color:{hc['text']}'>{flag_img(home)}{home}</div>"
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
            f"<div style='background:linear-gradient(225deg,{ac['primary']}dd,{ac['primary']}77);"
            f"border-radius:12px;padding:20px 16px;text-align:center;min-height:110px;"
            f"display:flex;flex-direction:column;justify-content:center'>"
            f"<div style='font-size:22px;font-weight:900;color:{ac['text']}'>{flag_img(away)}{away}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.plotly_chart(
        prob_bar(row["p_home_win"], row["p_draw"], row["p_away_win"],
                 home, away, key=f"pb_{home}_{away}_{row['date']}"),
        use_container_width=True,
        key=f"pb_{home}_{away}_{row['date']}",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(f"🟢 {home}", f"{row['p_home_win']:.1%}")
    c2.metric("⚪ Draw", f"{row['p_draw']:.1%}")
    c3.metric(f"🔴 {away}", f"{row['p_away_win']:.1%}")

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
    st.markdown(
        "<h2 style='color:#FFD700!important;font-family:Arial Black;letter-spacing:1px'>⚽ 2026 WC PREDICTOR</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='color:rgba(255,255,255,0.6)!important;font-size:13px'>Elo · Poisson · Monte Carlo</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    page = st.radio("Navigate", [
        "📅 Today's Matches",
        "📊 All Predictions",
        "🏆 Tournament Odds",
        "🗂️ Group Standings",
        "🔲 Bracket",
        "👥 Squads",
        "🔍 Head to Head",
    ])
    st.markdown("---")
    st.markdown(
        f"<p style='color:white!important;font-size:13px;line-height:2'>"
        f"<span style='color:#FFD700'>📅 Updated:</span> {datetime.date.today().strftime('%b %d, %Y')}<br>"
        f"<span style='color:#FFD700'>📊 Matches:</span> 49,478 historical<br>"
        f"<span style='color:#FFD700'>🎲 Simulations:</span> 10,000 Monte Carlo<br>"
        f"<span style='color:#FFD700'>🤖 Model:</span> Elo + Poisson"
        f"</p>",
        unsafe_allow_html=True
    )


# ── Load data ──────────────────────────────────────────────────────────────────
try:
    predictions = load_predictions()
    mc = load_mc()
    elo_df = load_elo()
    standings_df = load_standings()
    squads_df = load_squads()
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
        up["Home"] = up["home_team"]
        up["Away"] = up["away_team"]
        up["Home Win %"] = up["p_home_win"].apply(lambda x: f"{x:.1%}")
        up["Draw %"] = up["p_draw"].apply(lambda x: f"{x:.1%}")
        up["Away Win %"] = up["p_away_win"].apply(lambda x: f"{x:.1%}")
        st.dataframe(
            up[["date", "Home", "Away", "city",
                "Home Win %", "Draw %", "Away Win %",
                "exp_home_goals", "exp_away_goals", "predicted_result"]].rename(columns={
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
            done["Home"] = done["home_team"]
            done["Away"] = done["away_team"]
            st.dataframe(
                done[["date", "Home", "Away", "Score",
                       "predicted_result", "actual_result", "✓"]].rename(columns={
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
            x=[row["win_pct"]], y=[row["team"]],
            orientation="h",
            marker_color=color,
            marker_line_color="rgba(255,255,255,0.15)", marker_line_width=1,
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
                f"<div style='border-left:4px solid {color};padding:7px 14px;"
                f"margin:5px 0;border-radius:4px;background:rgba(255,255,255,0.03)'>"
                f"<b style='color:#FFD700'>Group {grp}:</b> "
                f"<span style='color:white'>{flag_img(top['team'])}{top['team']}</span> "
                f"<span style='color:rgba(255,255,255,0.5)'>{top['win_pct']:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True
            )


# ══ PAGE 4: GROUP STANDINGS ════════════════════════════════════════════════════
elif page == "🗂️ Group Standings":
    st.title("🗂️ 2026 FIFA World Cup — Group Standings")
    st.caption("Updated after each completed match · Top 2 qualify · Best 8 third-place teams also advance")

    if standings_df is None:
        st.error("Run `python main.py` first.")
        st.stop()

    from monte_carlo import WC_GROUPS

    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
    col_l1.markdown("🟢 **Q** = Qualified")
    col_l2.markdown("🟡 **M** = Maybe (best 3rd)")
    col_l3.markdown("🔴 **E** = Eliminated")
    col_l4.markdown("⚪ = In progress")
    st.markdown("---")

    groups = sorted(WC_GROUPS.keys())
    for i in range(0, len(groups), 2):
        cols = st.columns(2)
        for j, grp in enumerate(groups[i:i+2]):
            with cols[j]:
                grp_df = standings_df[standings_df["group"] == grp].copy()
                grp_color = gc(grp_df.iloc[0]["team"])["primary"] if len(grp_df) > 0 else "#FFD700"

                st.markdown(
                    f"<div style='border-left:4px solid {grp_color};padding:4px 12px;margin-bottom:8px'>"
                    f"<span style='font-size:18px;font-weight:900;color:#FFD700'>Group {grp}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                rows_html = ""
                for _, tr in grp_df.iterrows():
                    team = tr["team"]
                    tc = gc(team)
                    q = tr["qualified"]

                    if q == "Q":
                        status, row_bg = "🟢", "rgba(0,200,100,0.08)"
                    elif q == "M":
                        status, row_bg = "🟡", "rgba(255,200,0,0.08)"
                    elif q == "E":
                        status, row_bg = "🔴", "rgba(200,0,0,0.08)"
                    else:
                        status, row_bg = "⚪", "rgba(255,255,255,0.03)"

                    gd_val = int(tr['gd'])
                    gd_str = f"+{gd_val}" if gd_val > 0 else str(gd_val)

                    rows_html += f"""
                    <tr style='background:{row_bg}'>
                        <td style='padding:8px 6px'>
                            {flag_img(team, height=14)}
                            <b style='color:white'>{team}</b>
                        </td>
                        <td style='text-align:center;color:white'>{int(tr['played'])}</td>
                        <td style='text-align:center;color:#2ecc71;font-weight:bold'>{int(tr['won'])}</td>
                        <td style='text-align:center;color:#f39c12'>{int(tr['drawn'])}</td>
                        <td style='text-align:center;color:#e74c3c'>{int(tr['lost'])}</td>
                        <td style='text-align:center;color:white'>{int(tr['gf'])}</td>
                        <td style='text-align:center;color:white'>{int(tr['ga'])}</td>
                        <td style='text-align:center;color:#FFD700;font-weight:bold'>{gd_str}</td>
                        <td style='text-align:center;color:#FFD700;font-size:16px;font-weight:900'>{int(tr['pts'])}</td>
                        <td style='text-align:center;font-size:14px'>{status}</td>
                    </tr>"""

                st.markdown(f"""
                <table style='width:100%;border-collapse:collapse;
                              background:rgba(255,255,255,0.02);
                              border-radius:8px;font-size:13px;margin-bottom:20px'>
                    <thead>
                        <tr style='background:rgba(255,255,255,0.07)'>
                            <th style='padding:8px 6px;text-align:left;color:#FFD700'>Team</th>
                            <th style='text-align:center;color:#FFD700'>P</th>
                            <th style='text-align:center;color:#2ecc71'>W</th>
                            <th style='text-align:center;color:#f39c12'>D</th>
                            <th style='text-align:center;color:#e74c3c'>L</th>
                            <th style='text-align:center;color:#FFD700'>GF</th>
                            <th style='text-align:center;color:#FFD700'>GA</th>
                            <th style='text-align:center;color:#FFD700'>GD</th>
                            <th style='text-align:center;color:#FFD700'>Pts</th>
                            <th style='text-align:center;color:#FFD700'>Q</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                """, unsafe_allow_html=True)


# ══ PAGE 5: BRACKET ═══════════════════════════════════════════════════════════
elif page == "🔲 Bracket":
    st.title("🔲 2026 FIFA World Cup — Predicted Knockout Bracket")
    st.caption(
        "Bracket seeded using the top 16 teams by Monte Carlo win probability, in standard "
        "tournament seeding (so the top 2 favorites can only meet in the Final). "
        "Boxes are blank like the official template — the two predicted teams for each "
        "match are shown below it."
    )

    # ── Build bracket data from top 16 MC teams ────────────────────────────────
    top16_df = mc.head(16).reset_index(drop=True)
    top16 = top16_df["team"].tolist()
    mc_dict = dict(zip(mc["team"], mc["win_probability"]))

    if len(top16) < 16:
        st.warning("Not enough teams in tournament_probabilities.csv to build a 16-team bracket.")
        st.stop()

    # Standard seeding pairs (0-indexed seed positions)
    left_pairs = [(0, 15), (7, 8), (4, 11), (3, 12)]
    right_pairs = [(1, 14), (6, 9), (2, 13), (5, 10)]

    left16 = [(top16[i], top16[j]) for i, j in left_pairs]
    right16 = [(top16[i], top16[j]) for i, j in right_pairs]

    def pred(matchup):
        a, b = matchup
        return a if mc_dict.get(a, 0) >= mc_dict.get(b, 0) else b

    left_qf = [(pred(left16[0]), pred(left16[1])), (pred(left16[2]), pred(left16[3]))]
    right_qf = [(pred(right16[0]), pred(right16[1])), (pred(right16[2]), pred(right16[3]))]

    left_sf = (pred(left_qf[0]), pred(left_qf[1]))
    right_sf = (pred(right_qf[0]), pred(right_qf[1]))

    final_match = (pred(left_sf), pred(right_sf))
    champion = pred(final_match)

    # ── SVG layout constants ────────────────────────────────────────────────────
    BOX_W = 130
    BOX_H = 40
    COL_SPACING = 215
    TOP_PAD = 46
    R16_SPACING = 92

    # R16 box vertical centers (4 per half)
    r16_centers = [TOP_PAD + BOX_H / 2 + i * R16_SPACING for i in range(4)]  # 4 values
    qf_centers = [
        (r16_centers[0] + r16_centers[1]) / 2,
        (r16_centers[2] + r16_centers[3]) / 2,
    ]
    sf_center = (qf_centers[0] + qf_centers[1]) / 2
    final_center = sf_center

    SVG_H = r16_centers[-1] + BOX_H / 2 + 56
    SVG_W = 6 * COL_SPACING + BOX_W

    col_x = [i * COL_SPACING for i in range(7)]  # 0..6

    def box_rect(x, cy, highlight=False):
        fill = "#1a2438" if not highlight else "#2a1f0a"
        stroke = "#FFD700" if highlight else "rgba(255,255,255,0.25)"
        sw = 2 if highlight else 1
        return (
            f"<rect x='{x}' y='{cy - BOX_H/2:.1f}' width='{BOX_W}' height='{BOX_H}' "
            f"rx='6' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"
        )

    def box_label(x, cy, text):
        return (
            f"<text x='{x + BOX_W/2}' y='{cy + 3:.1f}' text-anchor='middle' "
            f"font-size='10' fill='rgba(255,255,255,0.35)' "
            f"font-family='Arial' letter-spacing='1'>{text}</text>"
        )

    def team_label(x, y, team, size=11):
        color = gc(team)["primary"]
        return (
            f"<text x='{x + BOX_W/2}' y='{y:.1f}' text-anchor='middle' "
            f"font-size='{size}' font-family='Arial' font-weight='bold'>"
            f"<tspan fill='{color}'>\u25A0 </tspan>"
            f"<tspan fill='#ffffff'>{team}</tspan>"
            f"</text>"
        )

    def hline(x1, y1, x2, y2):
        return f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='rgba(255,215,0,0.4)' stroke-width='1.5'/>"

    parts = []
    parts.append(
        f"<rect x='0' y='0' width='{SVG_W}' height='{SVG_H}' rx='12' fill='#0a0f1e'/>"
    )

    # Round labels
    label_y = 20
    parts.append(f"<text x='{col_x[0]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>ROUND OF 16</text>")
    parts.append(f"<text x='{col_x[1]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>QUARTERFINALS</text>")
    parts.append(f"<text x='{col_x[2]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>SEMIFINALS</text>")
    parts.append(f"<text x='{col_x[3]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='13' fill='#FFD700' font-weight='900' letter-spacing='2'>FINAL</text>")
    parts.append(f"<text x='{col_x[4]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>SEMIFINALS</text>")
    parts.append(f"<text x='{col_x[5]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>QUARTERFINALS</text>")
    parts.append(f"<text x='{col_x[6]+BOX_W/2}' y='{label_y}' text-anchor='middle' font-size='12' fill='#FFD700' font-weight='bold' letter-spacing='2'>ROUND OF 16</text>")

    # ── R16 LEFT (col 0) ─────────────────────────────────────────────────────
    for i, cy in enumerate(r16_centers):
        x = col_x[0]
        parts.append(box_rect(x, cy))
        parts.append(box_label(x, cy, f"R16 · M{i+1}"))
        ta, tb = left16[i]
        parts.append(team_label(x, cy + BOX_H/2 + 14, ta))
        parts.append(team_label(x, cy + BOX_H/2 + 28, tb))

    # ── R16 RIGHT (col 6) ────────────────────────────────────────────────────
    for i, cy in enumerate(r16_centers):
        x = col_x[6]
        parts.append(box_rect(x, cy))
        parts.append(box_label(x, cy, f"R16 · M{i+5}"))
        ta, tb = right16[i]
        parts.append(team_label(x, cy + BOX_H/2 + 14, ta))
        parts.append(team_label(x, cy + BOX_H/2 + 28, tb))

    # ── QF LEFT (col 1) ──────────────────────────────────────────────────────
    for i, cy in enumerate(qf_centers):
        x = col_x[1]
        parts.append(box_rect(x, cy))
        parts.append(box_label(x, cy, f"QF · {i+1}"))
        ta, tb = left_qf[i]
        parts.append(team_label(x, cy + BOX_H/2 + 14, ta))
        parts.append(team_label(x, cy + BOX_H/2 + 28, tb))

    # ── QF RIGHT (col 5) ─────────────────────────────────────────────────────
    for i, cy in enumerate(qf_centers):
        x = col_x[5]
        parts.append(box_rect(x, cy))
        parts.append(box_label(x, cy, f"QF · {i+3}"))
        ta, tb = right_qf[i]
        parts.append(team_label(x, cy + BOX_H/2 + 14, ta))
        parts.append(team_label(x, cy + BOX_H/2 + 28, tb))

    # ── SF LEFT (col 2) ──────────────────────────────────────────────────────
    parts.append(box_rect(col_x[2], sf_center))
    parts.append(box_label(col_x[2], sf_center, "SF · 1"))
    parts.append(team_label(col_x[2], sf_center + BOX_H/2 + 14, left_sf[0]))
    parts.append(team_label(col_x[2], sf_center + BOX_H/2 + 28, left_sf[1]))

    # ── SF RIGHT (col 4) ─────────────────────────────────────────────────────
    parts.append(box_rect(col_x[4], sf_center))
    parts.append(box_label(col_x[4], sf_center, "SF · 2"))
    parts.append(team_label(col_x[4], sf_center + BOX_H/2 + 14, right_sf[0]))
    parts.append(team_label(col_x[4], sf_center + BOX_H/2 + 28, right_sf[1]))

    # ── FINAL (col 3) ────────────────────────────────────────────────────────
    parts.append(box_rect(col_x[3], final_center, highlight=True))
    parts.append(box_label(col_x[3], final_center, "🏆 FINAL"))
    parts.append(team_label(col_x[3], final_center + BOX_H/2 + 16, final_match[0], size=12))
    parts.append(team_label(col_x[3], final_center + BOX_H/2 + 32, final_match[1], size=12))
    parts.append(
        f"<text x='{col_x[3]+BOX_W/2}' y='{final_center + BOX_H/2 + 50}' text-anchor='middle' "
        f"font-size='11' fill='#00ff88' font-weight='900' font-family='Arial'>"
        f"\u2605 {champion}</text>"
    )

    # ── Connectors: LEFT side R16 -> QF -> SF -> Final ──────────────────────────
    def connect_pair(x_from, yA, yB, x_to, yC):
        """Connect two boxes (centers yA, yB) at x_from+BOX_W to one box (center yC) at x_to."""
        out = []
        xmid = x_from + BOX_W + (x_to - (x_from + BOX_W)) / 2
        out.append(hline(x_from + BOX_W, yA, xmid, yA))
        out.append(hline(x_from + BOX_W, yB, xmid, yB))
        out.append(hline(xmid, yA, xmid, yB))
        out.append(hline(xmid, yC, x_to, yC))
        return out

    def connect_pair_mirrored(x_from, yA, yB, x_to, yC):
        """Mirrored version: x_from is to the RIGHT of x_to."""
        out = []
        xmid = x_to + BOX_W + (x_from - (x_to + BOX_W)) / 2
        out.append(hline(x_from, yA, xmid, yA))
        out.append(hline(x_from, yB, xmid, yB))
        out.append(hline(xmid, yA, xmid, yB))
        out.append(hline(xmid, yC, x_to + BOX_W, yC))
        return out

    # R16 -> QF (left)
    parts += connect_pair(col_x[0], r16_centers[0], r16_centers[1], col_x[1], qf_centers[0])
    parts += connect_pair(col_x[0], r16_centers[2], r16_centers[3], col_x[1], qf_centers[1])
    # QF -> SF (left)
    parts += connect_pair(col_x[1], qf_centers[0], qf_centers[1], col_x[2], sf_center)
    # SF -> Final (left, straight since same y)
    parts.append(hline(col_x[2] + BOX_W, sf_center, col_x[3], final_center))

    # ── Connectors: RIGHT side R16 -> QF -> SF -> Final (mirrored) ──────────────
    # R16 -> QF (right)
    parts += connect_pair_mirrored(col_x[6], r16_centers[0], r16_centers[1], col_x[5], qf_centers[0])
    parts += connect_pair_mirrored(col_x[6], r16_centers[2], r16_centers[3], col_x[5], qf_centers[1])
    # QF -> SF (right)
    parts += connect_pair_mirrored(col_x[5], qf_centers[0], qf_centers[1], col_x[4], sf_center)
    # SF -> Final (right, straight)
    parts.append(hline(col_x[4], sf_center, col_x[3] + BOX_W, final_center))

    svg_body = "".join(parts)
    svg_html = f"""
    <div style='overflow-x:auto;padding:8px 0 16px;border-radius:12px;background:#0a0f1e'>
        <svg width='{SVG_W}' height='{SVG_H}' viewBox='0 0 {SVG_W} {SVG_H}'
             xmlns='http://www.w3.org/2000/svg' style='display:block;margin:0 auto'>
            {svg_body}
        </svg>
    </div>
    """

    st.markdown(svg_html, unsafe_allow_html=True)
    st.markdown(
        "<p style='color:rgba(255,255,255,0.4);font-size:11px;text-align:center;margin-top:6px'>"
        "\u25A0 = team color &nbsp;·&nbsp; \u2605 = predicted champion &nbsp;·&nbsp; "
        "Scroll horizontally on smaller screens</p>",
        unsafe_allow_html=True
    )

    # ── Podium ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🥇 Predicted Podium")
    top3 = mc.head(3)
    p_cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, ((_, row), col) in enumerate(zip(top3.iterrows(), p_cols)):
        tc = gc(row["team"])
        with col:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,{tc['primary']}cc,{tc['primary']}44);"
                f"border-radius:12px;padding:20px;text-align:center;border:1px solid {tc['primary']}'>"
                f"<div style='font-size:28px'>{medals[i]}</div>"
                f"<div style='margin:4px 0'>{flag_img(row['team'], height=20)}</div>"
                f"<div style='font-size:18px;font-weight:900;color:{tc['text']};margin:6px 0'>{row['team']}</div>"
                f"<div style='font-size:22px;font-weight:bold;color:#FFD700'>{row['win_pct']:.1f}%</div>"
                f"<div style='font-size:11px;color:rgba(255,255,255,0.5)'>win probability</div>"
                f"</div>",
                unsafe_allow_html=True
            )


# ══ PAGE 6: SQUADS ════════════════════════════════════════════════════════════
elif page == "👥 Squads":
    st.title("👥 2026 FIFA World Cup — Squads")
    st.caption("Full 26-player rosters with current club affiliations for every team")

    if squads_df is None:
        st.error("squads_clubs.csv not found. Run `python generate_squads_csv.py` and place "
                 "the output in `international_results/`.")
        st.stop()

    all_teams = sorted(squads_df["team"].unique())
    sel_team = st.selectbox(
        "Select a team",
        all_teams,
        format_func=lambda t: f"{t} (Group {squads_df[squads_df['team']==t]['group'].iloc[0]})",
    )

    team_df = squads_df[squads_df["team"] == sel_team]
    tc = gc(sel_team)
    group = team_df["group"].iloc[0]
    featured_row = team_df[team_df["featured"] == "Y"]
    featured_name = featured_row["player"].iloc[0] if len(featured_row) else None
    featured_club = featured_row["club"].iloc[0] if len(featured_row) else None

    # ── Header banner ────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,{tc['primary']}dd,{tc['primary']}33);"
        f"border-radius:14px;padding:24px 28px;margin-bottom:16px;"
        f"border:1px solid {tc['primary']}'>"
        f"<div style='display:flex;align-items:center;gap:14px'>"
        f"{flag_img(sel_team, height=36)}"
        f"<div>"
        f"<div style='font-size:26px;font-weight:900;color:{tc['text']}'>{sel_team}</div>"
        f"<div style='font-size:13px;color:rgba(255,255,255,0.65)'>Group {group} · 2026 FIFA World Cup</div>"
        f"</div>"
        f"</div>"
        + (
            f"<div style='margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.15)'>"
            f"<span style='font-size:11px;color:#FFD700;letter-spacing:2px;font-weight:bold'>★ FEATURED PLAYER</span><br>"
            f"<span style='font-size:18px;font-weight:900;color:white'>{featured_name}</span> "
            f"<span style='font-size:13px;color:rgba(255,255,255,0.6)'>· {featured_club}</span>"
            f"</div>"
            if featured_name else ""
        )
        + "</div>",
        unsafe_allow_html=True
    )

    # ── Squad by position ────────────────────────────────────────────────────
    POSITION_LABELS = {
        "GK": "🧤 Goalkeepers",
        "DEF": "🛡️ Defenders",
        "MID": "⚙️ Midfielders",
        "FWD": "⚡ Forwards",
    }

    cols = st.columns(2)
    for i, pos in enumerate(["GK", "DEF", "MID", "FWD"]):
        pos_df = team_df[team_df["position"] == pos]
        if len(pos_df) == 0:
            continue
        with cols[i % 2]:
            rows_html = ""
            for _, r in pos_df.iterrows():
                star = " ★" if r["featured"] == "Y" else ""
                name_color = "#FFD700" if r["featured"] == "Y" else "#FFFFFF"
                rows_html += (
                    f"<tr>"
                    f"<td style='padding:6px 10px;color:{name_color};font-weight:{'900' if r['featured']=='Y' else '500'}'>"
                    f"{r['player']}{star}</td>"
                    f"<td style='padding:6px 10px;text-align:right;color:rgba(255,255,255,0.6);font-size:13px'>{r['club']}</td>"
                    f"</tr>"
                )
            st.markdown(
                f"<div style='margin-bottom:18px'>"
                f"<div style='font-size:14px;font-weight:bold;color:#FFD700;letter-spacing:1px;"
                f"margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid rgba(255,215,0,0.3)'>"
                f"{POSITION_LABELS[pos]} ({len(pos_df)})</div>"
                f"<table style='width:100%;border-collapse:collapse;font-size:14px'>"
                f"{rows_html}"
                f"</table>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ── Club distribution ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🌍 Club Breakdown")
    club_counts = team_df["club"].value_counts()
    multi_club = club_counts[club_counts > 1]
    if len(multi_club) > 0:
        chips = "".join(
            f"<span style='display:inline-block;background:rgba(255,215,0,0.12);"
            f"border:1px solid rgba(255,215,0,0.3);border-radius:20px;padding:5px 14px;"
            f"margin:3px;font-size:13px;color:white'>{club} <b style='color:#FFD700'>×{n}</b></span>"
            for club, n in multi_club.items()
        )
        st.markdown(
            f"<p style='color:rgba(255,255,255,0.6);font-size:12px;margin-bottom:8px'>"
            f"Clubs with multiple players in this squad:</p>{chips}",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:13px'>"
            "Every player in this squad plays for a different club.</p>",
            unsafe_allow_html=True
        )


# ══ PAGE 7: HEAD TO HEAD ══════════════════════════════════════════════════════
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
                f"<div style='background:linear-gradient(135deg,{hc['primary']}cc,{hc['primary']}55);"
                f"border-radius:12px;padding:20px 16px;text-align:center;min-height:110px;"
                f"display:flex;flex-direction:column;justify-content:center'>"
                f"<div style='font-size:22px;font-weight:900;color:{hc['text']}'>{flag_img(team_a)}{team_a}</div>"
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
                f"<div style='background:linear-gradient(225deg,{ac['primary']}cc,{ac['primary']}55);"
                f"border-radius:12px;padding:20px 16px;text-align:center;min-height:110px;"
                f"display:flex;flex-direction:column;justify-content:center'>"
                f"<div style='font-size:22px;font-weight:900;color:{ac['text']}'>{flag_img(team_b)}{team_b}</div>"
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
            f"**Expected Goals:** {team_a} `{xg_home:.2f}` — "
            f"`{xg_away:.2f}` {team_b}"
        )

        probs = {team_a: p_home, "Draw": p_draw, team_b: p_away}
        winner = max(probs, key=probs.get)
        st.success(f"🤖 Model predicts: **{winner}**")
