"""`btf`: command-line entry point for the Beyond The Formation SEO engine."""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import (analytics, calendar_plan, captions, fixtures, hashtags, keywords, profile, report, scorer,
               trends)


def _print_table(rows, cols, limit=None):
    rows = rows[:limit] if limit else rows
    if not rows:
        print("(no data)")
        return
    widths = []
    for key, label, w in cols:
        widths.append(min(w, max(len(label), *(len(_cell(r.get(key), key)) for r in rows))))
    print("  ".join(label.ljust(w) for (_, label, _), w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(_cell(r.get(k), k)[:w].ljust(w) for (k, _, _), w in zip(cols, widths)))


PERCENT_KEYS = {"you", "target", "value"}


def _cell(v, key=""):
    if isinstance(v, float) and (key.endswith("_rate") or key in PERCENT_KEYS):
        return f"{v * 100:.2f}%"
    if isinstance(v, (list, tuple)):
        return ", ".join(map(str, v))
    return str(v if v is not None else "")


def _dump(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ------------------------------------------------------------------ commands

def cmd_caption(a):
    brief = captions.Brief(a.pillar, a.hook or "", a.team or "", a.opponent or "", a.player or "",
                           a.competition or "", a.topic or "", a.point, a.notes or "")
    if a.ai:
        from . import ai
        try:
            pkg = ai.build(brief, model=a.model, effort=a.effort)
        except ai.AIUnavailable as e:
            print(f"[AI unavailable: {e}. Falling back to templates]\n", file=sys.stderr)
            pkg = captions.build(brief)
    else:
        pkg = captions.build(brief)
    _dump(pkg.to_dict()) if a.json else print(pkg.render())


def cmd_score(a):
    text = Path(a.file).read_text(encoding="utf-8") if a.file else a.caption if a.caption else sys.stdin.read()
    r = scorer.score(text, a.alt, a.screen)
    if a.json:
        _dump(r.to_dict())
    else:
        for c in r.checks:
            print(f"{'✅' if c.ok else '❌'} [{c.points:>4g}/{c.max_points:g}] {c.message}")
        print(f"\nSEO score: {r.score}/100 (grade {r.grade}). {'Ready to post' if r.score >= 80 else 'Fix the ❌ items first'}")
    return 0 if r.score >= 80 else 1


def cmd_hashtags(a):
    tags = hashtags.select(a.pillar, a.text or "", a.team, a.player, a.competition)
    print(" ".join(tags))
    for p in hashtags.validate(tags):
        print("⚠", p)


def _trend_weights(offline, errors):
    if offline:
        return {}, []
    t = trends.detect(errors=errors)
    return trends.weights(t), t


def cmd_keywords(a):
    errors = []
    weights, _ = _trend_weights(a.no_trends, errors)
    ks = keywords.research(a.seeds, deep=a.deep, trending=weights, errors=errors)
    if a.json:
        _dump([k.to_dict() for k in ks[: a.limit]])
    else:
        _print_table([k.to_dict() for k in ks], [("score", "score", 6), ("phrase", "phrase", 48), ("intent", "intent", 9),
                                                  ("pillar", "pillar", 9), ("sources", "seen on", 15)], a.limit)
    _warn(errors)


def cmd_trends(a):
    errors = []
    t = trends.detect(errors=errors)
    ideas = trends.ideas(t, a.limit)
    if a.json:
        _dump({"trends": [x.to_dict() for x in t[: a.limit]], "ideas": ideas})
    else:
        print("TRENDING NOW")
        _print_table([{**x.to_dict(), "latest": x.headlines[0].title if x.headlines else ""} for x in t],
                     [("score", "heat", 6), ("name", "name", 22), ("kind", "type", 11), ("mentions", "mentions", 8),
                      ("latest", "latest headline", 70)], a.limit)
        print("\nPOST THESE NEXT")
        _print_table(ideas, [("pillar", "pillar", 9), ("idea", "idea", 70)])
    _warn(errors)


def cmd_calendar(a):
    start = dt.date.fromisoformat(a.start) if a.start else dt.date.today()
    fx = []
    if a.fixtures:
        fx = fixtures.load_csv(a.fixtures)
    elif a.football_data:
        fx = fixtures.from_api(start, days=a.weeks * 7)
    errors = []
    ideas = [] if a.no_trends else trends.ideas(trends.detect(errors=errors), 30)
    slots = calendar_plan.build(start, a.weeks, fx, ideas, a.time)
    if a.out:
        out = Path(a.out)
        out.write_text(calendar_plan.to_ics(slots) if out.suffix == ".ics" else calendar_plan.to_csv(slots), encoding="utf-8")
        print(f"Wrote {len(slots)} slots → {out}")
    _print_table([s.to_dict() for s in slots], [("date", "date", 10), ("weekday", "day", 3), ("format", "format", 8),
                                                 ("pillar", "pillar", 9), ("topic", "topic", 60), ("reason", "why", 40)])
    _warn(errors)


def _load_posts(a):
    if a.csv:
        return analytics.load_csv(a.csv)
    if a.instagram:
        from .instagram_api import InstagramAPI
        return InstagramAPI().posts(a.limit)
    raise SystemExit("Give --csv FILE (Meta Business Suite export) or --instagram (needs IG_ACCESS_TOKEN)")


def cmd_analytics(a):
    r = analytics.analyze(_load_posts(a))
    if a.json:
        return _dump(r)
    print(f"{r['posts']} posts · {r['period'][0]} → {r['period'][1]} · avg reach {r['avg_reach']:,}\n")
    _print_table([{"kpi": k, "you": v["value"], "target": v["target"], "ok": "✅" if v["ok"] else "❌"} for k, v in r["kpis"].items()],
                 [("kpi", "KPI", 16), ("you", "you", 8), ("target", "target", 8), ("ok", "", 2)])
    print("\nBY PILLAR")
    _print_table(r["by_pillar"], [("group", "pillar", 10), ("posts", "posts", 5), ("avg_reach", "avg reach", 9),
                                  ("send_rate", "sends", 7), ("save_rate", "saves", 7), ("index", "index", 5)])
    print("\nTOP POSTS")
    _print_table(r["top"], [("date", "date", 10), ("index", "index", 5), ("reach", "reach", 7), ("seo_score", "seo", 3),
                            ("first_line", "first line", 70)])
    print("\nWHAT TO DO NEXT")
    for rec in r["recommendations"]:
        print(" •", rec.replace("**", ""))


def cmd_profile(a):
    r = profile.audit(a.handle, a.name, a.bio.replace("\\n", "\n") if a.bio else "", a.link)
    if a.json:
        return _dump(r)
    print(f"Profile score: {r['score']}/100\n")
    for c in r["checks"]:
        print(f"{'✅' if c['ok'] else '❌'} {c['area']:<7} {c['message']}")
    print("\nFIXES")
    for s in r["suggestions"]:
        print(s, "\n")


def cmd_report(a):
    errors, ctx = [], {}
    ctx["profile"] = profile.audit(a.handle, a.name, a.bio.replace("\\n", "\n") if a.bio else "", a.link)
    if not a.offline:
        t = trends.detect(errors=errors)
        ctx["trends"] = [x.to_dict() for x in t[:20]]
        ctx["ideas"] = trends.ideas(t, 12)
        ctx["keywords"] = [k.to_dict() for k in keywords.research(a.seeds, trending=trends.weights(t), errors=errors)[:40]]
        idea_list = ctx["ideas"]
    else:
        idea_list = []
    start = dt.date.today()
    fx = fixtures.load_csv(a.fixtures) if a.fixtures else []
    ctx["calendar"] = [s.to_dict() for s in calendar_plan.build(start, 2, fx, idea_list)]
    if a.csv or a.instagram:
        ctx["analytics"] = analytics.analyze(_load_posts(a))
    ctx["sample"] = captions.build(captions.Brief("breakdown", team="Arsenal", opponent="Chelsea",
                                                  competition="Premier League", topic="high press")).render()
    ctx["errors"] = errors[:10]
    Path(a.out).write_text(report.build(**ctx), encoding="utf-8")
    print(f"Report written → {a.out}")


def cmd_serve(a):
    from .web import serve
    serve(a.host, a.port)


def _warn(errors):
    if errors:
        print(f"\n⚠ {len(errors)} source(s) failed, e.g. {errors[0]}", file=sys.stderr)


# ------------------------------------------------------------------ parser

def build_parser():
    p = argparse.ArgumentParser(prog="btf", description="Beyond The Formation: Instagram SEO engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("caption", help="Generate a full post package (hooks, caption, hashtags, alt text)")
    c.add_argument("--pillar", choices=captions.PILLARS, required=True)
    for f in ("hook", "team", "opponent", "player", "competition", "topic", "notes"):
        c.add_argument(f"--{f}")
    c.add_argument("--point", action="append", default=[], help="Key point (repeat up to 3x)")
    c.add_argument("--ai", action="store_true", help="Write with Claude (needs anthropic SDK + API key)")
    c.add_argument("--model", help="Claude model id (default claude-opus-5-5)")
    c.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_caption)

    s = sub.add_parser("score", help="Score a caption 0–100 (exit code 0 if ≥80)")
    s.add_argument("caption", nargs="?")
    s.add_argument("--file")
    s.add_argument("--alt", help="Alt text to score too")
    s.add_argument("--screen", help="On-screen hook text to score too")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_score)

    h = sub.add_parser("hashtags", help="Pick the best 5 hashtags")
    h.add_argument("--pillar", choices=captions.PILLARS, default="breakdown")
    for f in ("text", "team", "player", "competition"):
        h.add_argument(f"--{f}")
    h.set_defaults(fn=cmd_hashtags)

    k = sub.add_parser("keywords", help="Keyword research from Google + YouTube autocomplete")
    k.add_argument("seeds", nargs="+")
    k.add_argument("--deep", action="store_true", help="a–z expansion (more requests)")
    k.add_argument("--no-trends", action="store_true", help="Don't boost by trending entities")
    k.add_argument("--limit", type=int, default=40)
    k.add_argument("--json", action="store_true")
    k.set_defaults(fn=cmd_keywords)

    t = sub.add_parser("trends", help="What's hot in football news right now + content ideas")
    t.add_argument("--limit", type=int, default=15)
    t.add_argument("--json", action="store_true")
    t.set_defaults(fn=cmd_trends)

    cal = sub.add_parser("calendar", help="Build a posting calendar (CSV/ICS)")
    cal.add_argument("--start", help="YYYY-MM-DD (default today)")
    cal.add_argument("--weeks", type=int, default=2)
    cal.add_argument("--time", default="19:00", help="Default post time HH:MM")
    cal.add_argument("--fixtures", help="Fixtures CSV: date,home,away,competition")
    cal.add_argument("--football-data", action="store_true", help="Pull fixtures from football-data.org")
    cal.add_argument("--no-trends", action="store_true")
    cal.add_argument("--out", help="Write .csv or .ics")
    cal.set_defaults(fn=cmd_calendar)

    an = sub.add_parser("analytics", help="Analyse post performance and get recommendations")
    an.add_argument("--csv", help="Insights CSV export")
    an.add_argument("--instagram", action="store_true", help="Pull live from the Instagram API")
    an.add_argument("--limit", type=int, default=50)
    an.add_argument("--json", action="store_true")
    an.set_defaults(fn=cmd_analytics)

    pr = sub.add_parser("profile", help="Audit handle, name field, bio and link")
    pr.add_argument("--handle", default="")
    pr.add_argument("--name", default="")
    pr.add_argument("--bio", default="", help=r"Use \n for line breaks")
    pr.add_argument("--link", default="")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(fn=cmd_profile)

    r = sub.add_parser("report", help="Full HTML report: profile, trends, keywords, calendar, analytics")
    r.add_argument("--out", default="btf-report.html")
    r.add_argument("--seeds", nargs="+", default=["football tactics", "formation explained", "tactical analysis"])
    r.add_argument("--csv")
    r.add_argument("--instagram", action="store_true")
    r.add_argument("--limit", type=int, default=50)
    r.add_argument("--fixtures")
    r.add_argument("--offline", action="store_true", help="Skip network sources")
    r.add_argument("--handle", default="")
    r.add_argument("--name", default="")
    r.add_argument("--bio", default="")
    r.add_argument("--link", default="")
    r.set_defaults(fn=cmd_report)

    sv = sub.add_parser("serve", help="Run the local web dashboard")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8787)
    sv.set_defaults(fn=cmd_serve)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        rc = args.fn(args)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
