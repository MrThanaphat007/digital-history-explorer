"""Timeline page with two views:
1) a cinematic scroll-through timeline with an auto-play mode, and
2) a radial cause-and-effect tree that branches outward from one event.
Both link to the map and to the GIS polity lookup."""
import json
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium
from db import init_db, query
from geo import polity_at
from utils import base_map, cert_badge, src_link, fmt_year, year_ticks, style_fig, ERA_RANGES, YEAR_MIN, YEAR_MAX

# One colour per event category (used by the cinematic view and the overview chart)
CAT_COLOURS = {"War": "#B5654A", "Politics": "#8A8F70", "Law": "#C2A66B", "Religion": "#9C7A8C",
               "Exploration": "#D08C4F", "Disease": "#8C8C86", "Trade": "#B8A87A", "Science": "#7F9C8A"}


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
  #wrap{position:relative;height:640px;background:radial-gradient(ellipse at top,#2a2d28 0%,#1d1f1c 70%);
        color:#eee;border-radius:10px;overflow:hidden;border:1px solid #3a3d37}
  #hud{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;gap:14px;
       padding:10px 16px;background:linear-gradient(#1d1f1cee,#1d1f1c00)}
  #year{font:700 2.4rem 'Libre Baskerville',Georgia,serif;color:#d68e73;min-width:190px;
        text-shadow:0 0 18px #d68e7366}
  button,select{background:#262823;color:#eee;border:1px solid #4a4d46;border-radius:6px;padding:7px 14px;
        font-size:.9rem;cursor:pointer} button:hover{border-color:#d68e73}
  #bar{position:absolute;top:0;left:0;height:3px;background:#d68e73;width:0;z-index:6;transition:width .5s}
  #stage{position:absolute;inset:0;overflow-y:auto;padding:90px 0 260px;scroll-behavior:smooth}
  #line{position:absolute;left:50%;top:0;bottom:0;width:2px;background:linear-gradient(#0000,#d68e7388,#0000)}
  .item{position:relative;width:50%;padding:14px 38px;opacity:0;transform:translateY(34px);
        transition:opacity .7s,transform .7s}
  .item.show{opacity:.55;transform:none} .item.active{opacity:1}
  .item.left{left:0;text-align:right} .item.right{left:50%}
  .dot{position:absolute;top:30px;width:14px;height:14px;border-radius:50%;background:var(--c);
       box-shadow:0 0 0 4px #1d1f1c,0 0 14px var(--c)}
  .left .dot{right:-7px} .right .dot{left:-7px}
  .card{background:#262823;border:1px solid #3a3d37;border-top:3px solid var(--c);border-radius:8px;
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


def _render_cinematic(year: int, dark: bool):
    st.caption("Scroll through history, or press Play to watch events unfold in order.")
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
        st.markdown(f"<div class='card'><h3>{ev.title}</h3><div class='meta'>{fmt_year(ev.year)}{cert_badge(ev.get('date_certainty'))} - {ev.category}</div>"
                    f"<p>{ev.description}</p><div class='meta'>Source: {src_link(ev.source, ev.get('url'))}</div></div>", unsafe_allow_html=True)
        snap, polities = polity_at(ev.lat, ev.lon, int(ev.year))
        st.markdown(f"**GIS lookup:** in the {fmt_year(snap)} border snapshot (nearest to this event) the location "
                    f"falls within: **{', '.join(polities) if polities else 'no mapped polity'}**.")
        st.caption("Snapshots can be centuries away from the event, so treat this as context, not proof.")
        st.button("Show on map", on_click=_show_on_map, args=(ev.to_dict(),), key="show_map_timeline")
    with right:
        m = base_map((ev.lat, ev.lon), 5, dark)
        folium.Marker((ev.lat, ev.lon), tooltip=ev.title).add_to(m)
        st_folium(m, height=300, use_container_width=True, returned_objects=[], key=f"mini_{ev.id}")



# ---------------------------------------------------------------------------
# Cause-and-effect tree (one tree per starting event, or the whole "forest")
# ---------------------------------------------------------------------------
def tree_html(trees: list[dict], linked: dict, dark: bool) -> str:
    """Radial branching trees drawn as SVG in JavaScript. One tree = the starting event in the
    centre with consequences in rings around it. Several trees are laid out in a chronological
    grid (the 'forest'). All text is inserted with textContent, so data cannot inject markup."""
    data = json.dumps({"trees": trees, "linked": linked, "dark": dark}).replace("</", "<\\/")
    return TREE_TEMPLATE.replace("__DATA__", data)


TREE_TEMPLATE = """
<style>
  *{box-sizing:border-box} body{margin:0;font-family:'DM Sans','Noto Sans Thai',system-ui,sans-serif}
  #wrap{--bg1:#2a2d28;--bg2:#1d1f1c;--tx:#eee;--mut:#9aa3ad;--pn:#262823;--ln:#3a3d37;--gold:#d68e73;
        --pb:#000;--pf:#f2f2f2;--pbd:#555;--dbt:#e0a040;
        position:relative;height:700px;border-radius:10px;overflow:hidden;border:1px solid var(--ln);
        background:radial-gradient(ellipse at center,var(--bg1) 0%,var(--bg2) 75%);color:var(--tx)}
  #wrap.light{--pb:#fff;--pf:#1d1d1d;--pbd:#bdbdbd;--dbt:#a8620a;--bg1:#fffdf8;--bg2:#efe6d3;--tx:#2a2420;--mut:#6d635a;--pn:#fffdf8;--ln:#d9ccb2;--gold:#A6644D}
  svg{width:100%;height:100%;display:block;cursor:grab;touch-action:none} svg:active{cursor:grabbing}
  .link{fill:none;stroke-linecap:round} .node{cursor:pointer}
  .lbl{fill:var(--tx);font-size:12.5px;pointer-events:none} .yr{fill:var(--mut);font-size:11px;pointer-events:none}
  svg.focus .link:not(.hl){opacity:.15} svg.focus .node:not(.hl){opacity:.35}
  svg.hide2 .dd2,svg.hide2 .dd3,svg.hide2 .dd4,svg.hide2 .dd5{display:none} svg.hide1 .dd1{display:none}
  .node circle.main{stroke:var(--bg2);stroke-width:3}
  #bar{position:absolute;top:10px;left:12px;right:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;z-index:3}
  button{background:var(--pn);color:var(--tx);border:1px solid var(--ln);border-radius:6px;padding:6px 12px;font:inherit;font-size:.85rem;cursor:pointer}
  button:hover{border-color:var(--gold)}
  #legend{font-size:.75rem;color:var(--mut);margin-left:auto;text-align:right}
  #pop{position:absolute;z-index:6;width:min(320px,calc(100% - 24px));background:var(--pb);color:var(--pf);
       border:1px solid var(--pbd);border-radius:6px;padding:12px 16px 14px;font-size:.92rem;line-height:1.7;box-shadow:0 10px 30px #0008}
  #pop[hidden]{display:none}
  #pop .t{font-weight:700;font-size:1rem;padding-right:22px} #pop .m{font-size:.76rem;opacity:.7;margin:2px 0 8px}
  #pop .s{font-size:.74rem;opacity:.65;margin-top:10px;line-height:1.5} #pop a{color:inherit;text-decoration:underline}
  #px{position:absolute;top:2px;right:4px;border:0;background:none;color:var(--pf);font-size:1.3rem;padding:2px 8px;line-height:1}
  #px:hover{border:0;color:var(--gold)}
  .badge{display:inline-block;padding:0 8px;border-radius:10px;font-size:.7rem;border:1px solid currentColor;margin-left:8px}
  .badge.debated{border-style:dashed;color:var(--dbt)}
  @media (max-width:640px){#legend{display:none}}
</style>
<div id="wrap">
  <div id="bar">
    <button id="replay">&#8635; เล่นแอนิเมชันอีกครั้ง</button><button id="zin">+</button>
    <button id="zout">&minus;</button><button id="zfit">ดูทั้งหมด</button>
    <div id="legend">คลิกที่จุดเพื่ออ่านคำอธิบาย<br>เส้นทึบ = ยอมรับทั่วไป &middot; เส้นประ = ยังถกเถียง &middot; &#8599; = เป็นเหตุการณ์ในระบบด้วย</div>
  </div>
  <svg id="svg"><g id="links"></g><g id="nodes"></g></svg>
  <div id="pop" hidden><button id="px" aria-label="ปิด">&times;</button><div class="t" id="pt1"></div>
    <div class="m" id="pm"></div><div id="pth"></div><div class="s" id="ps"></div></div>
</div>
<script>
const D = __DATA__, NS = 'http://www.w3.org/2000/svg';
document.getElementById('wrap').classList.toggle('light', !D.dark);
const svg = document.getElementById('svg'), gL = document.getElementById('links'), gN = document.getElementById('nodes');
const FOREST = D.trees.length > 1, K = FOREST ? 0.62 : 1;
const fmt = y => (y === null || y === undefined || y === '') ? '' : (y < 0 ? Math.abs(y) + ' BCE' : y + ' CE');
const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
const PALETTE = ['#d98324', '#4a90c2', '#3f8f6b', '#b565a7', '#c0392b', '#8aa13a', '#5b7f95'];
const RADII = [0, 150, 270, 370, 460, 540].map(r => r * K);
const SEG = (typeof Intl !== 'undefined' && Intl.Segmenter) ? new Intl.Segmenter('th', {granularity: 'word'}) : null;

// ---- build each tree from flat rows (parent id -> children)
function build(t) {
  const byId = {}; t.nodes.forEach(n => byId[n.id] = Object.assign({children: []}, n));
  const root = {id: 'root_' + t.root.id, label: t.root.title, year: t.root.year, detail: t.root.description,
                th: t.root.th, source: t.root.source, url: t.root.url, certainty: 'established', children: [], linked: null};
  Object.keys(byId).forEach(k => { const n = byId[k]; (n.parent && byId[n.parent] ? byId[n.parent] : root).children.push(n); });
  return root;
}
// ---- radial layout: each subtree gets an angle slice proportional to its leaf count
const leaves = n => n.children.length ? n.children.reduce((s, c) => s + leaves(c), 0) : 1;
function layout(n, a0, a1, d, branch, parent, ox, oy) {
  n.depth = d; n.up = parent; n.a = (a0 + a1) / 2; n.branch = branch; n.ox = ox; n.oy = oy;
  n.r = RADII[Math.min(d, RADII.length - 1)];
  n.x = ox + n.r * Math.cos(n.a); n.y = oy + n.r * Math.sin(n.a);
  let a = a0; const L = leaves(n);
  n.children.forEach((c, i) => { const span = (a1 - a0) * leaves(c) / L; layout(c, a, a + span, d + 1, d === 0 ? i : branch, n, ox, oy); a += span; });
}
const roots = D.trees.map(build);
const COLS = FOREST ? Math.ceil(Math.sqrt(roots.length * 1.3)) : 1;
const CW = 2 * 540 * K + 460, CH = 2 * 540 * K + 200;
roots.forEach((r, i) => layout(r, -Math.PI / 2, 1.5 * Math.PI, 0, -1, null, (i % COLS) * CW, Math.floor(i / COLS) * CH));
const all = []; roots.forEach(r => (function walk(n) { all.push(n); n.children.forEach(walk); })(r));
const colour = n => n.branch < 0 ? (D.dark ? '#d68e73' : '#A6644D') : PALETTE[n.branch % PALETTE.length];
const pol = (n, a, r) => [n.ox + r * Math.cos(a), n.oy + r * Math.sin(a)];

// ---- links (curved radial connectors)
const linkEls = [];
all.filter(n => n.up).forEach(n => {
  const p = n.up, rm = (p.r + n.r) / 2;
  const [x0, y0] = pol(n, p.a, p.r), [x1, y1] = pol(n, p.a, rm), [x2, y2] = pol(n, n.a, rm), [x3, y3] = pol(n, n.a, n.r);
  const path = el('path', {d: `M${x0},${y0} C${x1},${y1} ${x2},${y2} ${x3},${y3}`, class: 'link',
    stroke: colour(n), 'stroke-width': Math.max(2, 6 - n.depth * 1.3), 'stroke-opacity': .85}, gL);
  path.dataset.depth = n.depth; path.dataset.debated = n.certainty === 'debated' ? 1 : 0; n.linkEl = path; linkEls.push(path);
});
// word wrap (Thai has no spaces, so use the browser's word segmenter when available)
function wrap(text, max) {
  const toks = SEG ? Array.from(SEG.segment(text), s => s.segment) : text.split(/(?<= )/);
  const lines = []; let cur = '';
  toks.forEach(w => { if ((cur + w).trim().length > max && cur.trim()) { lines.push(cur.trim()); cur = w; } else cur += w; });
  if (cur.trim()) lines.push(cur.trim()); return lines.slice(0, 3);
}
// ---- nodes
all.forEach(n => {
  const g = el('g', {class: 'node', transform: `translate(${n.x},${n.y})`}, gN);
  const rad = n.depth === 0 ? (FOREST ? 64 : 50) : 11, fs = n.depth === 0 && FOREST ? 17 : 12.5;
  if (n.certainty === 'debated') el('circle', {r: rad + 6, fill: 'none', stroke: '#e0a040', 'stroke-dasharray': '4 3', 'stroke-width': 1.5}, g);
  el('circle', {r: rad + 9, fill: 'transparent'}, g);              // larger invisible click target
  el('circle', {r: rad, fill: colour(n), class: 'main'}, g);
  el('title', {}, g).textContent = n.label + (fmt(n.year) ? ' (' + fmt(n.year) + ')' : '');
  const cls = 'dd' + n.depth;
  const txt = (lines, x, y0, anchor, c, size) => lines.forEach((ln, i) => { const t = el('text', {x, y: y0 + i * (size ? size + 2.5 : 15), 'text-anchor': anchor, class: c + ' ' + cls}, g);
    if (size) t.style.fontSize = size + 'px'; t.textContent = ln; });
  if (n.depth === 0) {
    const lines = wrap(n.label, FOREST ? 11 : 14); const lh = fs + 2.5;
    txt(lines, 0, -((lines.length - 1) * lh) / 2 - 2, 'middle', 'lbl', fs);
    const y = el('text', {x: 0, y: (lines.length * lh) / 2 + 12, 'text-anchor': 'middle', class: 'yr ' + cls}, g); y.textContent = fmt(n.year);
    Array.from(g.childNodes).forEach(c => { if (c.tagName === 'text') c.style.fill = '#1d1f1c'; });
  } else {
    const cosA = Math.cos(n.a), side = cosA < -0.25 ? 'end' : cosA > 0.25 ? 'start' : 'middle';
    const lines = wrap(n.label + (n.linked ? ' \u2197' : ''), 22);
    const dx = side === 'end' ? -(rad + 8) : side === 'start' ? rad + 8 : 0;
    const dy = side === 'middle' ? (Math.sin(n.a) > 0 ? rad + 16 : -(rad + 8) - lines.length * 15 + 15) : -4;
    txt(lines, dx, dy, side, 'lbl');
    if (fmt(n.year)) { const y = el('text', {x: dx, y: dy + lines.length * 15, 'text-anchor': side, class: 'yr ' + cls}, g); y.textContent = fmt(n.year); }
  }
  g.addEventListener('click', ev => { if (ev.stopPropagation) ev.stopPropagation(); if (moved) return;
    if (FOREST && n.depth === 0 && vb.w > 2200) focusTree(n);       // first click on a tree zooms to it
    select(n); });
  n.el = g;
});

// ---- click a dot: highlight its path back to the centre and open a Thai explanation box
const pop = document.getElementById('pop');
function clearFocus() { svg.classList.remove('focus'); all.forEach(m => { m.el.classList.remove('hl'); if (m.linkEl) m.linkEl.classList.remove('hl'); }); }
function closePop() { pop.hidden = true; clearFocus(); }
function placePop(n) {
  pop.hidden = false;
  const wr = document.getElementById('wrap').getBoundingClientRect(), pt = svg.createSVGPoint(); pt.x = n.x; pt.y = n.y;
  const sp = pt.matrixTransform(svg.getScreenCTM()), w = pop.offsetWidth || 300, h = pop.offsetHeight || 150;
  let x = sp.x - wr.left + 18, y = sp.y - wr.top + 14;
  if (x + w > wr.width - 8) x = sp.x - wr.left - w - 18;
  if (y + h > wr.height - 8) y = sp.y - wr.top - h - 14;
  pop.style.left = Math.max(8, x) + 'px'; pop.style.top = Math.max(8, y) + 'px';
}
function select(n) {
  document.getElementById('pt1').textContent = n.label;
  const pm = document.getElementById('pm'); pm.textContent = (fmt(n.year) || 'ไม่ระบุปีที่แน่ชัด') + (n.depth ? '' : ' \u00b7 เหตุการณ์เริ่มต้น');
  if (n.depth) { const b = document.createElement('span'); b.className = 'badge' + (n.certainty === 'debated' ? ' debated' : '');
                 b.textContent = n.certainty === 'debated' ? 'ยังเป็นข้อถกเถียง' : 'ยอมรับกันทั่วไป'; pm.appendChild(b); }
  document.getElementById('pth').textContent = n.th || n.detail || '';
  const ps = document.getElementById('ps'); ps.textContent = 'แหล่งที่มา: ' + (n.source || '-');
  if (n.linked && D.linked[String(n.linked)]) { const l = D.linked[String(n.linked)]; ps.textContent += ' \u00b7 ตรงกับเหตุการณ์ในระบบ: ' + l.title + ' (' + fmt(l.year) + ')'; }
  if (n.url && String(n.url).startsWith('https://')) { const a = document.createElement('a'); a.href = n.url; a.target = '_blank';
    a.rel = 'noopener'; a.textContent = ' \u2197 เปิดแหล่งที่มา'; ps.appendChild(a); }
  const path = new Set(); for (let c = n; c; c = c.up) path.add(c.id);
  svg.classList.add('focus');
  all.forEach(m => { m.el.classList.toggle('hl', path.has(m.id)); if (m.linkEl) m.linkEl.classList.toggle('hl', path.has(m.id)); });
  placePop(n);
}
document.getElementById('px').onclick = closePop;
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePop(); });
svg.addEventListener('click', e => { if (!moved && !(e.target.closest && e.target.closest('.node'))) closePop(); });

// ---- growth animation: each ring draws outward after the previous one
let timers = [];
function play() {
  timers.forEach(clearTimeout); timers = [];
  linkEls.forEach(l => { const len = l.getTotalLength(); l.dataset.len = len; l.style.transition = 'none';
                         l.style.strokeDasharray = len; l.style.strokeDashoffset = len; });
  all.forEach(n => { n.el.style.transition = 'none'; n.el.style.opacity = n.depth === 0 ? 1 : 0; });
  void svg.getBoundingClientRect();
  const maxD = Math.max(...all.map(n => n.depth));
  for (let d = 1; d <= maxD; d++) timers.push(setTimeout(() => {
    linkEls.filter(l => +l.dataset.depth === d).forEach(l => { l.style.transition = 'stroke-dashoffset .8s ease'; l.style.strokeDashoffset = 0; });
    all.forEach(n => { if (n.depth === d) { n.el.style.transition = 'opacity .6s ease .5s'; n.el.style.opacity = 1; } });
    timers.push(setTimeout(() => linkEls.filter(l => +l.dataset.depth === d).forEach(l => {
      l.style.strokeDasharray = +l.dataset.debated ? '7 6' : 'none'; }), 900));
  }, (d - 1) * 800));
}

// ---- zoom / pan through the viewBox (labels of deeper rings hide when zoomed far out)
let vb = {x: -500, y: -380, w: 1000, h: 760}, moved = false;
function lod() { const sc = (svg.clientWidth || 900) / vb.w;
  svg.classList.toggle('hide2', FOREST && sc < 0.62); svg.classList.toggle('hide1', FOREST && sc < 0.38); }
function setVB() { svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`); lod(); }
function box(list) {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  list.forEach(n => { const left = n.depth && Math.cos(n.a) < -0.25, right = n.depth && Math.cos(n.a) > 0.25, rr = n.depth ? 0 : 80;
    x0 = Math.min(x0, n.x - (left ? 190 : 60) - rr); x1 = Math.max(x1, n.x + (right ? 190 : 60) + rr);
    y0 = Math.min(y0, n.y - 50 - rr); y1 = Math.max(y1, n.y + 70 + rr); });
  const ar = (svg.clientWidth || 900) / (svg.clientHeight || 700);
  let w = x1 - x0, h = y1 - y0; if (w / h < ar) w = h * ar; else h = w / ar;
  vb = {x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - h / 2, w, h}; setVB();
}
const fit = () => box(all);
function focusTree(rootNode) { box(all.filter(n => n.ox === rootNode.ox && n.oy === rootNode.oy)); }
function zoom(k, cx, cy) { closePop(); const px = cx === undefined ? vb.x + vb.w / 2 : cx, py = cy === undefined ? vb.y + vb.h / 2 : cy;
  vb = {x: px - (px - vb.x) * k, y: py - (py - vb.y) * k, w: vb.w * k, h: vb.h * k}; setVB(); }
svg.addEventListener('wheel', e => { e.preventDefault(); const r = svg.getBoundingClientRect();
  zoom(e.deltaY > 0 ? 1.1 : 0.9, vb.x + (e.clientX - r.left) / r.width * vb.w, vb.y + (e.clientY - r.top) / r.height * vb.h); }, {passive: false});
let drag = null;
svg.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY}; moved = false; });
window.addEventListener('pointermove', e => { if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
  if (moved) { closePop(); vb.x -= dx * vb.w / svg.clientWidth; vb.y -= dy * vb.h / svg.clientHeight; drag = {x: e.clientX, y: e.clientY}; setVB(); } });
window.addEventListener('pointerup', () => { drag = null; setTimeout(() => moved = false, 0); });
document.getElementById('zin').onclick = () => zoom(0.8);
document.getElementById('zout').onclick = () => zoom(1.25);
document.getElementById('zfit').onclick = fit;
document.getElementById('replay').onclick = play;
window.addEventListener('resize', fit);
fit(); play();
</script>
"""


def _load_impacts():
    """Read the impacts table. If the SQLite file was built before impacts.csv existed,
    rebuild it once (db.init_db is cached, so clear the cache first)."""
    try:
        return query("SELECT * FROM impacts")
    except Exception:
        try:
            init_db.clear()
            init_db()
            return query("SELECT * FROM impacts")
        except Exception:
            return None


def _drop_debated(df: pd.DataFrame) -> pd.DataFrame:
    """Remove debated nodes together with everything that hangs below them."""
    drop = set(df.loc[df["certainty"] == "debated", "id"])
    changed = True
    while changed:
        kids = set(df.loc[df["parent_id"].isin(drop), "id"]) - drop
        changed = bool(kids)
        drop |= kids
    return df[~df["id"].isin(drop)]


def _txt(v) -> str:
    """Text value from a DataFrame cell ('' when empty)."""
    return v if isinstance(v, str) else ""


def _th_or_en(row, th_col: str, en_col: str) -> str:
    """Prefer the Thai column, fall back to English."""
    return _txt(row.get(th_col)) or _txt(row.get(en_col))


def _tree_payload(ev: pd.DataFrame, imp: pd.DataFrame, root_ids, show_debated: bool):
    """Build the JSON-ready list of trees (Thai text preferred) and the linked-event lookup."""
    trees, linked_ids = [], set()
    for rid in root_ids:
        nodes = imp[imp["root_event_id"] == rid]
        if not show_debated:
            nodes = _drop_debated(nodes)
        recs = []
        for r in nodes.to_dict("records"):
            lk = None if pd.isna(r.get("linked_event_id")) else int(r["linked_event_id"])
            if lk:
                linked_ids.add(lk)
            recs.append({"id": r["id"], "parent": "" if pd.isna(r.get("parent_id")) else r["parent_id"],
                         "label": _th_or_en(r, "label_th", "label"),
                         "year": None if pd.isna(r.get("year")) else int(r["year"]),
                         "detail": _txt(r.get("detail")), "th": _txt(r.get("detail_th")),
                         "certainty": r["certainty"], "linked": lk, "source": _txt(r.get("source")),
                         "url": _txt(r.get("url"))})
        e = ev[ev["id"] == rid].iloc[0].to_dict()
        trees.append({"root": {"id": int(rid), "title": _th_or_en(e, "title_th", "title"), "year": int(e["year"]),
                               "description": _txt(e.get("description")), "th": _txt(e.get("description_th")),
                               "source": _txt(e.get("source")), "url": _txt(e.get("url"))}, "nodes": recs})
    linked = {str(int(r["id"])): {"title": _th_or_en(r, "title_th", "title"), "year": int(r["year"])}
              for r in ev[ev["id"].isin(linked_ids)].to_dict("records")}
    return trees, linked


ALL_TREES = "all"


def _render_tree(year: int, dark: bool):
    st.caption("เลือกเหตุการณ์เริ่มต้นไว้ตรงกลาง วงที่ขยายออกไปคือสิ่งที่เกิดตามมา "
               "คลิกที่จุดเพื่อดูคำอธิบายภาษาไทย ลากเพื่อเลื่อน เลื่อนล้อเมาส์เพื่อซูม")
    imp = _load_impacts()
    if imp is None or imp.empty:
        st.info("The cause-and-effect data is missing. Upload data/impacts.csv to the repository and reboot the app.")
        return
    ev = query("SELECT * FROM events")
    roots = ev[ev["id"].isin(imp["root_event_id"].unique())].sort_values(["year", "id"])
    titles = {int(r["id"]): f"{fmt_year(r['year'])} - {_th_or_en(r, 'title_th', 'title')}" for r in roots.to_dict("records")}
    options = [ALL_TREES] + list(titles)
    sel = st.selectbox("Starting event / เหตุการณ์เริ่มต้น", options, key="tree_root",
                       format_func=lambda i: f"★ ทุกต้นไม้รวมกัน ({len(titles)} เหตุการณ์ เรียงตามเวลา)" if i == ALL_TREES else titles[i])
    show_debated = st.toggle("Show debated links / แสดงข้อถกเถียง", value=True, key="tree_debated")

    ids = list(titles) if sel == ALL_TREES else [int(sel)]
    trees, linked = _tree_payload(ev, imp, ids, show_debated)
    if sel == ALL_TREES:
        st.caption("มุมมองรวม: ต้นไม้เรียงตามปีจากซ้ายไปขวา แล้วขึ้นแถวใหม่ ซูมเข้าเพื่ออ่านป้ายชื่อ "
                   "หรือคลิกที่วงกลมกลางของต้นไม้เพื่อซูมไปที่ต้นนั้น")
    page = ("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" + tree_html(trees, linked, dark)
            + "</body></html>")
    if hasattr(st, "iframe"):
        st.iframe(page, height=720)
    else:
        components.html(page, height=720, scrolling=False)

    if sel != ALL_TREES:
        root_ev = ev[ev["id"] == sel].iloc[0]
        st.button("Show starting event on map", on_click=_show_on_map, args=(root_ev.to_dict(),), key="show_map_tree")
    with st.expander("All branches with sources"):
        nodes = imp[imp["root_event_id"].isin(ids)]
        if not show_debated:
            nodes = pd.concat([_drop_debated(nodes[nodes["root_event_id"] == i]) for i in ids])
        tbl = nodes.assign(when=nodes["year"].map(lambda y: "" if pd.isna(y) else fmt_year(y)))
        show = [c for c in ["label_th", "label", "when", "certainty", "detail_th", "source", "url"] if c in tbl]
        st.dataframe(tbl[show], hide_index=True, width="stretch",
                     column_config={"url": st.column_config.LinkColumn("link", display_text="open")} if "url" in show else None)
    st.caption("Cause-and-effect links are interpretations. 'Debated' marks links where historians disagree or the "
               "connection is indirect. Check each against its source before citing.")


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Historical Timeline</h1></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Cinematic timeline", "Cause & effect tree"])
    with t1:
        _render_cinematic(year, dark)
    with t2:
        _render_tree(year, dark)
