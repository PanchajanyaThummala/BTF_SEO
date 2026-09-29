"""Content calendar: weekly pillar rhythm + big matches + trending topics, exportable to CSV/ICS."""
import csv
import datetime as dt
import io
import uuid
from dataclasses import asdict, dataclass

# Weekday rhythm (0 = Monday) from docs/06-posting-calendar.md
WEEK = [
    ("reel", "breakdown", "Weekend's biggest tactical story", "Poll: best tactical performance of the weekend?"),
    ("carousel", "breakdown", "5 tactical takeaways from the weekend", "Share poll results + requests box"),
    ("reel", "breakdown", "Midweek European match analysis", "Live reactions"),
    ("reel", "explained", "Formation / concept explained", "Quiz sticker"),
    ("reel", "player", "Weekend preview: how {team} will set up", "Predictions slider"),
    ("reel", "debate", "Hot take or quiz", "Live match reactions"),
    ("carousel", "breakdown", "Big-match breakdown", "Week recap + tease next week"),
]
EVERGREEN = ["4-3-3 vs 4-2-3-1 explained", "What is an inverted full-back?", "The false 9 explained",
             "Gegenpressing in 60 seconds", "How a low block works", "Rest defence explained",
             "Why back threes are back", "Half-spaces explained", "The box midfield explained",
             "Man-marking vs zonal marking"]


@dataclass
class Slot:
    date: dt.date
    time: str
    format: str
    pillar: str
    topic: str
    stories: str
    reason: str = ""

    def to_dict(self):
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["weekday"] = self.date.strftime("%a")
        return d


def build(start, weeks=2, fixtures=None, trend_ideas=None, post_time="19:00"):
    """``fixtures``: list of fixtures.Fixture. ``trend_ideas``: output of trends.ideas()."""
    fixtures = sorted(fixtures or [], key=lambda f: f.date)
    ideas = list(trend_ideas or [])
    evergreen = list(EVERGREEN)
    slots = []
    for day in range(weeks * 7):
        date = start + dt.timedelta(days=day)
        fmt, pillar, topic, stories = WEEK[date.weekday()]
        reason = "Weekly rhythm"
        # Big match yesterday or today (evening post) → post-match breakdown wins the slot.
        recent = [f for f in fixtures if f.big and (date - f.date).days in (0, 1)]
        upcoming = [f for f in fixtures if f.big and 1 <= (f.date - date).days <= 2]
        if recent:
            f = recent[0]
            fmt, pillar = "reel", "breakdown"
            topic = f"{f.title()} tactical breakdown{' (' + f.competition + ')' if f.competition else ''}"
            reason = "Post within 2–6h of full time: search demand peaks"
        elif pillar == "player" and upcoming:
            f = upcoming[0]
            topic = f"Preview: how {f.home} and {f.away} will set up"
            reason = f"Big match on {f.date:%a %d %b}"
        elif pillar == "explained" and evergreen:
            topic = evergreen.pop(0)
            reason = "Evergreen search traffic"
        elif ideas and pillar in ("breakdown", "debate", "player"):
            idea = next((i for i in ideas if i["pillar"] == pillar), ideas[0])
            ideas.remove(idea)
            topic, reason = idea["idea"], f"Trending: {idea['why'][:80]}" if idea.get("why") else "Trending"
        slots.append(Slot(date, post_time, fmt, pillar, topic.replace("{team}", "the big teams"), stories, reason))
    return slots


def to_csv(slots):
    buf = io.StringIO()
    fields = ["date", "weekday", "time", "format", "pillar", "topic", "stories", "reason"]
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for s in slots:
        w.writerow({k: v for k, v in s.to_dict().items() if k in fields})
    return buf.getvalue()


def _ics_escape(text):
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(slots, duration_minutes=30):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Beyond The Formation//SEO Engine//EN", "CALSCALE:GREGORIAN"]
    for s in slots:
        h, m = (int(x) for x in s.time.split(":"))
        start = dt.datetime.combine(s.date, dt.time(h, m))
        end = start + dt.timedelta(minutes=duration_minutes)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid5(uuid.NAMESPACE_URL, f'btf-{s.date}-{s.topic}')}",
            f"DTSTAMP:{now}",
            f"DTSTART:{start:%Y%m%dT%H%M%S}",
            f"DTEND:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{_ics_escape(f'[{s.format.upper()}] {s.topic}')}",
            f"DESCRIPTION:{_ics_escape(f'Pillar: {s.pillar}. Stories: {s.stories}. Why: {s.reason}')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
