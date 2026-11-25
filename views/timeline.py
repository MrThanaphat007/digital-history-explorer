"""Cinematic timeline: scroll-through "documentary" view with an auto-play mode,
linked to the map and to the GIS polity lookup."""
import json
import folium
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium
from db import query
from geo import polity_at
from utils import base_map, fmt_year, year_ticks, style_fig, ERA_RANGES, YEAR_MIN, YEAR_MAX

# One colour per event category (used by the cinematic view and the overview chart)
CAT_COLOURS = {"War": "#c0392b", "Politics": "#4a6fa5", "Law": "#3f8f6b", "Religion": "#8e5ea2",
               "Exploration": "#d98324", "Disease": "#7f8c8d", "Trade": "#b08d57"}


def _show_on_map(row):
    """Callback: remember the event, move the global year, jump to the map page."""
    st.session_state["focus_event"] = {"lat": row["lat"], "lon": row["lon"], "title": row["title"]}
    st.session_state["year"] = int(row["year"])
    st.session_state["nav"] = "Interactive Map"


def cinematic_html(events: list[dict]) -> str:
    """Self-contained HTML/CSS/JS block. Data is passed as JSON and inserted with
    textContent (never innerHTML), so event text cannot inject markup."""
    data = json.dumps(events).replace("</", "<\\/")
    colours = json.dumps(CAT_COLOURS)
    return """
<style>
  *{box-sizing:border-box} body{margin:0;font-family:'Inter',system-ui,sans-serif}
  #wrap{position:relative;height:640px;background:radial-gradient(ellipse at top,#1b2230 0%,#0b0e14 70%);
        color:#eee;border-radius:10px;overflow:hidden;border:1px solid #2b323b}
  #hud{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;gap:14px;
       padding:10px 16px;background:linear-gradient(#0b0e14ee,#0b0e1400)}
  #year{font:700 2.4rem 'Libre Baskerville',Georgia,serif;color:#d4b06a;min-width:190px;
        text-shadow:0 0 18px #d4b06a66}
  button,select{background:#1d2229;color:#eee;border:1px solid #3a4350;border-radius:6px;padding:7px 14px;
        font-size:.9rem;cursor:pointer} button:hover{border-color:#d4b06a}
  #bar{position:absolute;top:0;left:0;height:3px;background:#d4b06a;width:0;z-index:6;transition:width .5s}
  #stage{position:absolute;inset:0;overflow-y:auto;padding:90px 0 260px;scroll-behavior:smooth}
  #line{position:absolute;left:50%;top:0;bottom:0;width:2px;background:linear-gradient(#0000,#d4b06a88,#0000)}
  .item{position:relative;width:50%;padding:14px 38px;opacity:0;transform:translateY(34px);
        transition:opacity .7s,transform .7s}
  .item.show{opacity:.55;transform:none} .item.active{opacity:1}
  .item.left{left:0;text-align:right} .item.right{left:50%}
  .dot{position:absolute;top:30px;width:14px;height:14px;border-radius:50%;background:var(--c);
       box-shadow:0 0 0 4px #0b0e14,0 0 14px var(--c)}
  .left .dot{right:-7px} .right .dot{left:-7px}
  .card{background:#141922;border:1px solid #2b323b;border-top:3px solid var(--c);border-radius:8px;
        padding:14px 18px;display:inline-block;max-width:100%;text-align:left;transition:box-shadow .4s}
  .active .card{box-shadow:0 0 28px -4px var(--c)}
  .yr{font:700 1.7rem 'Libre Baskerville',Georgia,serif;color:var(--c)}
  .chip{font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#aab;margin-left:8px}
  .ttl{font-weight:600;font-size:1.05rem;margin:4px 0}
  .dsc{font-size:.9rem;color:#c9ced6;line-height:1.5} .src{font-size:.75rem;color:#8a93a0;margin-top:8px}
  @media (max-width:640px){
    #line{left:18px} .item{width:100%;left:0!important;text-align:left!important;padding:12px 12px 12px 44px}
    .dot{left:11px!important;right:auto!important} #year{font-size:1.6rem;min-width:130px}}
</style>
<div id="wrap">
  <div id="bar"></div>
  <div id="hud">
    <div id="year">&nbsp;</div>
    <button id="play">&#9654; Play</button>
    <select id="speed"><option value="6000">Slow</option><option value="4000" selected>Normal</option>
      <option value="2200">Fast</option></select>
  </div>
  <div id="stage"><div id="line"></div></div>
</div>
<script>
const EVENTS = __DATA__, COLOURS = __COLOURS__;
const stage = document.getElementById('stage'), yearEl = document.getElementById('year');
const barEl = document.getElementById('bar'), playBtn = document.getElementById('play');
const fmt = y => (y < 0 ? Math.abs(y) + ' BCE' : y + ' CE');

// Build one card per event (alternating left/right)
const items = EVENTS.map((e, i) => {
  const d = document.createElement('div');
  d.className = 'item ' + (i % 2 ? 'right' : 'left');
  d.style.setProperty('--c', COLOURS[e.category] || '#aaa');
  const mk = (cls, txt, parent) => { const n = document.createElement('div'); n.className = cls;
                                      n.textContent = txt; parent.appendChild(n); return n; };
  const dot = document.createElement('div'); dot.className = 'dot'; d.appendChild(dot);
  const card = document.createElement('div'); card.className = 'card'; d.appendChild(card);
  const head = mk('yr', fmt(e.year), card);
  const chip = document.createElement('span'); chip.className = 'chip'; chip.textContent = e.category;
  head.appendChild(chip);
  mk('ttl', e.title, card); mk('dsc', e.description, card); mk('src', 'Source: ' + e.source, card);
  stage.appendChild(d); return d;
});

// Fade cards in as they scroll into view
const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) x.target.classList.add('show'); }),
                                    {root: stage, threshold: 0.2});
items.forEach(i => io.observe(i));

// Year counter tweens to the target year
let shown = EVENTS.length ? EVENTS[0].year : 0, raf = null;
function setYear(target) {
  cancelAnimationFrame(raf);
  const from = shown, t0 = performance.now();
  (function tick(t) {
    const p = Math.min(1, (t - t0) / 600);
    shown = Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3)));
    yearEl.textContent = fmt(shown);
    if (p < 1) raf = requestAnimationFrame(tick);
  })(t0);
}

// Highlight the card nearest the vertical centre while scrolling
let current = -1;
function focusNearest() {
  const mid = stage.scrollTop + stage.clientHeight / 2; let best = 0, bd = 1e9;
  items.forEach((it, i) => { const d = Math.abs(it.offsetTop + it.offsetHeight / 2 - mid);
                              if (d < bd) { bd = d; best = i; } });
  if (best !== current) {
    current = best; items.forEach((it, i) => it.classList.toggle('active', i === best));
    items[best].classList.add('show'); setYear(EVENTS[best].year);
    barEl.style.width = (EVENTS.length > 1 ? best / (EVENTS.length - 1) * 100 : 100) + '%';
  }
}
stage.addEventListener('scroll', () => requestAnimationFrame(focusNearest));
function goTo(i) {
  const it = items[i];
  stage.scrollTo({top: it.offsetTop - stage.clientHeight / 2 + it.offsetHeight / 2, behavior: 'smooth'});
}

// Play mode: step through events from the earliest to the latest
let playing = false, timer = null, idx = 0;
function step() {
  if (!playing) return;
  if (idx >= items.length) { stop(); return; }
  goTo(idx); idx++;
  timer = setTimeout(step, +document.getElementById('speed').value);
}
function stop() { playing = false; clearTimeout(timer); playBtn.innerHTML = '&#9654; Play'; }
playBtn.onclick = () => {
  if (playing) { stop(); return; }
  playing = true; playBtn.innerHTML = '&#10073;&#10073; Pause';
  if (idx >= items.length || current < 0) idx = 0; else idx = Math.max(current + 1, 0);
  step();
};
if (EVENTS.length) { yearEl.textContent = fmt(EVENTS[0].year); focusNearest(); }
</script>
""".replace("__DATA__", data).replace("__COLOURS__", colours)


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Historical Timeline</h1>"
                "<p class='small-note'>Scroll through history, or press Play to watch events unfold in order.</p></div>",
                unsafe_allow_html=True)
    preset = st.radio("Era", list(ERA_RANGES), horizontal=True)
    lo, hi = ERA_RANGES[preset] or st.slider("Year range", YEAR_MIN, YEAR_MAX, (-500, 1500), 10,
                                              help="Negative values are BCE")
    cats = query("SELECT DISTINCT category FROM events ORDER BY category")["category"].tolist()
    chosen = st.multiselect("Categories", cats, default=cats)

    df = query("SELECT * FROM events WHERE year BETWEEN ? AND ? ORDER BY year", (lo, hi))
    df = df[df["category"].isin(chosen)]
    if df.empty:
        st.info("No events in this range. Add rows to data/events.csv to extend the timeline.")
        return

    # Cinematic scroll + play view (rendered in an iframe)
    cols = ["year", "title", "category", "description", "source"]
    page = "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" + \
           cinematic_html(df[cols].to_dict("records")) + "</body></html>"
    if hasattr(st, "iframe"):          # newer Streamlit (components.v1.html is being removed)
        st.iframe(page, height=660)
    else:                              # older Streamlit versions
        components.html(page, height=660, scrolling=False)

    with st.expander("Overview chart (all events at once)"):
        d2 = df.assign(label=df["year"].map(fmt_year))
        fig = px.scatter(d2, x="year", y="category", color="category", hover_name="title",
                         color_discrete_map=CAT_COLOURS,
                         hover_data={"label": True, "year": False, "category": False})
        fig.update_traces(marker=dict(size=14, line=dict(width=1, color="#444")))
        tv, tt = year_ticks(d2["year"])
        fig.update_xaxes(tickvals=tv, ticktext=tt, title="")
        fig.update_yaxes(title="")
        fig.add_vline(x=year, line_dash="dot", line_color="#b08d57", annotation_text="selected year")
        st.plotly_chart(style_fig(fig, dark, 360), width="stretch")

    st.subheader("Explore an event")
    title = st.selectbox("Event", df["title"],
                         format_func=lambda t: f"{fmt_year(df[df.title == t].year.iloc[0])} - {t}")
    ev = df[df.title == title].iloc[0]
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"<div class='card'><h3>{ev.title}</h3><div class='meta'>{fmt_year(ev.year)} - {ev.category}</div>"
                    f"<p>{ev.description}</p><div class='meta'>Source: {ev.source}</div></div>", unsafe_allow_html=True)
        snap, polities = polity_at(ev.lat, ev.lon, int(ev.year))
        st.markdown(f"**GIS lookup:** in the {fmt_year(snap)} border snapshot (nearest to this event) the location "
                    f"falls within: **{', '.join(polities) if polities else 'no mapped polity'}**.")
        st.caption("Snapshots can be centuries away from the event, so treat this as context, not proof.")
        st.button("Show on map", on_click=_show_on_map, args=(ev.to_dict(),))
    with right:
        m = base_map((ev.lat, ev.lon), 5, dark)
        folium.Marker((ev.lat, ev.lon), tooltip=ev.title).add_to(m)
        st_folium(m, height=300, use_container_width=True, returned_objects=[], key=f"mini_{ev.id}")
