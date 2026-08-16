"""Render the tabbed dashboard as one self-contained HTML document."""

import datetime

MAROON = "#7B1E2B"
MAROON_LIGHT = "#A32B3D"
GOLD = "#E0B44C"
GOLD_DIM = "#8A6E2F"
GROUND = "#14161A"
PANEL = "#1D2026"
PANEL_EDGE = "#2B3038"
TEXT = "#F2F3F5"
TEXT_DIM = "#9AA1AC"


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


def _countdown_text(event, today):
    if not event or not event.get("start"):
        return ""
    days = days_until(event["start"], today)
    if days is None:
        return ""
    if days > 1:
        return "%s &middot; %d days out" % (escape(event.get("label", "")), days)
    if days == 1:
        return "%s &middot; tomorrow" % escape(event.get("label", ""))
    if days == 0:
        return "%s &middot; today" % escape(event.get("label", ""))
    return "%s &middot; finished" % escape(event.get("label", ""))


def _delta_text(tab):
    if tab.get("previous") is None:
        return "First run"
    delta = tab.get("delta", 0)
    if delta > 0:
        return "+%d since last run" % delta
    if delta < 0:
        return "%d since last run" % delta
    return "No change since last run"


def _bar_chart(pairs):
    """Horizontal bars as a plain HTML grid — crisper than SVG at small sizes."""
    if not pairs:
        return '<p class="empty">No responses yet.</p>'
    top = max(count for _, count in pairs) or 1
    rows = []
    for label, count in pairs:
        width = max(2.0, 100.0 * count / top)
        rows.append(
            '<div class="bar-row">'
            '<span class="bar-label">%s</span>'
            '<span class="bar-track"><span class="bar-fill" style="width:%.1f%%"></span></span>'
            '<span class="bar-value">%d</span>'
            '</div>' % (escape(label), width, count))
    return '<div class="bars">%s</div>' % "".join(rows)


def _timeline_chart(points):
    """Cumulative line with per-day bars behind it, drawn as inline SVG."""
    if not points:
        return '<p class="empty">No signups yet.</p>'

    width, height, pad = 620, 200, 28
    inner_w = width - pad * 2
    inner_h = height - pad * 2
    peak = max(point["cumulative"] for point in points) or 1
    daily_peak = max(point["new"] for point in points) or 1
    step = inner_w / float(max(1, len(points) - 1)) if len(points) > 1 else 0.0

    bars = []
    for index, point in enumerate(points):
        x = pad + step * index if len(points) > 1 else pad + inner_w / 2.0
        bar_h = inner_h * (point["new"] / float(daily_peak)) * 0.55
        bar_w = max(6.0, min(26.0, step * 0.5)) if len(points) > 1 else 26.0
        bars.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s" opacity="0.45"/>'
            % (x - bar_w / 2.0, pad + inner_h - bar_h, bar_w, bar_h, GOLD_DIM))

    coords = []
    for index, point in enumerate(points):
        x = pad + step * index if len(points) > 1 else pad + inner_w / 2.0
        y = pad + inner_h - inner_h * (point["cumulative"] / float(peak))
        coords.append((x, y))

    line = " ".join("%.1f,%.1f" % point for point in coords)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x, y, GOLD)
                   for x, y in coords)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">%s</text>'
        % (coords[i][0], height - 8, points[i]["date"][5:].replace("-", "/"))
        for i in range(len(points)))

    return (
        '<svg viewBox="0 0 %d %d" class="timeline" role="img" '
        'aria-label="Cumulative signups over time">'
        '%s<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5" '
        'stroke-linejoin="round" stroke-linecap="round"/>%s%s'
        '<text x="%d" y="%d" class="axis">%d total</text></svg>'
        % (width, height, "".join(bars), line, GOLD, dots, labels,
           pad, pad - 10, peak))


def _panel(tab, today, is_first):
    metrics = tab["metrics"]
    dimension_blocks = []
    for dimension in metrics.get("dimensions", []):
        dimension_blocks.append(
            '<section class="block"><h3>%s</h3>%s</section>'
            % (escape(dimension["question"]), _bar_chart(dimension["values"])))

    return (
        '<div class="tab-panel%s" id="panel-%s" role="tabpanel">'
        '  <div class="headline">'
        '    <div class="figure"><span class="figure-number">%d</span>'
        '         <span class="figure-caption">Registered</span></div>'
        '    <div class="meta"><p class="countdown">%s</p><p class="delta">%s</p></div>'
        '  </div>'
        '  <section class="block"><h3>By grade</h3>%s</section>'
        '  %s'
        '  <section class="block"><h3>Signups over time</h3>%s</section>'
        '</div>'
        % (" is-active" if is_first else "", escape(tab["slug"]),
           metrics.get("total", 0), _countdown_text(tab.get("event"), today),
           _delta_text(tab), _bar_chart(metrics.get("grades", [])),
           "".join(dimension_blocks), _timeline_chart(metrics.get("timeline", []))))


STYLE = """
:root{--maroon:%s;--maroon-light:%s;--gold:%s;--gold-dim:%s;--ground:%s;
--panel:%s;--edge:%s;--text:%s;--dim:%s}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
-webkit-font-smoothing:antialiased}
header{background:linear-gradient(135deg,var(--maroon),var(--maroon-light));
padding:22px 20px;border-bottom:3px solid var(--gold)}
header h1{margin:0;font-size:1.15rem;letter-spacing:.16em;text-transform:uppercase;
font-weight:800}
header p{margin:6px 0 0;color:rgba(255,255,255,.82);font-size:.8rem}
.wrap{max-width:960px;margin:0 auto;padding:0 16px 56px}
.tabs{display:flex;gap:8px;overflow-x:auto;padding:16px 0;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab-button{flex:0 0 auto;background:var(--panel);color:var(--dim);border:1px solid var(--edge);
border-radius:999px;padding:10px 18px;font-size:.82rem;font-weight:700;cursor:pointer;
letter-spacing:.04em;white-space:nowrap}
.tab-button.is-active{background:var(--maroon);color:#fff;border-color:var(--gold)}
.tab-panel{display:none}
.tab-panel.is-active{display:block}
.headline{display:flex;flex-wrap:wrap;align-items:flex-end;gap:20px;
background:var(--panel);border:1px solid var(--edge);border-radius:14px;padding:22px 24px}
.figure-number{font-size:3.6rem;font-weight:800;color:var(--gold);line-height:1;
letter-spacing:-.02em;display:block}
.figure-caption{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--dim)}
.meta{margin-left:auto;text-align:right}
.countdown{margin:0;font-size:.95rem;font-weight:700}
.delta{margin:4px 0 0;font-size:.82rem;color:var(--gold)}
.block{background:var(--panel);border:1px solid var(--edge);border-radius:14px;
padding:20px 24px;margin-top:16px}
.block h3{margin:0 0 16px;font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;
color:var(--dim);font-weight:700}
.bar-row{display:grid;grid-template-columns:minmax(96px,34%%) 1fr 42px;align-items:center;
gap:12px;margin-bottom:10px}
.bar-label{font-size:.86rem;color:var(--text)}
.bar-track{background:#000;border-radius:5px;height:14px;overflow:hidden}
.bar-fill{display:block;height:100%%;border-radius:5px;
background:linear-gradient(90deg,var(--gold-dim),var(--gold))}
.bar-value{font-size:.9rem;font-weight:700;text-align:right;color:var(--gold)}
.timeline{width:100%%;height:auto}
.axis{fill:var(--dim);font-size:11px}
.empty{color:var(--dim);font-size:.86rem;margin:0}
footer{color:var(--dim);font-size:.72rem;text-align:center;padding:8px 16px 32px}
@media(max-width:560px){
.figure-number{font-size:2.8rem}
.meta{margin-left:0;text-align:left;width:100%%}
.bar-row{grid-template-columns:minmax(76px,42%%) 1fr 34px}}
""" % (MAROON, MAROON_LIGHT, GOLD, GOLD_DIM, GROUND, PANEL, PANEL_EDGE, TEXT, TEXT_DIM)

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


def render_dashboard(tabs, generated_at, today):
    if tabs:
        buttons = "".join(
            '<button class="tab-button%s" data-slug="%s" role="tab" aria-selected="%s">%s</button>'
            % (" is-active" if i == 0 else "", escape(tab["slug"]),
               "true" if i == 0 else "false", escape(tab["name"]))
            for i, tab in enumerate(tabs))
        panels = "".join(_panel(tab, today, i == 0) for i, tab in enumerate(tabs))
        body = ('<nav class="tabs" role="tablist">%s</nav>%s' % (buttons, panels))
    else:
        body = '<div class="block"><p class="empty">No active registrations.</p></div>'

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        "<title>LSGBA Registrations</title><style>%s</style></head><body>"
        "<header><h1>LSGBA Registrations</h1><p>Updated %s</p></header>"
        '<div class="wrap">%s</div>'
        "<footer>Aggregate counts only. Rebuilt on demand from SportsEngine.</footer>"
        "<script>%s</script></body></html>\n"
        % (STYLE, escape(generated_at), body, SCRIPT))
