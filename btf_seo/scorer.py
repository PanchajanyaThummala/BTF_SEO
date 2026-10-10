"""Score a post's search/discovery readiness (0–100) with actionable fixes."""
import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from . import config, hashtags
from .text import (HASHTAG_RE, contains_phrase, count_emoji, extract_hashtags, find_entities,
                   first_line, normalize, words)

STOPWORDS = set("""a an the and or but if of to in on at by for with from this that these those is are was were be
been it its as so than then there their they them you your we our i me my he she his her who what why how when where
which not no yes just only very can will would should could do does did have has had more most less into out up down
over under again about after before all any each few other some such own same too""".split())


@dataclass
class Check:
    name: str
    ok: bool
    points: float
    max_points: float
    message: str


@dataclass
class ScoreReport:
    score: int
    grade: str
    checks: list = field(default_factory=list)

    @property
    def fixes(self):
        return [c.message for c in self.checks if not c.ok]

    def to_dict(self):
        return {"score": self.score, "grade": self.grade, "checks": [asdict(c) for c in self.checks], "fixes": self.fixes}


def _has_keyword(text):
    kw = config.keywords()
    norm = normalize(text)
    terms = kw["core_keywords"] + kw["tactical_terms"]
    return any(contains_phrase(norm, t) for t in terms)


def _grade(score):
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 65 else "D" if score >= 50 else "F"


def score(caption, alt_text=None, on_screen_text=None):
    """Score a caption. ``alt_text`` and ``on_screen_text`` are optional; when given they are scored too."""
    kw = config.keywords()
    checks = []

    def add(name, ok, max_points, ok_msg, fix_msg, partial=None):
        pts = max_points if ok else (partial or 0)
        checks.append(Check(name, ok, pts, max_points, ok_msg if ok else fix_msg))

    line1 = first_line(caption)
    body_no_tags = HASHTAG_RE.sub(" ", caption)
    tags = extract_hashtags(caption)
    lower = caption.lower()

    add("first_line_keyword", _has_keyword(line1), 20, "First line contains a tactics search keyword",
        "Put a search keyword in the FIRST line (e.g. 'tactical analysis', 'formation', 'high press', '4-3-3')")
    ents = [n for n, k, _ in find_entities(line1)]
    add("first_line_entity", bool(ents), 10,
        f"First line names who it's about ({', '.join(ents[:3])})" if ents else "",
        "Name a club, player, manager or competition in the first line; people search names")
    add("first_line_length", 0 < len(line1) <= 125, 8, "First line fits before '… more'",
        f"First line is {len(line1)} chars; keep it ≤125 so it isn't cut off")
    add("opens_with_words", bool(line1) and line1[0] not in "#@", 4, "Caption opens with words, not tags",
        "Don't start the caption with a hashtag or @mention")

    add("hashtag_count", 0 < len(tags) <= hashtags.MAX_HASHTAGS, 10,
        f"{len(tags)} hashtags (≤{hashtags.MAX_HASHTAGS})",
        f"Use 1–{hashtags.MAX_HASHTAGS} hashtags (found {len(tags)})")
    add("brand_hashtag", kw["brand"]["hashtag"] in tags, 5, "Brand hashtag present",
        f"Add {kw['brand']['hashtag']} so all your posts collect under one tag")
    bad = [t for t in tags if t in kw["avoid_hashtags"]]
    add("no_generic_hashtags", not bad, 5, "No generic/dead hashtags", f"Remove generic tags: {' '.join(bad)}")

    has_send = any(p in lower for p in kw["cta_send"])
    has_other = any(p in lower for p in kw["cta_other"])
    add("cta", has_send, 10, "Has a 'send/share/tag' CTA (sends are the strongest reach signal)",
        "Add a send CTA, e.g. 'Send this to the mate who…'" + ("" if has_other else " (no CTA at all right now)"),
        partial=5 if has_other else 0)

    n_words = len(words(body_no_tags))
    add("length", 20 <= n_words <= 300, 8, f"Length OK ({n_words} words)",
        f"Caption body has {n_words} words; aim for 20–300 so search has context")

    counts = Counter(w for w in words(body_no_tags) if len(w) > 3 and w not in STOPWORDS)
    stuffed = [w for w, c in counts.items() if c > 4]
    add("no_stuffing", not stuffed, 5, "No keyword stuffing",
        f"Words repeated too often (reads as spam): {', '.join(stuffed)}")
    emo = count_emoji(caption)
    add("emoji_balance", emo <= 12, 5, f"Emoji use balanced ({emo})", f"{emo} emoji; cut to ≤12 so it reads cleanly")

    placeholders = re.findall(r"\{[^}]*\}", caption)
    add("no_placeholders", not placeholders, 5, "No unfilled template placeholders",
        f"Fill in the placeholders before posting: {', '.join(placeholders[:3])}")
    if alt_text is not None:
        good_alt = len(alt_text.strip()) >= 30 and (_has_keyword(alt_text) or find_entities(alt_text))
        add("alt_text", good_alt, 10, "Alt text is descriptive and keyworded",
            "Write alt text (≥30 chars) describing the graphic with team/tactic keywords")
    if on_screen_text is not None:
        ok = _has_keyword(on_screen_text) or bool(find_entities(on_screen_text))
        add("on_screen_text", ok and len(on_screen_text) <= 70, 10, "On-screen hook is short and keyworded",
            "On-screen hook should be ≤70 chars and include a team/player/tactic keyword (Instagram reads it)")

    total = sum(c.max_points for c in checks)
    value = round(100 * sum(c.points for c in checks) / total)
    return ScoreReport(value, _grade(value), checks)
