"""Detect what football fans are talking about right now from public news RSS feeds,
and turn it into ranked content ideas."""
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from email.utils import parsedate_to_datetime

from . import config
from .net import FetchError, fetch
from .text import find_entities, strip_accents

TAG_RE = re.compile(r"<[^>]+>")
CAPS_RE = re.compile(r"\b([A-Z][a-zà-ÿ'’-]+(?:\s+(?:de|van|di|da|dos|del|le|la)?\s*[A-Z][a-zà-ÿ'’-]+){0,2})\b")
CAPS_STOP = set("""The A An And But Or For With From After Before Premier League Champions Europa Cup World
Football Sport Sports BBC Sky ESPN Guardian Live Report Watch Video Analysis How Why What Who When Where Which
This That These Those Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May
June July August September October November December England Spain Italy Germany France Portugal He She They It
We You I His Her Their Our Your Says Said New First Last Big Top Best Player Manager Club Team Fans Game Match
Week Weekend Year Season Transfer News Getty Images Reuters Twitter Instagram Why How There Here""".split())


@dataclass
class Headline:
    title: str
    link: str
    published: float
    source: str


@dataclass
class Trend:
    name: str
    kind: str
    score: float
    mentions: int
    headlines: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["headlines"] = [asdict(h) if not isinstance(h, dict) else h for h in self.headlines]
        return d


def _parse_date(text):
    try:
        return parsedate_to_datetime(text).timestamp()
    except (TypeError, ValueError, IndexError):
        return time.time()


def parse_feed(xml_text, source=""):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = TAG_RE.sub(" ", item.findtext("description") or "").strip()
        items.append((Headline(title, (item.findtext("link") or "").strip(),
                               _parse_date(item.findtext("pubDate")), source), f"{title}. {desc}"))
    return items


def collect(feeds=None, errors=None):
    feeds = feeds or config.keywords().get("feeds", [])
    items = []
    for url in feeds:
        try:
            xml_text = fetch(url, ttl=1800)
        except FetchError as e:
            if errors is not None:
                errors.append(str(e))
            continue
        items += parse_feed(xml_text, source=re.sub(r"^https?://(www\.)?", "", url).split("/")[0])
    return items


def detect(items=None, half_life_hours=24, now=None, errors=None):
    """Rank entities by recency-weighted mentions. Also surfaces 'emerging' capitalised names
    that aren't in entities.json yet (new signings, breakout players)."""
    if items is None:
        items = collect(errors=errors)
    now = now or time.time()
    scores, mentions, heads, kinds = defaultdict(float), Counter(), defaultdict(list), {}
    unknown = Counter()
    known_words = set()
    for kind in ("clubs", "players", "managers"):
        for rec in config.entities().get(kind, []):
            for alias in [rec["name"], *rec.get("aliases", [])]:
                known_words.update(strip_accents(alias).split())

    for head, text in items:
        age_h = max(0.0, (now - head.published) / 3600)
        weight = 0.5 ** (age_h / half_life_hours)
        in_title = {n for n, _, _ in find_entities(head.title)}
        for name, kind, _ in find_entities(text):
            w = weight * (2.0 if name in in_title else 1.0)
            scores[name] += w
            mentions[name] += 1
            kinds[name] = kind
            if len(heads[name]) < 3:
                heads[name].append(head)
        for cand in CAPS_RE.findall(head.title):
            parts = strip_accents(cand).split()
            if any(p in CAPS_STOP for p in parts) or all(p in known_words for p in parts):
                continue
            if len(parts) >= 2 or len(cand) > 5:
                unknown[cand] += 1
                if len(heads[cand]) < 3:
                    heads[cand].append(head)
                scores[cand] += weight * 0.6

    trends = [Trend(n, kinds.get(n, "emerging"), round(s, 2), mentions.get(n, unknown.get(n, 0)), heads[n])
              for n, s in scores.items() if n in kinds or unknown[n] >= 2]
    trends.sort(key=lambda t: -t.score)
    return trends


def weights(trends, top=20):
    """{name: 0..1} boost map for keyword scoring."""
    top_trends = trends[:top]
    if not top_trends:
        return {}
    best = top_trends[0].score or 1
    return {t.name: round(t.score / best, 3) for t in top_trends}


OFF_PITCH = ["guilty", "charge", "charges", "contract", "contracts", "funding", "court", "ban", "fined", "takeover",
             "owner", "ownership", "finances", "ffp", "psr", "profit", "investigation", "appeal"]
SACKED = ["sack", "sacks", "sacked", "leaves", "departs", "fired", "appoint", "appoints", "appointed", "new boss", "new manager"]

IDEA_TEMPLATES = {
    "club": [("breakdown", "How {name} set up in their last game: tactical analysis"),
             ("debate", "{name}'s biggest tactical problem right now"),
             ("player", "The most important player in {name}'s system (and why)")],
    "player": [("player", "Why {name} is so hard to stop: role explained"),
               ("debate", "Is {name} overrated or underrated? The tactical case")],
    "manager": [("breakdown", "{name}'s system explained in 60 seconds"),
                ("debate", "Has {name} figured it out? Tactical verdict")],
    "competition": [("breakdown", "5 tactical trends from this week's {name}")],
    "emerging": [("player", "Who is {name}? Tactical profile in 60 seconds")],
}


def _angle(t, i):
    """Pick an angle that fits the news: sackings → manager profile, off-pitch → on-pitch verdict."""
    headline = t.headlines[0].title if t.headlines else ""
    words = set(re.findall(r"[a-z]+", headline.lower()))
    if t.kind == "club" and words & set(SACKED):
        return "breakdown", f"What {t.name} need from their next manager: tactical profile"
    if t.kind == "club" and words & set(OFF_PITCH):
        return "debate", f"Forget the headlines: is {t.name}'s football actually good right now?"
    options = IDEA_TEMPLATES.get(t.kind, [])
    if not options:
        return None
    pillar, tmpl = options[i % len(options)]
    return pillar, tmpl.format(name=t.name)


def ideas(trends, limit=10):
    out = []
    for i, t in enumerate(trends):
        angle = _angle(t, i)
        if not angle:
            continue
        out.append({"pillar": angle[0], "idea": angle[1], "entity": t.name, "trend_score": t.score,
                    "why": t.headlines[0].title if t.headlines else ""})
        if len(out) >= limit:
            break
    return out
