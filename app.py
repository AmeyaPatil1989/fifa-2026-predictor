import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from urllib.parse import quote
import datetime
from background_image import BG_IMAGE_B64
from live_scores import fetch_live_scores, fetch_match_events, fetch_tournament_scores
from live_predictions import live_win_probability, parse_minutes_elapsed
from live_standings import compute_live_group_standings

st.set_page_config(
    page_title="2026 FIFA World Cup Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Click-to-navigate routing ───────────────────────────────────────────────
# Clicking a team name anywhere (HTML link with ?team=... or a chart point)
# routes here, sets the selected team, and switches to the Squads page with that team selected.
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📅 Today's Matches"
if "selected_team" not in st.session_state:
    st.session_state.selected_team = None

_qp = st.query_params
if "team" in _qp:
    st.session_state.selected_team = _qp["team"]
    st.session_state.nav_page = "👥 Squads"
    st.query_params.clear()
    st.rerun()

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


def soccer_ball(size=24, inline_style="vertical-align:-4px;margin-right:6px"):
    """Original SVG soccer ball (classic pentagon/hexagon pattern) — generic,
    not a depiction of any official/licensed match ball. Safe to use anywhere
    emoji was used for a more polished look."""
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 100 100' "
        f"style='{inline_style}' xmlns='http://www.w3.org/2000/svg'>"
        f"<circle cx='50' cy='50' r='48' fill='#FFFFFF' stroke='#1a1a1a' stroke-width='3'/>"
        f"<polygon points='50,30 62,38 58,52 42,52 38,38' fill='#1a1a1a'/>"
        f"<path d='M 50,30 L 62,38 M 50,30 L 38,38 M 62,38 L 58,52 M 38,38 L 42,52 M 58,52 L 42,52' "
        f"stroke='#1a1a1a' stroke-width='2.5' fill='none'/>"
        f"<path d='M 50,30 L 50,8' stroke='#1a1a1a' stroke-width='2.5'/>"
        f"<path d='M 62,38 L 80,30' stroke='#1a1a1a' stroke-width='2.5'/>"
        f"<path d='M 38,38 L 20,30' stroke='#1a1a1a' stroke-width='2.5'/>"
        f"<path d='M 58,52 L 68,68' stroke='#1a1a1a' stroke-width='2.5'/>"
        f"<path d='M 42,52 L 32,68' stroke='#1a1a1a' stroke-width='2.5'/>"
        f"<path d='M 50,8 A 42,42 0 0 1 80,30' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 50,8 A 42,42 0 0 0 20,30' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 92,50 A 42,42 0 0 1 68,68' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 8,50 A 42,42 0 0 0 32,68' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 80,30 A 42,42 0 0 1 92,50' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 20,30 A 42,42 0 0 0 8,50' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 68,68 A 42,42 0 0 1 50,92' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"<path d='M 32,68 A 42,42 0 0 0 50,92' fill='none' stroke='#1a1a1a' stroke-width='2'/>"
        f"</svg>"
    )


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


def team_link(team, label=None, color="#FFFFFF", underline=True, weight="inherit"):
    """Returns an <a> tag that navigates to this team's Squads page on click."""
    if not team:
        return label or "TBD"
    label = label if label is not None else team
    style = f"color:{color};text-decoration:none;cursor:pointer;font-weight:{weight};"
    if underline:
        style += f"border-bottom:1px dotted {color};"
    return f"<a href='?team={quote(team)}' target='_self' style='{style}'>{label}</a>"


POSITION_LABELS = {
    "GK": "🧤 Goalkeepers",
    "DEF": "🛡️ Defenders",
    "MID": "⚙️ Midfielders",
    "FWD": "⚡ Forwards",
}


def render_team_squad(team_df, sel_team, show_header=True):
    """Renders the team header banner (optional), star players, squad by position,
    and club breakdown. Used by the Squads page."""
    tc = gc(sel_team)
    group = team_df["group"].iloc[0]
    star_rows = team_df[team_df["star_rank"] != ""].sort_values("star_rank")

    star_chips = ""
    for _, sr in star_rows.iterrows():
        star_chips += (
            f"<div style='margin-top:8px'>"
            f"<span style='font-size:17px;font-weight:900;color:white'>{sr['player']}</span> "
            f"<span style='font-size:13px;color:rgba(255,255,255,0.6)'>· {sr['club']}</span>"
            f"</div>"
        )

    if show_header:
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
                f"<span style='font-size:11px;color:#FFD700;letter-spacing:2px;font-weight:bold'>★ PLAYERS TO WATCH</span>"
                f"{star_chips}"
                f"</div>"
                if len(star_rows) else ""
            )
            + "</div>",
            unsafe_allow_html=True
        )
    elif len(star_rows):
        st.markdown(
            f"<div style='margin-bottom:16px'>"
            f"<span style='font-size:11px;color:#FFD700;letter-spacing:2px;font-weight:bold'>★ PLAYERS TO WATCH</span>"
            f"{star_chips}"
            f"</div>",
            unsafe_allow_html=True
        )

    # ── Squad by position ────────────────────────────────────────────────────
    cols = st.columns(2)
    for i, pos in enumerate(["GK", "DEF", "MID", "FWD"]):
        pos_df = team_df[team_df["position"] == pos]
        if len(pos_df) == 0:
            continue
        with cols[i % 2]:
            rows_html = ""
            for _, r in pos_df.iterrows():
                is_star = r["star_rank"] != ""
                star = " ★" if is_star else ""
                name_color = "#FFD700" if is_star else "#FFFFFF"
                rows_html += (
                    f"<tr>"
                    f"<td style='padding:6px 10px;color:{name_color};font-weight:{'900' if is_star else '500'}'>"
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


# ── Background image (stadium photo, dark overlay for text readability) ────────
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(6,11,24,0.82), rgba(6,11,24,0.82)),
                           url("data:image/jpeg;base64,{BG_IMAGE_B64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    header[data-testid="stHeader"] {
        background-color: #060b18 !important;
    }
    [data-testid="stToolbar"] {
        background-color: #060b18 !important;
    }
    [data-testid="stDecoration"] {
        background-color: #060b18 !important;
    }
    /* Sidebar collapse / expand toggle (the « » arrow) */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        background-color: #1b263b !important;
        border: 1px solid #FFD700 !important;
        border-radius: 6px !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg {
        fill: #FFD700 !important;
        color: #FFD700 !important;
    }
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
def load_scorers():
    try:
        return pd.read_csv(OUTPUT_DIR / "wc2026_scorers.csv")
    except FileNotFoundError:
        return None

@st.cache_data(ttl=60)
def load_live_scores(dates=None):
    """
    Cached for 60s so we don't hit ESPN on every rerun, but stay close to live.
    `dates`: optional ESPN-format date string (e.g. "20260618") to fetch a
    specific past day instead of today's default scoreboard. Cached separately
    per `dates` value since Streamlit's cache keys on all arguments.
    """
    return fetch_live_scores(dates=dates)

@st.cache_data(ttl=600)
def load_tournament_scores():
    """
    Cached for 10 minutes. Covers the WHOLE tournament date range, not just
    today — used as a bridge for any date being viewed (including past dates)
    when our own match_predictions.csv hasn't been synced yet by the daily
    pipeline. Longer cache than the today-only loader since this is mostly
    used to backfill already-finished matches, not track a live in-progress one.
    """
    return fetch_tournament_scores()

@st.cache_data(ttl=60)
def load_match_events(event_id):
    """Cached for 60s, keyed by event_id so each live match gets its own cache entry."""
    return fetch_match_events(event_id)

@st.cache_data(ttl=3600)
def load_squads():
    try:
        return pd.read_csv(
            BASE_DIR / "international_results" / "squads_clubs.csv",
            dtype={"star_rank": str},
            keep_default_na=False,
        )
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


EVENT_TYPE_STYLE = {
    "goal": ("⚽", "#00ff88"),
    "penalty - scored": ("⚽", "#00ff88"),
    "penalty - missed": ("❌", "#ff4d4d"),
    "yellow card": ("🟨", "#FFD700"),
    "red card": ("🟥", "#ff4d4d"),
    "substitution": ("🔄", "rgba(255,255,255,0.6)"),
    "kickoff": ("▶️", "rgba(255,255,255,0.5)"),
    "halftime": ("⏸️", "#FFD700"),
    "start 2nd half": ("▶️", "rgba(255,255,255,0.5)"),
    "end regular time": ("⏹️", "#FFD700"),
    "start delay": ("⏱️", "rgba(255,255,255,0.4)"),
    "end delay": ("⏱️", "rgba(255,255,255,0.4)"),
}


def render_live_feed(event_id, home, away):
    events = load_match_events(event_id)
    if not events:
        return

    rows_html = ""
    # Newest first: reverse chronological order
    for ev in reversed(events):
        icon, color = EVENT_TYPE_STYLE.get(ev["type"].lower(), ("•", "rgba(255,255,255,0.5)"))
        minute = ev["minute"] or ""
        text = ev["text"]
        rows_html += (
            f"<div style='display:flex;gap:10px;padding:7px 4px;"
            f"border-bottom:1px solid rgba(255,255,255,0.06)'>"
            f"<div style='min-width:38px;color:rgba(255,255,255,0.4);font-size:12px;font-weight:700'>{minute}</div>"
            f"<div style='min-width:20px'>{icon}</div>"
            f"<div style='color:{color};font-size:13px;flex:1'>{text}</div>"
            f"</div>"
        )

    st.markdown(
        f"<div style='margin-top:10px;margin-bottom:6px;color:#FFD700;font-size:12px;"
        f"font-weight:bold;letter-spacing:1px'>📋 LIVE COMMENTARY — {home} vs {away}</div>"
        f"<div style='max-height:280px;overflow-y:auto;background:rgba(255,255,255,0.02);"
        f"border-radius:8px;padding:6px 12px;border:1px solid rgba(255,255,255,0.08)'>"
        f"{rows_html}"
        f"</div>",
        unsafe_allow_html=True
    )


def render_match_card(row, live_data=None):
    home, away = row["home_team"], row["away_team"]
    hc, ac = gc(home), gc(away)
    done = row["completed"]
    live = live_data.get((home, away)) if live_data else None
    is_live_now = live is not None and live["status"] == "in"

    live_probs = None
    if is_live_now:
        minutes_elapsed = parse_minutes_elapsed(live.get("clock"))
        if minutes_elapsed is not None and live["home_score"] is not None:
            live_probs = live_win_probability(
                exp_home_goals_full=row["exp_home_goals"],
                exp_away_goals_full=row["exp_away_goals"],
                current_home_score=live["home_score"],
                current_away_score=live["away_score"],
                minutes_elapsed=minutes_elapsed,
            )
    # Fall back to pre-match probabilities if live recalculation wasn't
    # possible (e.g. halftime, where ESPN's clock isn't a parseable minute)
    display_p_home = live_probs["p_home_win"] if live_probs else row["p_home_win"]
    display_p_draw = live_probs["p_draw"] if live_probs else row["p_draw"]
    display_p_away = live_probs["p_away_win"] if live_probs else row["p_away_win"]
    # ESPN says finished but our own pipeline hasn't picked up the result yet
    # (daily_update.bat hasn't run since kickoff) — show ESPN's final score
    # rather than falling through to the pre-match "VS / xG" view.
    espn_finished_not_yet_synced = (
        not done and live is not None and live["status"] == "post"
        and live["home_score"] is not None
    )

    st.markdown(
        f"<div class='match-label'>{soccer_ball(14, 'vertical-align:-2px;margin-right:4px')} FIFA WORLD CUP 2026 &nbsp;·&nbsp; {str(row['date'])[:10]}"
        + ("&nbsp;·&nbsp;<span style='color:#ff4d4d;font-weight:900'>🔴 LIVE</span>" if is_live_now else "")
        + "</div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([2, 1.5, 2])

    with col1:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{hc['primary']}dd,{hc['primary']}77);"
            f"border-radius:12px;padding:20px 16px;text-align:center;min-height:110px;"
            f"display:flex;flex-direction:column;justify-content:center'>"
            f"<div style='font-size:22px;font-weight:900;color:{hc['text']}'>{flag_img(home)}"
            f"{team_link(home, color=hc['text'], underline=False, weight='900')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    with col2:
        if is_live_now:
            st.markdown(
                f"<div class='center-box' style='border:1px solid rgba(255,77,77,0.5)'>"
                f"<div class='score-label' style='color:#ff4d4d'>{live['home_score']} — {live['away_score']}</div>"
                f"<div style='color:#ff4d4d;font-size:10px;letter-spacing:1px;font-weight:900'>⏱ {live['status_detail']}</div>"
                f"<div class='venue-label'>📍 {row['city']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        elif espn_finished_not_yet_synced:
            st.markdown(
                f"<div class='center-box'>"
                f"<div class='score-label'>{live['home_score']} — {live['away_score']}</div>"
                f"<div style='color:rgba(255,255,255,0.4);font-size:10px;letter-spacing:1px'>FULL TIME</div>"
                f"<div class='venue-label'>📍 {row['city']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        elif done:
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
            f"<div style='font-size:22px;font-weight:900;color:{ac['text']}'>{flag_img(away)}"
            f"{team_link(away, color=ac['text'], underline=False, weight='900')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.plotly_chart(
        prob_bar(display_p_home, display_p_draw, display_p_away,
                 home, away, key=f"pb_{home}_{away}_{row['date']}"),
        use_container_width=True,
        key=f"pb_{home}_{away}_{row['date']}",
        config={"displayModeBar": False},
    )

    if live_probs:
        st.caption(
            f"🔴 Live win probability — recalculated from current score and time remaining "
            f"(expected additional goals: {live_probs['exp_additional_home_goals']:.2f} — "
            f"{live_probs['exp_additional_away_goals']:.2f})"
        )

    c1, c2, c3 = st.columns(3)
    c1.metric(f"🟢 {home}", f"{display_p_home:.1%}")
    c2.metric("⚪ Draw", f"{display_p_draw:.1%}")
    c3.metric(f"🔴 {away}", f"{display_p_away:.1%}")

    bc1, bc2 = st.columns(2)
    with bc1:
        if live_probs:
            live_predicted = max(
                {"Home Win": display_p_home, "Draw": display_p_draw, "Away Win": display_p_away},
                key=lambda k: {"Home Win": display_p_home, "Draw": display_p_draw, "Away Win": display_p_away}[k]
            )
            st.warning(f"🔴 Live Prediction (updated from current score): **{live_predicted}**")
        elif is_live_now:
            st.warning(f"🔴 Live now — model prediction shown pre-match: **{row['predicted_result']}**")
        else:
            st.info(f"📊 Model Prediction: **{row['predicted_result']}**")
    if done:
        with bc2:
            ok = row["predicted_result"] == row["actual_result"]
            if ok:
                st.success(f"✅ Actual: **{row['actual_result']}**")
            else:
                st.error(f"❌ Actual: **{row['actual_result']}**")
    elif espn_finished_not_yet_synced:
        with bc2:
            hs, as_ = live["home_score"], live["away_score"]
            actual = "Home Win" if hs > as_ else ("Away Win" if as_ > hs else "Draw")
            ok = row["predicted_result"] == actual
            label = f"{'✅' if ok else '❌'} Actual: **{actual}** (via live feed, syncing soon)"
            if ok:
                st.success(label)
            else:
                st.error(label)

    if is_live_now and live.get("event_id"):
        render_live_feed(live["event_id"], home, away)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"<h2 style='color:#FFD700!important;font-family:Arial Black;letter-spacing:1px'>{soccer_ball(22)} 2026 WC PREDICTOR</h2>",
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
    ], key="nav_page")
    st.markdown("---")
    st.markdown(
        f"<p style='color:white!important;font-size:13px;line-height:2'>"
        f"<span style='color:#FFD700'>📅 Updated:</span> {datetime.date.today().strftime('%b %d, %Y')}<br>"
        f"<span style='color:#FFD700'>📊 Matches:</span> 49,478 historical<br>"
        f"<span style='color:#FFD700'>🎲 Simulations:</span> 10,000 Monte Carlo<br>"
        f"<span style='color:#FFD700'>⚙️ Model:</span> Elo + Poisson"
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
    scorers_df = load_scorers()
except FileNotFoundError:
    st.error("⚠️ Run `python main.py` first to generate output files.")
    st.stop()


# ══ PAGE 1: TODAY'S MATCHES ═══════════════════════════════════════════════════
if page == "📅 Today's Matches":
    st.markdown(
        f"<h1 style='display:flex;align-items:center;gap:10px'>{soccer_ball(36)} "
        f"2026 FIFA World Cup Predictions</h1>",
        unsafe_allow_html=True
    )

    all_dates = sorted(predictions["date"].dt.date.unique())
    selected_date = st.date_input(
        "Select match date",
        value=datetime.date.today(),
        min_value=min(all_dates),
        max_value=max(all_dates),
    )
    day_matches = predictions[predictions["date"].dt.date == selected_date].copy()

    if len(day_matches) == 0:
        st.info("No matches on this date. Use the date picker to find match days.")
    else:
        # Today gets the fast (60s-cached) today-only feed so in-progress
        # matches update quickly. Any other date (including past matches our
        # own pipeline hasn't synced yet) falls back to the slower-cached
        # tournament-wide feed, which still has historical results.
        if selected_date == datetime.date.today():
            live_data = load_live_scores()
        else:
            tournament_data = load_tournament_scores()
            # Match by team pair, not by comparing kickoff_time's UTC calendar
            # date against selected_date — ESPN's kickoff_time is in UTC, but
            # an evening match in the Americas can cross into the next UTC
            # day (e.g. a 7pm Mexico kickoff is 1am UTC the following day),
            # which would silently fail a plain date-string comparison even
            # though it's unambiguously the correct match.
            day_team_pairs = set(zip(day_matches["home_team"], day_matches["away_team"]))
            live_data = {
                teams: info for teams, info in tournament_data.items()
                if teams in day_team_pairs
            }

        # Sort by ESPN kickoff time when we have it for this date (more reliable
        # than our own data, which only stores date not time-of-day); matches
        # without ESPN data keep their original relative order at the end.
        if live_data:
            def kickoff_sort_key(row):
                info = live_data.get((row["home_team"], row["away_team"]))
                return info["kickoff_time"] if info and info.get("kickoff_time") else "9999"
            day_matches = day_matches.assign(
                _sort_key=day_matches.apply(kickoff_sort_key, axis=1)
            ).sort_values("_sort_key").drop(columns="_sort_key")

        st.markdown(f"**{selected_date.strftime('%A, %B %d, %Y')} · {len(day_matches)} match(es)**")
        if selected_date == datetime.date.today():
            n_live = sum(1 for info in live_data.values() if info["status"] == "in") if live_data else 0
            if n_live > 0:
                st.caption(f"🔴 {n_live} match(es) live now")
            else:
                st.caption("⚪ No matches live right now")
        st.markdown("---")
        for _, row in day_matches.iterrows():
            render_match_card(row, live_data=live_data)


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
    st.caption("Each team's chance of winning the entire tournament")

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
    event = st.plotly_chart(
        fig, use_container_width=True,
        on_select="rerun", key="tournament_odds_chart",
        config={"displayModeBar": False},
    )
    if event and event.get("selection", {}).get("points"):
        clicked_team = event["selection"]["points"][0].get("y")
        if clicked_team:
            st.session_state.selected_team = clicked_team
            st.session_state.nav_page = "👥 Squads"
            st.rerun()
    st.caption("💡 Click any bar to view that team's squad and outlook")

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
                f"<span style='color:white'>{flag_img(top['team'])}{team_link(top['team'], color='white', weight='bold')}</span> "
                f"<span style='color:rgba(255,255,255,0.5)'>{top['win_pct']:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True
            )


# ══ PAGE 4: GROUP STANDINGS ════════════════════════════════════════════════════
elif page == "🗂️ Group Standings":
    st.title("🗂️ 2026 FIFA World Cup — Group Standings")

    # Use live-recalculated standings (ESPN scores overlaid on predictions)
    # whenever there's any tournament data available; otherwise fall back to
    # the static daily-batch CSV. Uses the tournament-wide feed (not just
    # today) since standings are cumulative across the whole group stage —
    # a match from yesterday that our own pipeline hasn't synced yet should
    # still count here.
    live_data_for_standings = load_tournament_scores()
    if live_data_for_standings:
        try:
            standings_df_live = compute_live_group_standings(predictions, live_data_for_standings)
            standings_df = standings_df_live
            st.caption("🔴 Live — includes in-progress and just-finished matches via live feed")
        except Exception:
            st.caption("Updated after each completed match · Top 2 qualify · Best 8 third-place teams also advance")
    else:
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
                            <b style='color:white'>{team_link(team, color='white')}</b>
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
        "Bracket seeded using the top 16 teams by predicted win probability, in standard "
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
        text_el = (
            f"<text x='{x + BOX_W/2}' y='{y:.1f}' text-anchor='middle' "
            f"font-size='{size}' font-family='Arial' font-weight='bold'>"
            f"<tspan fill='{color}'>\u25A0 </tspan>"
            f"<tspan fill='#ffffff' style='text-decoration:underline;text-decoration-style:dotted'>{team}</tspan>"
            f"</text>"
        )
        return f"<a href='?team={quote(team)}' target='_self' style='cursor:pointer'>{text_el}</a>"

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
        f"<a href='?team={quote(champion)}' target='_self' style='cursor:pointer'>"
        f"<text x='{col_x[3]+BOX_W/2}' y='{final_center + BOX_H/2 + 50}' text-anchor='middle' "
        f"font-size='11' fill='#00ff88' font-weight='900' font-family='Arial' "
        f"style='text-decoration:underline;text-decoration-style:dotted'>"
        f"\u2605 {champion}</text></a>"
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
                f"<div style='font-size:18px;font-weight:900;color:{tc['text']};margin:6px 0'>{team_link(row['team'], color=tc['text'])}</div>"
                f"<div style='font-size:22px;font-weight:bold;color:#FFD700'>{row['win_pct']:.1f}%</div>"
                f"<div style='font-size:11px;color:rgba(255,255,255,0.5)'>win probability</div>"
                f"</div>",
                unsafe_allow_html=True
            )


# ══ PAGE 6: SQUADS ════════════════════════════════════════════════════════════
# ══ PAGE 6: SQUADS ════════════════════════════════════════════════════════════
elif page == "👥 Squads":
    st.title("👥 2026 FIFA World Cup — Squads")
    st.caption("Squad, fixtures, and tournament outlook for every team")

    if squads_df is None:
        st.error("squads_clubs.csv not found. Run `python generate_squads_csv.py` and place "
                 "the output in `international_results/`.")
        st.stop()

    all_teams = sorted(squads_df["team"].unique())
    default_idx = 0
    if st.session_state.selected_team in all_teams:
        default_idx = all_teams.index(st.session_state.selected_team)

    sel_team = st.selectbox(
        "Select a team",
        all_teams,
        index=default_idx,
        format_func=lambda t: f"{t} (Group {squads_df[squads_df['team']==t]['group'].iloc[0]})",
        key="squads_page_select",
    )
    st.session_state.selected_team = sel_team

    team_df = squads_df[squads_df["team"] == sel_team]
    render_team_squad(team_df, sel_team)

    # ── 2026 World Cup Matches ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### {soccer_ball(22)} 2026 World Cup Matches", unsafe_allow_html=True)

    team_matches = predictions[
        (predictions["home_team"] == sel_team) | (predictions["away_team"] == sel_team)
    ].sort_values("date")

    if len(team_matches) == 0:
        st.info("No fixtures found for this team.")
    else:
        for _, m in team_matches.iterrows():
            is_home = m["home_team"] == sel_team
            opponent = m["away_team"] if is_home else m["home_team"]
            oc = gc(opponent)
            date_str = str(m["date"])[:10]

            if m["completed"]:
                hs, as_ = int(m["actual_home_score"]), int(m["actual_away_score"])
                my_score, opp_score = (hs, as_) if is_home else (as_, hs)
                score_str = f"{my_score} – {opp_score}"
                if my_score > opp_score:
                    badge, badge_color = "W", "#2ecc71"
                elif my_score < opp_score:
                    badge, badge_color = "L", "#e74c3c"
                else:
                    badge, badge_color = "D", "#f39c12"
                right_html = (
                    f"<span style='font-size:18px;font-weight:900;color:#00ff88'>{score_str}</span> "
                    f"<span style='background:{badge_color};color:#000;padding:2px 10px;"
                    f"border-radius:4px;font-weight:900;margin-left:8px;font-size:13px'>{badge}</span>"
                )
            else:
                pred = m["predicted_result"]
                right_html = f"<span style='color:#FFD700;font-size:13px'>📊 Predicted: {pred}</span>"

            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"background:rgba(255,255,255,0.03);border-radius:8px;padding:10px 16px;margin-bottom:6px'>"
                f"<div>"
                f"<span style='color:rgba(255,255,255,0.45);font-size:12px'>{date_str} · {m['city']}</span><br>"
                f"<span style='color:white;font-size:14px'>vs {flag_img(opponent, height=14)}"
                f"{team_link(opponent, color=oc['primary'], weight='bold')}</span>"
                f"</div>"
                f"<div>{right_html}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ── Goals in the Tournament ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚡ Goals in the Tournament")

    if scorers_df is None or len(scorers_df) == 0:
        st.info("No goals recorded yet — check back once matches are completed.")
    else:
        team_scorers = scorers_df[scorers_df["team"] == sel_team].sort_values("goals", ascending=False)
        if len(team_scorers) == 0:
            st.info(f"{sel_team} haven't scored yet in this tournament.")
        else:
            chips = ""
            for _, sc in team_scorers.iterrows():
                pen_note = f" <span style='color:rgba(255,255,255,0.5);font-size:11px'>({int(sc['penalties'])} pen)</span>" if sc["penalties"] > 0 else ""
                chips += (
                    f"<div style='display:inline-block;background:rgba(255,255,255,0.04);"
                    f"border:1px solid rgba(255,215,0,0.25);border-radius:10px;"
                    f"padding:10px 16px;margin:4px;text-align:center'>"
                    f"<div style='color:white;font-size:14px;font-weight:700'>{sc['scorer']}</div>"
                    f"<div style='color:#FFD700;font-size:22px;font-weight:900'>{int(sc['goals'])}</div>"
                    f"<div style='color:rgba(255,255,255,0.4);font-size:10px;letter-spacing:1px'>GOAL{'S' if sc['goals'] != 1 else ''}{pen_note}</div>"
                    f"</div>"
                )
            st.markdown(chips, unsafe_allow_html=True)

    # ── Tournament Outlook ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🏆 Tournament Outlook")

    mc_row = mc[mc["team"] == sel_team]
    standings_row = standings_df[standings_df["team"] == sel_team] if standings_df is not None else None

    out_cols = st.columns(3)
    if len(mc_row):
        r = mc_row.iloc[0]
        out_cols[0].metric("Win Probability", f"{r['win_pct']:.2f}%")
        out_cols[1].metric("Predicted Rank", f"#{int(r['rank'])} of 48")
    else:
        out_cols[0].metric("Win Probability", "—")
        out_cols[1].metric("Predicted Rank", "—")

    if standings_row is not None and len(standings_row):
        s = standings_row.iloc[0]
        q = s["qualified"]
        q_label = {"Q": "🟢 Qualified", "M": "🟡 In contention", "E": "🔴 Eliminated"}.get(q, "⚪ In progress")
        out_cols[2].metric("Group Stage Status", q_label)

        st.markdown(
            f"<div style='display:flex;gap:10px;margin-top:10px;flex-wrap:wrap'>"
            f"<div style='background:rgba(255,255,255,0.04);border-radius:8px;padding:10px 16px'>"
            f"<span style='color:rgba(255,255,255,0.5);font-size:11px'>PLAYED</span><br>"
            f"<span style='color:white;font-size:18px;font-weight:900'>{int(s['played'])}</span></div>"
            f"<div style='background:rgba(46,204,113,0.1);border-radius:8px;padding:10px 16px'>"
            f"<span style='color:rgba(255,255,255,0.5);font-size:11px'>WON</span><br>"
            f"<span style='color:#2ecc71;font-size:18px;font-weight:900'>{int(s['won'])}</span></div>"
            f"<div style='background:rgba(243,156,18,0.1);border-radius:8px;padding:10px 16px'>"
            f"<span style='color:rgba(255,255,255,0.5);font-size:11px'>DRAWN</span><br>"
            f"<span style='color:#f39c12;font-size:18px;font-weight:900'>{int(s['drawn'])}</span></div>"
            f"<div style='background:rgba(231,76,60,0.1);border-radius:8px;padding:10px 16px'>"
            f"<span style='color:rgba(255,255,255,0.5);font-size:11px'>LOST</span><br>"
            f"<span style='color:#e74c3c;font-size:18px;font-weight:900'>{int(s['lost'])}</span></div>"
            f"<div style='background:rgba(255,215,0,0.08);border-radius:8px;padding:10px 16px'>"
            f"<span style='color:rgba(255,255,255,0.5);font-size:11px'>POINTS</span><br>"
            f"<span style='color:#FFD700;font-size:18px;font-weight:900'>{int(s['pts'])}</span></div>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        out_cols[2].metric("Group Stage Status", "—")


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
                f"<div style='font-size:22px;font-weight:900;color:{hc['text']}'>{flag_img(team_a)}"
                f"{team_link(team_a, color=hc['text'], underline=False, weight='900')}</div>"
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
                f"<div style='font-size:22px;font-weight:900;color:{ac['text']}'>{flag_img(team_b)}"
                f"{team_link(team_b, color=ac['text'], underline=False, weight='900')}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.plotly_chart(
            prob_bar(p_home, p_draw, p_away, team_a, team_b, key="h2h"),
            use_container_width=True, key="h2h_bar",
            config={"displayModeBar": False},
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
        if winner == "Draw":
            st.success("📊 Model predicts: **Draw**")
        else:
            st.markdown(
                f"<div style='background:rgba(46,204,113,0.15);border:1px solid rgba(46,204,113,0.4);"
                f"border-radius:8px;padding:12px 16px;color:#2ecc71;font-size:15px'>"
                f"📊 Model predicts: <b>{team_link(winner, color='#2ecc71', weight='900')}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
