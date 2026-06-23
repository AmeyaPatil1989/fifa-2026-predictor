import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from urllib.parse import quote
import datetime
import streamlit.components.v1 as components
from background_image import BG_IMAGE_B64
from live_scores import fetch_live_scores, fetch_match_events, fetch_tournament_scores, fetch_match_scorers
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

@st.cache_data(ttl=300)
def load_match_scorers(event_id, home_team, away_team):
    """
    Cached for 5 minutes (longer than the 60s live-data cache, since scorer
    history only grows — re-fetching constantly adds no value once a goal
    has been confirmed, and this stays useful after full-time too, unlike
    the 'in-progress' specific live score/feed caches).
    """
    return fetch_match_scorers(event_id, home_team=home_team, away_team=away_team)

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


def render_scorer_list(event_id, home, away, hc, ac):
    scorers = load_match_scorers(event_id, home, away)
    if not scorers:
        return

    def scorer_line(s, align="left"):
        og_tag = " <span style='opacity:0.6'>(OG)</span>" if s["own_goal"] else ""
        pen_tag = " <span style='opacity:0.6'>(pen)</span>" if s["penalty"] and not s["own_goal"] else ""
        minute = s["minute"] or ""
        minute_html = f"<span style='color:rgba(255,255,255,0.45);font-size:11px'>{minute}</span>"
        if align == "right":
            # Minute first, name last, so it reads naturally right-to-left
            content = f"{minute_html} {s['scorer']}{og_tag}{pen_tag} ⚽"
        else:
            content = f"⚽ {s['scorer']}{og_tag}{pen_tag} {minute_html}"
        return f"<div style='font-size:13px;color:white;padding:3px 0;text-align:{align}'>{content}</div>"

    home_scorers = [s for s in scorers if s["team"] == home]
    away_scorers = [s for s in scorers if s["team"] == away]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div style='color:{hc['primary']};font-size:11px;font-weight:bold;"
            f"letter-spacing:1px;margin-bottom:2px;text-align:left'>{home.upper()}</div>",
            unsafe_allow_html=True
        )
        if home_scorers:
            st.markdown("".join(scorer_line(s, align="left") for s in home_scorers), unsafe_allow_html=True)
    with col2:
        st.markdown(
            f"<div style='color:{ac['primary']};font-size:11px;font-weight:bold;"
            f"letter-spacing:1px;margin-bottom:2px;text-align:right'>{away.upper()}</div>",
            unsafe_allow_html=True
        )
        if away_scorers:
            st.markdown("".join(scorer_line(s, align="right") for s in away_scorers), unsafe_allow_html=True)


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

    kickoff_utc = live.get("kickoff_time") if live else None
    kickoff_label = ""
    kickoff_js = None
    if kickoff_utc and not is_live_now and not done and not espn_finished_not_yet_synced:
        try:
            from zoneinfo import ZoneInfo
            dt = datetime.datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
            dt_et = dt.astimezone(ZoneInfo("America/New_York"))
            et_str = dt_et.strftime("%-I:%M %p ET")
            uid = f"kt{abs(hash(home+away)) % 99999}"
            # Show ET immediately (server-side, no blank span, no layout gap)
            kickoff_label = f"&nbsp;·&nbsp;<span id='{uid}'>{et_str}</span>"
            # Then replace with local time via JS if available
            kickoff_js = (uid, kickoff_utc)
        except Exception:
            pass

    st.markdown(
        f"<div class='match-label'>{soccer_ball(14, 'vertical-align:-2px;margin-right:4px')} FIFA WORLD CUP 2026 &nbsp;·&nbsp; {str(row['date'])[:10]}"
        + kickoff_label
        + ("&nbsp;·&nbsp;<span style='color:#ff4d4d;font-weight:900'>🔴 LIVE</span>" if is_live_now else "")
        + "</div>",
        unsafe_allow_html=True
    )

    if kickoff_js:
        uid, kut = kickoff_js
        components.html(
            f"""<script>
            (function(){{
                var d=new Date('{kut}');
                var s;
                try{{
                    s=d.toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}});
                    if(!s||s.indexOf('NaN')>=0)throw new Error();
                    // Find the ET span in the parent document and replace it
                    var el=window.parent.document.getElementById('{uid}');
                    if(el)el.textContent=s;
                }}catch(e){{}}
            }})();
            </script>""",
            height=0,
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

    # Goal scorers — shown whenever ESPN has data for this match (live,
    # finished-but-not-yet-synced, or already-synced but still within ESPN's
    # tournament feed window), not just while strictly in-progress, so this
    # persists alongside the final score after full-time too.
    if live and live.get("event_id"):
        render_scorer_list(live["event_id"], home, away, hc, ac)

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

    # Top countdown — shown when no match is currently live.
    # Uses the tournament-wide feed so it works even between match days.
    _top_live = load_live_scores()
    _any_live = any(info["status"] == "in" for info in _top_live.values()) if _top_live else False
    if not _any_live:
        _all_tourney = load_tournament_scores()
        _upcoming = sorted([
            info["kickoff_time"] for info in _all_tourney.values()
            if info["status"] == "pre" and info.get("kickoff_time")
        ]) if _all_tourney else []
        if _upcoming:
            _next = _upcoming[0]
            components.html(
                f"""<div style='font-family:sans-serif;font-size:15px;
                    color:rgba(255,255,255,0.85);background:transparent;
                    padding:4px 0 8px 0'>
                    ⏱️ Next match in:&nbsp;
                    <span id='top_countdown'
                        style='color:#FFD700;font-weight:bold;font-size:17px'></span>
                </div>
                <script>
                (function(){{
                    var target=new Date('{_next}');
                    function tick(){{
                        var now=new Date();
                        var diff=target-now;
                        var el=document.getElementById('top_countdown');
                        if(!el)return;
                        if(diff<=0){{el.textContent='Starting now!';return;}}
                        var h=Math.floor(diff/3600000);
                        var m=Math.floor((diff%3600000)/60000);
                        var s=Math.floor((diff%60000)/1000);
                        el.textContent=(h>0?h+'h ':'')+m+'m '+s+'s';
                        setTimeout(tick,1000);
                    }}
                    tick();
                }})();
                </script>""",
                height=40,
            )

    all_dates = sorted(predictions["date"].dt.date.unique())

    # Use tournament-wide ESPN feed to find the correct default date.
    # This avoids relying on datetime.date.today() (server UTC, wrong timezone)
    # and avoids stale load_live_scores() cache issues.
    # Logic: find the latest date that has any finished or live matches —
    # that's the "current" match day regardless of server timezone.
    try:
        _tourney = load_tournament_scores()
        _played_dates = set()
        _upcoming_dates = set()
        for (home, away), info in (_tourney or {}).items():
            kt = info.get("kickoff_time", "")
            if not kt:
                continue
            try:
                dt = datetime.datetime.fromisoformat(kt.replace("Z", "+00:00"))
                # Use ET date (UTC-4 in summer) to match US match day convention
                et_date = (dt - datetime.timedelta(hours=4)).date()
                match_date = et_date if et_date in all_dates else dt.date()
                if info["status"] in ("in", "post"):
                    _played_dates.add(match_date)
                elif info["status"] == "pre":
                    _upcoming_dates.add(match_date)
            except Exception:
                continue

        if _played_dates:
            # Show the most recent day that has played/live matches
            default_date = max(d for d in _played_dates if d in all_dates)
        elif _upcoming_dates:
            # Nothing played yet today — show next upcoming match day
            default_date = min(d for d in _upcoming_dates if d in all_dates)
        else:
            # ESPN feed empty — fall back to first future date
            today = datetime.date.today()
            future = [d for d in all_dates if d >= today]
            default_date = future[0] if future else all_dates[-1]
    except Exception:
        today = datetime.date.today()
        future = [d for d in all_dates if d >= today]
        default_date = future[0] if future else all_dates[-1]

    selected_date = st.date_input(
        "Select match date",
        value=default_date,
        min_value=min(all_dates),
        max_value=max(all_dates),
        key=f"date_picker_{default_date}",
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
            # Always overlay the fresh 60s-cached live feed on top, regardless
            # of date. This catches late-evening matches that cross midnight UTC
            # (e.g. a 11pm ET kickoff = 3am UTC next day) — the tournament feed
            # has a 10min cache and may still show "pre" for a match that just
            # kicked off, while load_live_scores() always has the current state.
            fresh_live = load_live_scores()
            for teams, info in fresh_live.items():
                if teams in day_team_pairs:
                    live_data[teams] = info  # fresh data wins over stale cache

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

    def pred_table(rows, cols, col_labels, col_align=None):
        """Renders a styled dark HTML table matching the dashboard theme."""
        if col_align is None:
            col_align = ["left"] * len(cols)
        header = "".join(
            f"<th style='text-align:{col_align[i]};color:#FFD700;font-size:12px;"
            f"font-weight:700;letter-spacing:1px;padding:8px 12px;"
            f"border-bottom:1px solid rgba(255,255,255,0.15);white-space:nowrap'>"
            f"{col_labels[i]}</th>"
            for i in range(len(cols))
        )
        body = ""
        for idx, row in rows.iterrows():
            cells = ""
            for i, col in enumerate(cols):
                val = row[col]
                align = col_align[i]
                # Color-code prediction/result columns
                color = "white"
                if col == "predicted_result" or col == "Predicted":
                    color = "#FFD700"
                elif col == "actual_result" or col == "Actual":
                    color = "#aaffaa" if row.get("✓", "") == "✅" else "#ffaaaa"
                elif col == "✓":
                    pass
                cells += (
                    f"<td style='text-align:{align};color:{color};font-size:13px;"
                    f"padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.06)'>"
                    f"{val}</td>"
                )
            body += f"<tr style='background:rgba(255,255,255,0.02)'>{cells}</tr>"
        st.markdown(
            f"<div style='overflow-x:auto'>"
            f"<table style='width:100%;border-collapse:collapse;"
            f"background:rgba(255,255,255,0.03);border-radius:8px;overflow:hidden'>"
            f"<thead><tr>{header}</tr></thead>"
            f"<tbody>{body}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True
        )

    with tab1:
        up = predictions[~predictions["completed"]].copy()
        up["date"] = up["date"].dt.strftime("%Y-%m-%d")
        up["Home Win %"] = up["p_home_win"].apply(lambda x: f"{x:.1%}")
        up["Draw %"] = up["p_draw"].apply(lambda x: f"{x:.1%}")
        up["Away Win %"] = up["p_away_win"].apply(lambda x: f"{x:.1%}")
        up["xG Home"] = up["exp_home_goals"].apply(lambda x: f"{x:.2f}")
        up["xG Away"] = up["exp_away_goals"].apply(lambda x: f"{x:.2f}")
        up["home_team"] = up["home_team"].apply(lambda t: team_link(t))
        up["away_team"] = up["away_team"].apply(lambda t: team_link(t))
        pred_table(
            up,
            cols=["date","home_team","away_team","city","Home Win %","Draw %","Away Win %","xG Home","xG Away","predicted_result"],
            col_labels=["Date","Home","Away","City","Home Win %","Draw %","Away Win %","xG Home","xG Away","Prediction"],
            col_align=["left","left","left","left","center","center","center","center","center","center"],
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
                lambda r: f"{int(r['actual_home_score'])} — {int(r['actual_away_score'])}", axis=1)
            done["✓"] = (done["predicted_result"] == done["actual_result"]).map(
                {True: "✅", False: "❌"})
            done["date"] = done["date"].dt.strftime("%Y-%m-%d")
            done["home_team"] = done["home_team"].apply(lambda t: team_link(t))
            done["away_team"] = done["away_team"].apply(lambda t: team_link(t))
            pred_table(
                done,
                cols=["date","home_team","away_team","Score","predicted_result","actual_result","✓"],
                col_labels=["Date","Home","Away","Score","Predicted","Actual",""],
                col_align=["left","left","left","center","center","center","center"],
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
    st.title("🔲 2026 FIFA World Cup — Knockout Bracket")
    
    # ── Caption: explain what's real vs predicted ──────────────────────────────
    all_groups_done = False
    if standings_df is not None:
        groups_with_3_played = (
            standings_df[standings_df["played"] == 3]["group"].nunique()
            if "played" in standings_df.columns else 0
        )
        all_groups_done = groups_with_3_played == 12
    
    if all_groups_done:
        st.caption("✅ All groups complete — bracket slots are confirmed. R16 onward shows model predictions.")
    else:
        st.caption(
            "🔄 Group stage in progress — confirmed slots shown where decided. "
            "3rd-place slots resolve June 27 when all groups finish."
        )
    
    # ── R32 slot definitions (hardcoded from FIFA regulations) ─────────────────
    # Each match: (match_id, team1_slot, team2_slot)
    # Slot format: ("winner"/"runner_up"/"third"/"host_winner"/"host_runnerup", group_or_pool_string)
    # "third" pool is a string of groups, e.g. "A/B/C/D/F"
    R32 = [
        ("M73", ("runner_up", "A"), ("runner_up", "B")),
        ("M74", ("winner",   "E"), ("third",     "A/B/C/D/F")),
        ("M75", ("winner",   "F"), ("runner_up", "C")),
        ("M76", ("winner",   "C"), ("runner_up", "F")),
        ("M77", ("winner",   "I"), ("third",     "C/D/F/G/H")),
        ("M78", ("runner_up","E"), ("runner_up", "I")),
        ("M79", ("winner",   "A"), ("third",     "C/E/F/H/I")),   # Mexico fixed as winner A
        ("M80", ("winner",   "L"), ("third",     "E/H/I/J/K")),
        ("M81", ("winner",   "D"), ("third",     "B/E/F/I/J")),   # USA fixed as winner D
        ("M82", ("winner",   "G"), ("third",     "A/E/H/I/J")),
        ("M83", ("runner_up","K"), ("runner_up", "L")),
        ("M84", ("winner",   "H"), ("runner_up", "J")),
        ("M85", ("winner",   "B"), ("third",     "E/F/G/I/J")),   # Canada fixed as winner B
        ("M86", ("winner",   "J"), ("runner_up", "H")),
        ("M87", ("winner",   "K"), ("third",     "D/E/I/J/L")),
        ("M88", ("runner_up","D"), ("runner_up", "G")),
    ]
    
    # R16 pairings: which two R32 winners meet
    R16 = [
        ("M89",  "M74", "M77"),
        ("M90",  "M73", "M75"),
        ("M91",  "M76", "M78"),
        ("M92",  "M79", "M80"),
        ("M93",  "M83", "M84"),
        ("M94",  "M81", "M82"),
        ("M95",  "M86", "M88"),
        ("M96",  "M85", "M87"),
    ]
    
    # QF pairings
    QF = [
        ("M97",  "M89", "M90"),
        ("M98",  "M91", "M92"),
        ("M99",  "M93", "M94"),   # NOTE: verify bracket half — FIFA doc shows M99/M100
        ("M100", "M95", "M96"),
    ]
    
    # SF pairings
    SF = [
        ("M101", "M97", "M98"),
        ("M102", "M99", "M100"),
    ]
    
    FINAL   = ("M104", "M101", "M102")
    BRONZE  = ("M103", "M101", "M102")   # losers
    
    # ── Build slot→team lookup from group_standings.csv ────────────────────────
    # Returns team name or None if not yet decided
    def get_team(standings, slot_type, slot_val):
        """
        slot_type: "winner" | "runner_up" | "third"
        slot_val:  group letter (A-L) for winner/runner_up,
                   pool string (e.g. "A/B/C/D/F") for third
        """
        if standings is None:
            return None
        if slot_type == "winner":
            row = standings[
                (standings["group"] == slot_val) & (standings["position"] == 1)
            ]
            return row.iloc[0]["team"] if len(row) > 0 else None
        elif slot_type == "runner_up":
            row = standings[
                (standings["group"] == slot_val) & (standings["position"] == 2)
            ]
            return row.iloc[0]["team"] if len(row) > 0 else None
        elif slot_type == "third":
            # Can't resolve until all groups in pool are done AND
            # we know which 8 thirds qualified (Annex C lookup).
            # Return None — displayed as "3rd <pool>" placeholder.
            return None
        return None
    
    def slot_label(slot_type, slot_val, team):
        """Human-readable label for a bracket slot."""
        if team:
            return team
        if slot_type == "winner":
            return f"Winner {slot_val}"
        elif slot_type == "runner_up":
            return f"Runner-up {slot_val}"
        elif slot_type == "third":
            return f"3rd ({slot_val})"
        return "TBD"
    
    def is_decided(team):
        return team is not None
    
    # Use live standings (same logic as Group Standings page)
    live_data_for_bracket = load_tournament_scores()
    if live_data_for_bracket:
        try:
            bracket_standings = compute_live_group_standings(predictions, live_data_for_bracket)
        except Exception:
            bracket_standings = standings_df
    else:
        bracket_standings = standings_df
    
    # ── Resolve all R32 team slots ─────────────────────────────────────────────
    r32_teams = {}   # match_id -> (team1_label, team2_label, team1_decided, team2_decided)
    for mid, s1, s2 in R32:
        t1 = get_team(bracket_standings, s1[0], s1[1])
        t2 = get_team(bracket_standings, s2[0], s2[1])
        l1 = slot_label(s1[0], s1[1], t1)
        l2 = slot_label(s2[0], s2[1], t2)
        r32_teams[mid] = (l1, l2, is_decided(t1), is_decided(t2))
    
    # ── Model prediction for a matchup ────────────────────────────────────────
    mc_dict = dict(zip(mc["team"], mc["win_probability"])) if mc is not None else {}
    
    def predict_winner(label_a, label_b, decided_a, decided_b):
        """
        Returns the predicted winner label.
        Uses MC win probability if both teams are known.
        Falls back to first team if either is unknown (can't predict TBD).
        """
        if not decided_a or not decided_b:
            return None   # Can't predict yet
        pa = mc_dict.get(label_a, 0)
        pb = mc_dict.get(label_b, 0)
        return label_a if pa >= pb else label_b
    
    # ── Resolve R16 → QF → SF → Final via model ───────────────────────────────
    # winner_of[match_id] = (winner_label, is_decided)
    winner_of = {}
    
    for mid, s1, s2 in R32:
        l1, l2, d1, d2 = r32_teams[mid]
        w = predict_winner(l1, l2, d1, d2)
        winner_of[mid] = (w, w is not None)
    
    def resolve_match(match_id, src_a, src_b):
        wa, da = winner_of.get(src_a, (None, False))
        wb, db = winner_of.get(src_b, (None, False))
        la = wa or f"W {src_a}"
        lb = wb or f"W {src_b}"
        w = predict_winner(la, lb, da, db)
        winner_of[match_id] = (w, w is not None)
        return la, lb, da, db
    
    r16_slots = {}
    for mid, src_a, src_b in R16:
        la, lb, da, db = resolve_match(mid, src_a, src_b)
        r16_slots[mid] = (la, lb, da, db)
    
    qf_slots = {}
    for mid, src_a, src_b in QF:
        la, lb, da, db = resolve_match(mid, src_a, src_b)
        qf_slots[mid] = (la, lb, da, db)
    
    sf_slots = {}
    for mid, src_a, src_b in SF:
        la, lb, da, db = resolve_match(mid, src_a, src_b)
        sf_slots[mid] = (la, lb, da, db)
    
    f_la, f_lb, f_da, f_db = resolve_match(FINAL[0], FINAL[1], FINAL[2])
    champion, champion_decided = winner_of.get(FINAL[0], (None, False))
    
    # ── Render: list view (mobile-friendly) ───────────────────────────────────
    # We use a list-style layout rather than SVG — more readable on mobile,
    # easier to maintain, and less prone to overflow issues.
    # Layout: tabs for each round.
    
    tab_r32, tab_r16, tab_qf, tab_sf, tab_final = st.tabs([
        "⚔️ Round of 32", "🔟 Round of 16", "🏅 Quarterfinals",
        "🎖️ Semifinals", "🏆 Final"
    ])
    
    def match_card_bracket(match_id, label_a, label_b, decided_a, decided_b,
                            winner_label=None, date_str="", venue=""):
        """Renders a single bracket match card."""
        wa = winner_label == label_a if winner_label else False
        wb = winner_label == label_b if winner_label else False
    
        def team_row(label, decided, is_winner):
            flag_html = flag_img(label) if decided and label in FLAG_CODES else ""
            tc = gc(label) if decided and label in TEAM_COLORS else DEFAULT_COLOR
            border = f"2px solid {tc['primary']}" if decided else "1px solid rgba(255,255,255,0.1)"
            bg = f"background:rgba({int(tc['primary'][1:3],16)},{int(tc['primary'][3:5],16)},{int(tc['primary'][5:7],16)},0.15);" if is_winner else ""
            star = " ⭐" if is_winner and winner_label else ""
            name_color = "#FFD700" if is_winner else ("white" if decided else "rgba(255,255,255,0.4)")
            link = team_link(label, color=name_color, weight="bold") if decided and label in FLAG_CODES else f"<span style='color:{name_color}'>{label}</span>"
            return (
                f"<div style='{bg}border-left:{border};padding:8px 12px;"
                f"display:flex;align-items:center;gap:8px;border-radius:4px;margin:3px 0'>"
                f"{flag_html}<span style='font-size:14px'>{link}{star}</span>"
                f"</div>"
            )
    
        meta = ""
        if date_str or venue:
            meta = f"<div style='font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:4px'>{match_id}"
            if date_str: meta += f" · {date_str}"
            if venue: meta += f" · {venue}"
            meta += "</div>"
    
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.03);border-radius:8px;"
            f"padding:10px 14px;margin-bottom:8px;border:1px solid rgba(255,255,255,0.08)'>"
            f"{meta}"
            f"{team_row(label_a, decided_a, wa)}"
            f"{team_row(label_b, decided_b, wb)}"
            f"</div>",
            unsafe_allow_html=True
        )
    
    # R32 dates and venues (hardcoded from schedule)
    R32_META = {
        "M73": ("Jun 28", "SoFi Stadium, LA"),
        "M74": ("Jun 29", "Gillette Stadium, Boston"),
        "M75": ("Jun 29", "Estadio BBVA, Monterrey"),
        "M76": ("Jun 29", "NRG Stadium, Houston"),
        "M77": ("Jun 30", "MetLife Stadium, NJ"),
        "M78": ("Jun 30", "AT&T Stadium, Dallas"),
        "M79": ("Jun 30", "Estadio Azteca, Mexico City"),
        "M80": ("Jul 1",  "Mercedes-Benz Stadium, Atlanta"),
        "M81": ("Jul 1",  "Levi's Stadium, San Francisco"),
        "M82": ("Jul 1",  "Lumen Field, Seattle"),
        "M83": ("Jul 2",  "BMO Field, Toronto"),
        "M84": ("Jul 2",  "SoFi Stadium, LA"),
        "M85": ("Jul 2",  "BC Place, Vancouver"),
        "M86": ("Jul 3",  "Hard Rock Stadium, Miami"),
        "M87": ("Jul 3",  "Arrowhead Stadium, Kansas City"),
        "M88": ("Jul 3",  "AT&T Stadium, Dallas"),
    }
    
    with tab_r32:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:12px'>"
            "16 matches · Jun 28 – Jul 3 · Group winners and runners-up + 8 best 3rd-place teams</p>",
            unsafe_allow_html=True
        )
        # Display in chronological order (matches sorted by date)
        r32_order = ["M73","M76","M74","M75","M78","M77","M79","M80","M82","M81","M84","M83","M85","M88","M86","M87"]
        cols_r32 = st.columns(2)
        for i, mid in enumerate(r32_order):
            l1, l2, d1, d2 = r32_teams[mid]
            w, wd = winner_of.get(mid, (None, False))
            date_str, venue = R32_META.get(mid, ("", ""))
            with cols_r32[i % 2]:
                match_card_bracket(mid, l1, l2, d1, d2,
                                   winner_label=w if wd else None,
                                   date_str=date_str, venue=venue)
    
    with tab_r16:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:12px'>"
            "8 matches · Jul 4 – Jul 7 · Winners of R32</p>",
            unsafe_allow_html=True
        )
        R16_META = {
            "M89": ("Jul 4", "Lincoln Financial Field, Philadelphia"),
            "M90": ("Jul 4", "NRG Stadium, Houston"),
            "M91": ("Jul 5", "MetLife Stadium, NJ"),
            "M92": ("Jul 5", "Estadio Azteca, Mexico City"),
            "M93": ("Jul 6", "AT&T Stadium, Dallas"),
            "M94": ("Jul 6", "Lumen Field, Seattle"),
            "M95": ("Jul 7", "Hard Rock Stadium, Miami"),
            "M96": ("Jul 7", "BC Place, Vancouver"),
        }
        cols_r16 = st.columns(2)
        for i, (mid, src_a, src_b) in enumerate(R16):
            la, lb, da, db = r16_slots[mid]
            w, wd = winner_of.get(mid, (None, False))
            date_str, venue = R16_META.get(mid, ("", ""))
            with cols_r16[i % 2]:
                match_card_bracket(mid, la, lb, da, db,
                                   winner_label=w if wd else None,
                                   date_str=date_str, venue=venue)
    
    with tab_qf:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:12px'>"
            "4 matches · Jul 9 – Jul 11 · Winners of R16</p>",
            unsafe_allow_html=True
        )
        QF_META = {
            "M97":  ("Jul 9",  "Lincoln Financial Field, Philadelphia"),
            "M98":  ("Jul 9",  "Estadio Azteca, Mexico City"),
            "M99":  ("Jul 11", "AT&T Stadium, Dallas"),
            "M100": ("Jul 11", "Lumen Field, Seattle"),
        }
        cols_qf = st.columns(2)
        for i, (mid, src_a, src_b) in enumerate(QF):
            la, lb, da, db = qf_slots[mid]
            w, wd = winner_of.get(mid, (None, False))
            date_str, venue = QF_META.get(mid, ("", ""))
            with cols_qf[i % 2]:
                match_card_bracket(mid, la, lb, da, db,
                                   winner_label=w if wd else None,
                                   date_str=date_str, venue=venue)
    
    with tab_sf:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:12px'>"
            "2 matches · Jul 14 – Jul 15</p>",
            unsafe_allow_html=True
        )
        SF_META = {
            "M101": ("Jul 14", "AT&T Stadium, Dallas"),
            "M102": ("Jul 15", "MetLife Stadium, NJ"),
        }
        cols_sf = st.columns(2)
        for i, (mid, src_a, src_b) in enumerate(SF):
            la, lb, da, db = sf_slots[mid]
            w, wd = winner_of.get(mid, (None, False))
            date_str, venue = SF_META.get(mid, ("", ""))
            with cols_sf[i % 2]:
                match_card_bracket(mid, la, lb, da, db,
                                   winner_label=w if wd else None,
                                   date_str=date_str, venue=venue)
    
    with tab_final:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.5);font-size:12px'>"
            "🏟️ MetLife Stadium, East Rutherford, NJ · Jul 19, 2026</p>",
            unsafe_allow_html=True
        )
    
        # Bronze Final
        st.markdown("#### 🥉 Third-Place Match — Jul 18 · AT&T Stadium, Dallas")
        sf1_loser_label = sf_slots["M101"][1] if winner_of.get("M101", (None,))[0] == sf_slots["M101"][0] else sf_slots["M101"][0]
        sf2_loser_label = sf_slots["M102"][1] if winner_of.get("M102", (None,))[0] == sf_slots["M102"][0] else sf_slots["M102"][0]
        sf1_loser_decided = sf_slots["M101"][2] or sf_slots["M101"][3]
        sf2_loser_decided = sf_slots["M102"][2] or sf_slots["M102"][3]
        match_card_bracket("M103 (Bronze)", sf1_loser_label, sf2_loser_label,
                           sf1_loser_decided, sf2_loser_decided)
    
        # Final
        st.markdown("#### 🏆 FINAL — Jul 19 · MetLife Stadium, NJ")
        match_card_bracket("M104 (Final)", f_la, f_lb, f_da, f_db,
                           winner_label=champion if champion_decided else None)
    
        # Champion podium
        if champion_decided and champion:
            tc = gc(champion)
            st.markdown(
                f"<div style='background:linear-gradient(135deg,{tc['primary']}cc,{tc['primary']}44);"
                f"border-radius:14px;padding:28px;text-align:center;margin-top:16px;"
                f"border:2px solid #FFD700'>"
                f"<div style='font-size:40px'>🏆</div>"
                f"<div style='margin:8px 0'>{flag_img(champion, height=28)}</div>"
                f"<div style='font-size:26px;font-weight:900;color:#FFD700'>"
                f"{team_link(champion, color='#FFD700', weight='900')}</div>"
                f"<div style='font-size:13px;color:rgba(255,255,255,0.5);margin-top:6px'>"
                f"Model predicted champion</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.info("🏆 Predicted champion will appear once group standings are decided.")
    
    # ── Model accuracy note ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<p style='color:rgba(255,255,255,0.35);font-size:11px'>"
        "R32 slots: real qualified teams from live standings. "
        "3rd-place slots: Annex C — resolves after June 27 when all 12 groups finish. "
        "R16 → Final: model predictions using Elo + Monte Carlo win probability.</p>",
        unsafe_allow_html=True
    )

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
