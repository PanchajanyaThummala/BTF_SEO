"""Performance analytics: turn your post history into decisions.

Input: a CSV export (Meta Business Suite → Insights → Content → Export, or any CSV with similar
columns) or live data from the Instagram API (see instagram_api.py).
"""
import csv
import datetime as dt
import io
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from . import config, scorer
from .text import contains_phrase, extract_hashtags, first_line, normalize

TARGETS = {  # docs/08-analytics-kpis.md
    "send_rate": 0.01,
    "save_rate": 0.015,
    "follow_rate": 0.003,
    "engagement_rate": 0.05,
}

COLUMNS = {
    "id": ["post id", "id", "media id", "media_id"],
    "caption": ["description", "caption", "title", "text"],
    "timestamp": ["publish time", "timestamp", "date", "posted", "published", "created time"],
    "media_type": ["post type", "media type", "media_type", "type", "media_product_type"],
    "permalink": ["permalink", "link", "url"],
    "reach": ["reach", "accounts reached"],
    "views": ["views", "plays", "impressions"],
    "likes": ["likes", "like_count"],
    "comments": ["comments", "comments_count"],
    "shares": ["shares", "sends"],
    "saves": ["saves", "saved"],
    "follows": ["follows", "follows gained", "new follows"],
    "duration": ["duration (sec)", "duration", "length"],
}
DATE_FORMATS = ["%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


@dataclass
class Post:
    id: str
    caption: str = ""
    timestamp: dt.datetime = None
    media_type: str = ""
    permalink: str = ""
    reach: float = 0
    views: float = 0
    likes: float = 0
    comments: float = 0
    shares: float = 0
    saves: float = 0
    follows: float = 0
    duration: float = 0
    pillar: str = ""
    seo_score: int = 0
    metrics: dict = field(default_factory=dict)

    def rate(self, attr):
        return getattr(self, attr) / self.reach if self.reach else 0.0

    def compute(self):
        self.pillar = classify_pillar(self.caption)
        self.seo_score = scorer.score(self.caption).score if self.caption else 0
        self.metrics = {
            "send_rate": self.rate("shares"),
            "save_rate": self.rate("saves"),
            "like_rate": self.rate("likes"),
            "comment_rate": self.rate("comments"),
            "follow_rate": self.rate("follows"),
            "engagement_rate": (self.likes + self.comments + self.shares + self.saves) / self.reach if self.reach else 0.0,
            "hashtags": len(extract_hashtags(self.caption)),
        }
        return self

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat() if self.timestamp else None
        return d


def classify_pillar(caption):
    kw = config.keywords()
    norm = normalize(caption)
    head = normalize(first_line(caption))
    best, best_score = "breakdown", 0
    for name, p in kw["pillars"].items():
        s = sum(2 if contains_phrase(head, sig) else 1 if contains_phrase(norm, sig) else 0 for sig in p["signals"])
        if s > best_score:
            best, best_score = name, s
    return best


def media_kind(v):
    v = (v or "").upper()
    for key, kind in (("REEL", "REEL"), ("VIDEO", "REEL"), ("CAROUSEL", "CAROUSEL"), ("ALBUM", "CAROUSEL"),
                      ("IMAGE", "IMAGE"), ("PHOTO", "IMAGE"), ("STORY", "STORY")):
        if key in v:
            return kind
    return v


def _num(v):
    if v is None:
        return 0.0
    v = str(v).replace(",", "").replace("%", "").strip()
    try:
        return float(v) if v else 0.0
    except ValueError:
        return 0.0


def parse_time(v):
    if not v:
        return None
    v = str(v).strip()
    for fmt in DATE_FORMATS:
        try:
            t = dt.datetime.strptime(v, fmt)
            return t.replace(tzinfo=None) if t.tzinfo else t
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def load_csv(source):
    """``source`` is a path or CSV text."""
    if "\n" in source or "," in source and not source.lower().endswith(".csv"):
        text = source
    else:
        with open(source, encoding="utf-8-sig") as f:
            text = f.read()
    text = text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}
    colmap = {}
    for key, aliases in COLUMNS.items():
        for a in aliases:
            if a in headers:
                colmap[key] = headers[a]
                break
    if "reach" not in colmap and "views" not in colmap:
        raise ValueError(f"CSV needs a 'Reach' or 'Views' column. Found: {', '.join(reader.fieldnames or [])}")
    posts = []
    for i, row in enumerate(reader):
        g = lambda k: row.get(colmap[k]) if k in colmap else None  # noqa: E731
        p = Post(
            id=str(g("id") or i), caption=g("caption") or "", timestamp=parse_time(g("timestamp")),
            media_type=media_kind(g("media_type")), permalink=g("permalink") or "",
            reach=_num(g("reach")) or _num(g("views")), views=_num(g("views")), likes=_num(g("likes")),
            comments=_num(g("comments")), shares=_num(g("shares")), saves=_num(g("saves")),
            follows=_num(g("follows")), duration=_num(g("duration")),
        )
        posts.append(p.compute())
    return posts


def _median(values):
    values = [v for v in values if v]
    return statistics.median(values) if values else 0.0


def performance_index(posts):
    """Composite score per post relative to the account's own medians (1.0 = typical post)."""
    med = {k: _median([p.metrics[k] for p in posts]) for k in ("send_rate", "save_rate", "follow_rate")}
    med_reach = _median([p.reach for p in posts])
    out = {}
    for p in posts:
        parts = [(0.4, p.reach / med_reach if med_reach else 0)]
        for w, k in ((0.3, "send_rate"), (0.2, "save_rate"), (0.1, "follow_rate")):
            parts.append((w, p.metrics[k] / med[k] if med[k] else 0))
        out[p.id] = round(sum(w * v for w, v in parts), 2)
    return out


def _group(posts, keyfn, pidx):
    groups = defaultdict(list)
    for p in posts:
        k = keyfn(p)
        if k is not None:
            groups[k].append(p)
    rows = []
    for k, ps in groups.items():
        rows.append({
            "group": k, "posts": len(ps),
            "avg_reach": round(statistics.mean(p.reach for p in ps)),
            "send_rate": round(statistics.mean(p.metrics["send_rate"] for p in ps), 4),
            "save_rate": round(statistics.mean(p.metrics["save_rate"] for p in ps), 4),
            "follow_rate": round(statistics.mean(p.metrics["follow_rate"] for p in ps), 4),
            "index": round(statistics.mean(pidx[p.id] for p in ps), 2),
        })
    rows.sort(key=lambda r: -r["index"])
    return rows


def _hour_bucket(p):
    if not p.timestamp or (p.timestamp.hour == 0 and p.timestamp.minute == 0):
        return None
    h = p.timestamp.hour
    return f"{h - h % 3:02d}:00–{h - h % 3 + 3:02d}:00"


def _grade_bucket(p):
    return "SEO ≥80" if p.seo_score >= 80 else "SEO 50–79" if p.seo_score >= 50 else "SEO <50"


def analyze(posts):
    if not posts:
        raise ValueError("No posts to analyse")
    pidx = performance_index(posts)
    ranked = sorted(posts, key=lambda p: -pidx[p.id])
    totals = {k: round(statistics.mean(p.metrics[k] for p in posts), 4) for k in TARGETS}
    result = {
        "posts": len(posts),
        "period": [min((p.timestamp for p in posts if p.timestamp), default=None),
                   max((p.timestamp for p in posts if p.timestamp), default=None)],
        "kpis": {k: {"value": v, "target": TARGETS[k], "ok": v >= TARGETS[k]} for k, v in totals.items()},
        "avg_reach": round(statistics.mean(p.reach for p in posts)),
        "by_pillar": _group(posts, lambda p: p.pillar, pidx),
        "by_weekday": _group(posts, lambda p: p.timestamp.strftime("%A") if p.timestamp else None, pidx),
        "by_hour": _group(posts, _hour_bucket, pidx),
        "by_type": _group(posts, lambda p: p.media_type or None, pidx),
        "by_seo": _group(posts, _grade_bucket, pidx),
        "top": [_summary(p, pidx) for p in ranked[:5]],
        "bottom": [_summary(p, pidx) for p in ranked[-5:][::-1]] if len(ranked) > 5 else [],
    }
    result["period"] = [t.date().isoformat() if t else None for t in result["period"]]
    result["recommendations"] = recommendations(posts, result)
    return result


def _summary(p, pidx):
    return {"id": p.id, "first_line": first_line(p.caption)[:100], "pillar": p.pillar, "reach": int(p.reach),
            "send_rate": round(p.metrics["send_rate"], 4), "save_rate": round(p.metrics["save_rate"], 4),
            "seo_score": p.seo_score, "index": pidx[p.id], "permalink": p.permalink,
            "date": p.timestamp.date().isoformat() if p.timestamp else ""}


def recommendations(posts, r):
    recs = []
    pct = lambda x: f"{x * 100:.1f}%"  # noqa: E731
    pillars = [g for g in r["by_pillar"] if g["posts"] >= 2]
    if len(pillars) >= 2:
        best, worst = pillars[0], pillars[-1]
        recs.append(f"Your strongest pillar is **{best['group']}** (index {best['index']}, send rate {pct(best['send_rate'])}). "
                    f"Shift 1–2 posts/week from **{worst['group']}** (index {worst['index']}) to it.")
    days = [g for g in r["by_weekday"] if g["posts"] >= 2]
    if days:
        recs.append(f"Best posting day so far: **{days[0]['group']}**; weakest: {days[-1]['group']}. Put your best idea of the week on {days[0]['group']}.")
    hours = [g for g in r["by_hour"] if g["posts"] >= 2]
    if hours:
        recs.append(f"Best time window: **{hours[0]['group']}**.")
    seo = {g["group"]: g for g in r["by_seo"]}
    if "SEO ≥80" in seo and len(seo) > 1:
        lo = min((g for k, g in seo.items() if k != "SEO ≥80"), key=lambda g: g["index"])
        hi = seo["SEO ≥80"]
        if hi["avg_reach"] > lo["avg_reach"]:
            recs.append(f"Captions scoring ≥80 average **{hi['avg_reach']:,} reach** vs {lo['avg_reach']:,} for {lo['group']}. Score every caption before posting.")
    elif "SEO ≥80" not in seo:
        recs.append("None of your captions score ≥80 yet. Start every caption with a team/player + tactic keyword and end with a send CTA.")
    kp = r["kpis"]
    if not kp["send_rate"]["ok"]:
        recs.append(f"Send rate is {pct(kp['send_rate']['value'])} (target {pct(TARGETS['send_rate'])}). End every Reel with 'send this to the mate who…' and post more debate/hot-take content.")
    if not kp["save_rate"]["ok"]:
        recs.append(f"Save rate is {pct(kp['save_rate']['value'])} (target {pct(TARGETS['save_rate'])}). Make more cheat-sheet carousels and 'formation explained' posts people keep.")
    if not kp["follow_rate"]["ok"]:
        recs.append("Few viewers follow after watching. Add a series name ('Formation of the Week') and say 'follow for part 2'.")
    over = sum(1 for p in posts if p.metrics["hashtags"] > 5)
    if over:
        recs.append(f"{over} posts use more than 5 hashtags. Instagram caps it at 5; trim to the 5-slot formula.")
    types = {g["group"]: g for g in r["by_type"]}
    reel, caro = types.get("REEL"), types.get("CAROUSEL")
    if reel and caro:
        better, other = (reel, caro) if reel["index"] >= caro["index"] else (caro, reel)
        recs.append(f"{better['group'].title()}s outperform {other['group'].lower()}s (index {better['index']} vs {other['index']}). "
                    f"Keep the 5 Reels + 2 carousels mix but use {better['group'].lower()}s for your biggest topics.")
    if r["top"]:
        t = r["top"][0]
        recs.append(f"Make a part 2 of your top post within 7 days: \"{t['first_line']}\".")
    return recs
