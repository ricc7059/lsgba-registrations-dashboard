"""Render the dashboard as one HTML document with local brand assets.

Layout is a fixed left rail carrying the LSGBA badge and one nav item per open
registration, with a scoreboard-style headline and card surfaces in the main
column. Colours are sampled from the association's own badge: the ring maroon,
the cougar's warmer maroon, and the cream and gold of the basketball.

The only external files referenced are under assets/ in this same repo. No CDN,
no remote font, no fetch.
"""

import datetime

# Sampled directly from assets/lsgba-badge-solid.png.
MAROON = "#8B1D41"        # the badge ring
MAROON_DEEP = "#5E1230"   # darker end of the scoreboard gradient
MAROON_BAR = "#A82A55"    # lifted for legibility as a chart series on charcoal
COUGAR = "#8B1F2E"        # the cougar's warmer maroon
GOLD = "#D2B77C"          # basketball seams, brightened to hold up on charcoal
GOLD_DIM = "#8A7647"
CREAM = "#E8D8B8"         # the basketball fill
GROUND = "#16171A"
SURFACE = "#1F2126"
SURFACE_2 = "#262A30"
EDGE = "#31363E"
TEXT = "#ECEDEF"
TEXT_DIM = "#8E959F"

NO_RESPONSE = "No response"


def escape(text):
    return (str(text)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def days_until(start, today):
    if not start:
        return None
    start_date = datetime.date(*[int(p) for p in start.split("-")])
    today_date = datetime.date(*[int(p) for p in today.split("-")])
    return (start_date - today_date).days


def unique_slugs(tabs):
    """Give every tab a distinct, non-empty slug so DOM ids cannot collide."""
    seen = {}
    slugs = []
    for index, tab in enumerate(tabs):
        base = (tab.get("slug") or tab.get("id") or "").strip()
        if not base:
            base = "registration-%d" % (index + 1)
        if base in seen:
            seen[base] += 1
            base = "%s-%d" % (base, seen[base])
        else:
            seen[base] = 1
        slugs.append(base)
    return slugs


def _countdown_text(event, today):
    if not event or not event.get("start"):
        return ""
    days = days_until(event["start"], today)
    if days is None:
        return ""
    if days > 1:
        return "%d days out" % days
    if days == 1:
        return "Tomorrow"
    if days == 0:
        return "Today"
    return "Finished"


def _countdown_reading(event, today):
    """(value, suffix) for the countdown cell, so the digit stays the big thing."""
    if not event or not event.get("start"):
        return ("—", "no date set")
    days = days_until(event["start"], today)
    if days is None:
        return ("—", "no date set")
    if days > 1:
        return ("%d" % days, "days out")
    if days == 1:
        return ("1", "day out")
    if days == 0:
        return ("0", "today")
    return ("—", "finished")


def _delta_reading(tab):
    """(value, suffix). Every scoreboard cell reads as a figure, like a real one."""
    if tab.get("previous") is None:
        return ("—", "first run")
    delta = tab.get("delta", 0)
    if delta > 0:
        return ("+%d" % delta, "since last run")
    if delta < 0:
        return ("−%d" % abs(delta), "since last run")
    return ("—", "no change")


def _bars(pairs):
    """Horizontal bars. Numbers are tabular so they align down the column."""
    if not pairs:
        return '<p class="empty">Nothing recorded yet.</p>'
    top = max(count for _, count in pairs) or 1
    rows = []
    for label, count in pairs:
        width = max(1.5, 100.0 * count / top)
        rows.append(
            '<div class="bar-row">'
            '<span class="bar-label">%s</span>'
            '<span class="bar-track"><span class="bar-fill" style="width:%.1f%%"></span></span>'
            '<span class="bar-value">%d</span>'
            '</div>' % (escape(label), width, count))
    return '<div class="bars">%s</div>' % "".join(rows)


def _split_no_response(values):
    """Pull 'No response' out so it cannot flatten the answers that matter.

    A question where 20 of 23 skipped it would otherwise scale every real answer
    to a sliver. The count still gets reported, just as a caption rather than a
    bar competing with the signal.
    """
    answered = [(label, count) for label, count in values if label != NO_RESPONSE]
    skipped = sum(count for label, count in values if label == NO_RESPONSE)
    return answered, skipped


def _timeline(points):
    """Cumulative line over per-day bars, drawn as inline SVG."""
    if not points:
        return '<p class="empty">No signups yet.</p>'

    width, height = 640, 150
    pad_x, pad_top, pad_bottom = 18, 14, 30
    inner_w = width - pad_x * 2
    inner_h = height - pad_top - pad_bottom
    peak = max(point["cumulative"] for point in points) or 1
    daily_peak = max(point["new"] for point in points) or 1
    single = len(points) < 2
    step = 0.0 if single else inner_w / float(len(points) - 1)

    def x_at(index):
        return pad_x + inner_w / 2.0 if single else pad_x + step * index

    # Per-day bars are the association's maroon so they read as a second series
    # rather than a dimmer version of the gold cumulative line.
    bars = []
    for index, point in enumerate(points):
        bar_h = inner_h * (point["new"] / float(daily_peak)) * 0.62
        bar_w = 22.0 if single else max(8.0, min(28.0, step * 0.4))
        bars.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
            % (x_at(index) - bar_w / 2.0, pad_top + inner_h - bar_h,
               bar_w, bar_h, MAROON_BAR))

    coords = [(x_at(i), pad_top + inner_h - inner_h * (p["cumulative"] / float(peak)))
              for i, p in enumerate(points)]
    line = " ".join("%.1f,%.1f" % point for point in coords)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x, y, GOLD)
                   for x, y in coords)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">%s</text>'
        % (coords[i][0], height - 10, points[i]["date"][5:].replace("-", "/"))
        for i in range(len(points)))

    return (
        '<svg viewBox="0 0 %d %d" class="timeline" role="img" '
        'aria-label="Cumulative signups by day">'
        '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
        '%s<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5" '
        'stroke-linejoin="round" stroke-linecap="round"/>%s%s</svg>'
        % (width, height,
           pad_x, pad_top + inner_h, width - pad_x, pad_top + inner_h, EDGE,
           "".join(bars), line, GOLD, dots, labels))


def _board_cell(label, value, suffix):
    return ('<div class="board-cell">'
            '<span class="board-label">%s</span>'
            '<span class="board-value">%s</span>'
            '<span class="board-suffix">%s</span>'
            '</div>' % (escape(label), escape(value), escape(suffix)))


def _panel(tab, slug, today, is_first):
    metrics = tab["metrics"]
    event = tab.get("event") or {}
    countdown_value, countdown_suffix = _countdown_reading(event, today)
    delta_value, delta_suffix = _delta_reading(tab)

    board = "".join([
        _board_cell("Registered", "%d" % metrics.get("total", 0), "athletes"),
        _board_cell("Countdown", countdown_value, countdown_suffix),
        _board_cell("Change", delta_value, delta_suffix),
    ])

    cards = ['<section class="card"><h3>By grade</h3>%s</section>'
             % _bars(metrics.get("grades", []))]

    for dimension in metrics.get("dimensions", []):
        answered, skipped = _split_no_response(dimension["values"])
        caption = ('<p class="caption">%d didn\'t answer</p>' % skipped) if skipped else ""
        cards.append(
            '<section class="card"><h3>%s</h3>%s%s</section>'
            % (escape(dimension["question"]), _bars(answered), caption))

    return (
        '<section class="tab-panel%s" id="panel-%s" role="tabpanel" aria-label="%s">'
        '  <header class="panel-head">'
        '    <h2>%s</h2>'
        '    <p class="dates">%s</p>'
        '  </header>'
        '  <div class="board">%s</div>'
        '  <div class="card-grid">%s</div>'
        '  <section class="card"><h3>Signups over time</h3>%s</section>'
        '</section>'
        % (" is-active" if is_first else "", escape(slug), escape(tab["name"]),
           escape(tab["name"]), escape(event.get("label", "")),
           board, "".join(cards),
           _timeline(metrics.get("timeline", []))))


STYLE = """
:root{--maroon:%s;--maroon-deep:%s;--cougar:%s;--gold:%s;--gold-dim:%s;
--cream:%s;--ground:%s;--surface:%s;--surface-2:%s;--edge:%s;--text:%s;--dim:%s;
--sans:"Avenir Next","Segoe UI Variable","Segoe UI",system-ui,-apple-system,
Helvetica,Arial,sans-serif;
--mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--ground);color:var(--text);font-family:var(--sans);
-webkit-font-smoothing:antialiased;font-size:15px;line-height:1.45}
.num,.board-value,.bar-value,.tab-count,.axis{font-family:var(--mono);
font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

.shell{display:flex;min-height:100vh;align-items:stretch}

/* ---- left rail ---- */
.rail{flex:0 0 268px;background:var(--surface);border-right:1px solid var(--edge);
padding:26px 20px;display:flex;flex-direction:column;gap:26px}
.brand{display:flex;align-items:center;gap:13px}
.brand img{width:54px;height:54px;flex:0 0 54px}
.brand-org{margin:0;font-size:.95rem;font-weight:800;letter-spacing:.02em;
line-height:1.15}
.brand-sub{margin:2px 0 0;font-size:.72rem;color:var(--dim);letter-spacing:.13em;
text-transform:uppercase}
.rail-label{margin:0 0 10px;font-size:.66rem;letter-spacing:.19em;
text-transform:uppercase;color:var(--dim);font-weight:700}
.tabs{display:flex;flex-direction:column;gap:6px}
.tab-button{display:flex;align-items:center;gap:10px;width:100%%;text-align:left;
background:transparent;border:1px solid transparent;border-radius:11px;
padding:11px 13px;color:var(--dim);font-family:inherit;font-size:.83rem;
font-weight:600;cursor:pointer;transition:background .15s,color .15s}
.tab-button:hover{background:var(--surface-2);color:var(--text)}
.tab-button:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.tab-button.is-active{background:var(--maroon);border-color:rgba(210,183,124,.5);
color:#fff}
.tab-name{flex:1;line-height:1.3}
.tab-count{font-size:.9rem;font-weight:700;color:var(--gold)}
.rail-foot{margin-top:auto}
.stamp{margin:0;font-size:.78rem;color:var(--text)}

/* ---- main column ---- */
.main{flex:1;min-width:0;padding:30px 34px 56px}
.tab-panel{display:none}
.tab-panel.is-active{display:block}
.panel-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;
margin-bottom:20px}
.panel-head h2{margin:0;font-size:1.32rem;font-weight:800;letter-spacing:-.01em}
.dates{margin:0;font-size:.83rem;color:var(--dim)}

/* ---- scoreboard ---- */
.board{display:grid;grid-template-columns:repeat(3,1fr);
background:linear-gradient(135deg,var(--maroon) 0%%,var(--maroon-deep) 100%%);
border:1px solid rgba(210,183,124,.28);border-radius:16px;overflow:hidden}
.board-cell{padding:20px 22px;border-right:1px solid rgba(210,183,124,.18);
display:flex;flex-direction:column;gap:7px}
.board-cell:last-child{border-right:0}
.board-label{font-size:.63rem;letter-spacing:.19em;text-transform:uppercase;
color:rgba(232,216,184,.75);font-weight:700}
.board-value{font-size:2.6rem;font-weight:700;color:var(--gold);line-height:1;
letter-spacing:-.02em}
.board-suffix{font-size:.73rem;color:rgba(232,216,184,.6);letter-spacing:.04em}

/* ---- cards ---- */
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));
gap:16px;margin-top:16px}
.card{background:var(--surface);border:1px solid var(--edge);border-radius:16px;
padding:19px 22px;margin-top:16px}
.card-grid .card{margin-top:0}
.card h3{margin:0 0 15px;font-size:.66rem;letter-spacing:.19em;
text-transform:uppercase;color:var(--dim);font-weight:700}
.caption{margin:12px 0 0;font-size:.76rem;color:var(--dim)}

/* ---- bars ---- */
.bar-row{display:grid;grid-template-columns:118px 1fr 34px;align-items:center;
gap:12px;margin-bottom:9px}
.bar-row:last-child{margin-bottom:0}
.bar-label{font-size:.83rem;overflow:hidden;text-overflow:ellipsis;
white-space:nowrap}
.bar-track{background:rgba(232,216,184,.07);border-radius:6px;height:11px;
overflow:hidden}
.bar-fill{display:block;height:100%%;border-radius:6px;
background:linear-gradient(90deg,var(--gold-dim),var(--gold))}
.bar-value{font-size:.86rem;font-weight:700;text-align:right;color:var(--gold)}
.timeline{width:100%%;height:auto;display:block}
.axis{fill:var(--dim);font-size:11px}
.empty{color:var(--dim);font-size:.83rem;margin:0}
.footer{margin-top:26px;font-size:.72rem;color:var(--dim)}

@media(max-width:860px){
.shell{flex-direction:column}
.rail{flex:0 0 auto;border-right:0;border-bottom:1px solid var(--edge);
padding:18px 16px;gap:16px}
.rail-foot{margin-top:0}
.tabs{flex-direction:row;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.tabs::-webkit-scrollbar{display:none}
.tab-button{flex:0 0 auto;white-space:nowrap;border-radius:999px}
.tab-name{flex:0 0 auto}
.main{padding:20px 16px 44px}
.board{grid-template-columns:1fr}
.board-cell{border-right:0;border-bottom:1px solid rgba(210,183,124,.18);
padding:15px 18px;flex-direction:row;align-items:baseline;justify-content:space-between}
.board-cell:last-child{border-bottom:0}
.board-value{font-size:1.7rem}
.card-grid{grid-template-columns:1fr}
.bar-row{grid-template-columns:96px 1fr 30px}
}
@media(prefers-reduced-motion:reduce){*{transition:none !important}}
""" % (MAROON, MAROON_DEEP, COUGAR, GOLD, GOLD_DIM, CREAM, GROUND, SURFACE,
       SURFACE_2, EDGE, TEXT, TEXT_DIM)

SCRIPT = """
document.querySelectorAll('.tab-button').forEach(function(button){
  button.addEventListener('click', function(){
    document.querySelectorAll('.tab-button').forEach(function(other){
      other.classList.remove('is-active');
      other.setAttribute('aria-selected','false');
    });
    document.querySelectorAll('.tab-panel').forEach(function(panel){
      panel.classList.remove('is-active');
    });
    button.classList.add('is-active');
    button.setAttribute('aria-selected','true');
    document.getElementById('panel-' + button.dataset.slug).classList.add('is-active');
  });
});
"""


def _event_sort_key(tab):
    """Soonest event first; registrations without dates fall to the end."""
    event = tab.get("event") or {}
    start = event.get("start")
    return (0, start, tab.get("name", "")) if start else (1, "", tab.get("name", ""))


def render_dashboard(tabs, generated_at, today):
    tabs = sorted(tabs, key=_event_sort_key)
    slugs = unique_slugs(tabs)

    if tabs:
        buttons = "".join(
            '<button class="tab-button%s" data-slug="%s" role="tab" aria-selected="%s">'
            '<span class="tab-name">%s</span>'
            '<span class="tab-count">%d</span></button>'
            % (" is-active" if i == 0 else "", escape(slugs[i]),
               "true" if i == 0 else "false", escape(tab["name"]),
               tab["metrics"].get("total", 0))
            for i, tab in enumerate(tabs))
        panels = "".join(_panel(tab, slugs[i], today, i == 0)
                         for i, tab in enumerate(tabs))
    else:
        buttons = '<p class="empty">No active registrations.</p>'
        panels = ('<div class="card"><p class="empty">No active registrations. '
                  'Nothing is open in SportsEngine right now.</p></div>')

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        '<link rel="icon" href="assets/favicon.png">'
        "<title>LSGBA Registrations</title><style>%s</style></head><body>"
        '<div class="shell">'
        '  <aside class="rail">'
        '    <div class="brand">'
        '      <img src="assets/lsgba-badge.png" alt="Lakeville South Basketball">'
        '      <div><p class="brand-org">Lakeville South</p>'
        '           <p class="brand-sub">Girls Basketball</p></div>'
        '    </div>'
        '    <div><p class="rail-label">Open registrations</p>'
        '         <nav class="tabs" role="tablist">%s</nav></div>'
        '    <div class="rail-foot"><p class="rail-label">Updated</p>'
        '         <p class="stamp num">%s</p></div>'
        '  </aside>'
        '  <main class="main">%s'
        '    <p class="footer">Aggregate counts only. Rebuilt on demand from '
        'SportsEngine.</p>'
        '  </main>'
        '</div>'
        "<script>%s</script></body></html>\n"
        % (STYLE, buttons, escape(generated_at), panels, SCRIPT))
