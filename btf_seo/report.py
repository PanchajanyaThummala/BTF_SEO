"""One-page HTML SEO report (open in any browser, share with collaborators)."""
import datetime as dt
import html
import re

from . import config

CSS = """
:root{--bg:#f6f7f4;--card:#fff;--ink:#16201a;--muted:#5d6b62;--line:#dde3dc;--accent:#0f7a3d;--bad:#b3261e;--good:#0f7a3d}
@media (prefers-color-scheme:dark){:root{--bg:#0f1511;--card:#17201a;--ink:#e6efe8;--muted:#9db0a3;--line:#2a372e;--accent:#4cc27a;--bad:#ff8a80;--good:#4cc27a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:0 0 12px}
.sub{color:var(--muted);margin-bottom:24px}section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:16px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}.ok{color:var(--good)}.bad{color:var(--bad)}.pill{display:inline-block;padding:1px 8px;border-radius:99px;border:1px solid var(--line);font-size:12px;color:var(--muted)}
.big{font-size:40px;font-weight:700;color:var(--accent)}pre{white-space:pre-wrap;background:var(--bg);padding:12px;border-radius:8px;border:1px solid var(--line)}
ul{padding-left:20px}li{margin:4px 0}
"""


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _md(x):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _e(x))


def _table(rows, cols):
    if not rows:
        return "<p class='sub'>No data.</p>"
    head = "".join(f"<th>{_e(label)}</th>" for _, label in cols)
    body = "".join("<tr>" + "".join(f"<td>{_fmt(r.get(k), k)}</td>" for k, _ in cols) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _fmt(v, key=""):
    if isinstance(v, float) and (key.endswith("_rate") or key in ("value", "target")):
        return f"{v * 100:.2f}%"
    if isinstance(v, (list, tuple)):
        return _e(", ".join(map(str, v)))
    return _e(v)


def build(profile=None, trends=None, ideas=None, keywords=None, calendar=None, analytics=None, sample=None, errors=None):
    brand = config.keywords()["brand"]
    parts = [f"<main><h1>{_e(brand['name'])}: SEO Report</h1>",
             f"<div class='sub'>{_e(brand['handle'])} · generated {dt.datetime.now():%d %b %Y %H:%M}</div>"]

    if analytics:
        kp = analytics["kpis"]
        rows = [{"kpi": k.replace("_", " "), "value": v["value"], "target": v["target"],
                 "status": "✅" if v["ok"] else "❌"} for k, v in kp.items()]
        parts.append("<section><h2>Performance</h2>"
                     f"<p>{analytics['posts']} posts · {_e(analytics['period'][0])} → {_e(analytics['period'][1])} · avg reach {analytics['avg_reach']:,}</p>"
                     + _table(rows, [("kpi", "KPI"), ("value", "You"), ("target", "Target"), ("status", "")])
                     + "<h2 style='margin-top:18px'>What to do next</h2><ul>"
                     + "".join(f"<li>{_md(r)}</li>" for r in analytics["recommendations"]) + "</ul>"
                     + "<h2 style='margin-top:18px'>By pillar</h2>"
                     + _table(analytics["by_pillar"], [("group", "Pillar"), ("posts", "Posts"), ("avg_reach", "Avg reach"),
                                                       ("send_rate", "Sends/reach"), ("save_rate", "Saves/reach"), ("index", "Index")])
                     + "<h2 style='margin-top:18px'>Top posts</h2>"
                     + _table(analytics["top"], [("date", "Date"), ("first_line", "First line"), ("pillar", "Pillar"),
                                                 ("reach", "Reach"), ("send_rate", "Sends"), ("seo_score", "SEO"), ("index", "Index")])
                     + "</section>")

    if profile:
        rows = [{"area": c["area"], "status": "✅" if c["ok"] else "❌", "message": c["message"]} for c in profile["checks"]]
        parts.append(f"<section><h2>Profile audit</h2><div class='big'>{profile['score']}/100</div>"
                     + _table(rows, [("area", "Area"), ("status", ""), ("message", "Finding")])
                     + "<h2 style='margin-top:18px'>Fixes</h2>" + "".join(f"<pre>{_e(s)}</pre>" for s in profile["suggestions"])
                     + "</section>")

    if ideas:
        parts.append("<section><h2>Post these next (trending now)</h2>"
                     + _table(ideas, [("idea", "Idea"), ("pillar", "Pillar"), ("why", "Why it's hot")]) + "</section>")
    if trends:
        parts.append("<section><h2>Trending entities</h2>"
                     + _table([{"name": t["name"], "kind": t["kind"], "score": t["score"], "mentions": t["mentions"],
                                "headline": (t["headlines"][0]["title"] if t["headlines"] else "")} for t in trends[:15]],
                              [("name", "Name"), ("kind", "Type"), ("score", "Heat"), ("mentions", "Mentions"), ("headline", "Latest")])
                     + "</section>")
    if keywords:
        parts.append("<section><h2>Keyword opportunities</h2><p class='sub'>From Google + YouTube autocomplete. "
                     "Use the top phrases in first lines, on-screen text and voiceover.</p>"
                     + _table(keywords[:30], [("phrase", "Phrase"), ("score", "Score"), ("intent", "Intent"),
                                              ("pillar", "Pillar"), ("sources", "Seen on")]) + "</section>")
    if calendar:
        parts.append("<section><h2>Content calendar</h2>"
                     + _table(calendar, [("date", "Date"), ("weekday", "Day"), ("format", "Format"), ("pillar", "Pillar"),
                                         ("topic", "Topic"), ("reason", "Why")]) + "</section>")
    if sample:
        parts.append(f"<section><h2>Example post package</h2><pre>{_e(sample)}</pre></section>")
    if errors:
        parts.append("<section><h2>Data sources that failed</h2><ul>" + "".join(f"<li>{_e(e)}</li>" for e in errors) + "</ul></section>")
    parts.append("</main>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>BTF SEO Report</title><style>{CSS}</style></head><body>{''.join(parts)}</body></html>")
