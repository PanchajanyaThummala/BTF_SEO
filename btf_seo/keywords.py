"""Keyword research from real search demand (Google + YouTube autocomplete).

Instagram has no public search API, but autocomplete shows what people actually type,
and YouTube autocomplete is the closest public signal to short-video search intent.
"""
import string
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from . import config
from .net import FetchError, fetch_json
from .text import contains_phrase, find_entities, normalize

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
SOURCES = {"google": {}, "youtube": {"ds": "yt"}}
MODIFIERS = ["explained", "tactics", "formation", "analysis", "vs", "press", "system", "role",
             "how", "why", "what is", "best"]

INTENTS = [
    ("gaming", ["fc 2", "fc2", "fifa", "fm2", "fm 2", "football manager", "efootball", "ea fc", "pes", "custom tactics", "ultimate team"]),
    ("explainer", ["explained", "explanation", "for beginners", "guide", "meaning", "what is", "tutorial", "basics"]),
    ("versus", [" vs ", " versus ", " v "]),
    ("analysis", ["analysis", "breakdown", "tactics", "tactical", "formation", "system", "press", "shape"]),
    ("news", ["news", "today", "live", "score", "result", "highlights", "injury", "transfer", "lineup", "line up"]),
]

QUESTION_WORDS = {"how", "why", "what", "who", "which", "when", "is", "does", "can", "should", "are"}


@dataclass
class Keyword:
    phrase: str
    score: float
    intent: str
    hits: int
    sources: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    pillar: str = ""

    def to_dict(self):
        return asdict(self)


def autocomplete(query, source="google", lang="en"):
    params = {"client": "firefox", "hl": lang, "q": query, **SOURCES[source]}
    data = fetch_json(SUGGEST_URL, params=params, ttl=6 * 3600)
    return [s for s in (data[1] if len(data) > 1 else []) if isinstance(s, str)]


def classify_intent(phrase):
    p = f" {phrase.lower()} "
    gaming = INTENTS[0]
    if any(m in p for m in gaming[1]):
        return "gaming"
    if p.split()[0] in QUESTION_WORDS:
        return "question"
    for intent, markers in INTENTS[1:]:
        if any(m in p for m in markers):
            return intent
    return "general"


def suggest_pillar(phrase, intent):
    if intent == "gaming":
        return "explained"
    if intent == "versus":
        return "breakdown"
    kinds = {k for _, k, _ in find_entities(phrase)}
    p = phrase.lower()
    if "player" in kinds and ("role" in p or "why" in p or "how" in p or intent == "general"):
        return "player"
    if intent in ("explainer", "question") and not kinds - {"competition"}:
        return "explained"
    if any(w in p for w in ("best", "worst", "overrated", "greatest", "better")):
        return "debate"
    if not kinds - {"competition"}:
        return "explained"
    return "breakdown"


FOOTBALL_CONTEXT = ["football", "soccer", "tactic", "tactics", "tactical", "formation", "full back", "fullback",
                    "wing back", "midfield", "midfielder", "striker", "winger", "defender", "centre back", "center back",
                    "goalkeeper", "pressing", "press", "false 9", "number 6", "number 8", "number 10", "playmaker",
                    "xg", "coach", "manager", "fc", "league", "fm", "pep", "4 3 3", "4 2 3 1", "3 5 2", "4 4 2", "3 4 3"]


def _relevance(phrase, seed):
    """0..1: is this about football tactics, and how much of the seed does it keep?"""
    kw = config.keywords()
    norm = normalize(phrase)
    tactical = any(contains_phrase(norm, t) for t in kw["core_keywords"] + kw["tactical_terms"])
    football = tactical and any(contains_phrase(norm, t) for t in FOOTBALL_CONTEXT) or bool(find_entities(phrase))
    context = 1.0 if football else 0.5 if tactical else 0.25
    seed_words = {w for w in normalize(seed).split() if len(w) > 2}
    coverage = len(seed_words & set(norm.split())) / len(seed_words) if seed_words else 1.0
    return context * (0.4 + 0.6 * coverage)


def research(seeds, sources=("google", "youtube"), deep=False, trending=None, errors=None):
    """Expand seeds via autocomplete and rank the phrases.

    Score = demand proxy (how often/high it shows up) × tactics relevance × long-tail bonus × trend boost.
    ``trending`` is an optional {entity_name: weight} map from ``trends.detect``.
    """
    trending = trending or {}
    queries = {}
    for seed in seeds:
        variants = [seed] + [f"{seed} {m}" for m in MODIFIERS] + [f"{m} {seed}" for m in ("how", "why", "what is")]
        if deep:
            variants += [f"{seed} {c}" for c in string.ascii_lowercase]
        for q in variants:
            queries.setdefault(q, seed)

    stats = defaultdict(lambda: {"hits": 0, "rank": 0.0, "sources": set(), "seed": ""})
    for q, seed in queries.items():
        for src in sources:
            try:
                suggestions = autocomplete(q, src)
            except FetchError as e:
                if errors is not None:
                    errors.append(str(e))
                continue
            for pos, s in enumerate(suggestions):
                s = " ".join(s.lower().split())
                st = stats[s]
                st["hits"] += 1
                st["rank"] += 1.0 / (pos + 1)
                st["sources"].add(src)
                st["seed"] = st["seed"] or seed

    out = []
    for phrase, st in stats.items():
        n_words = len(phrase.split())
        long_tail = 1.2 if 3 <= n_words <= 7 else 1.0 if n_words == 2 else 0.7
        multi_source = 1.25 if len(st["sources"]) > 1 else 1.0
        ents = [n for n, _, _ in find_entities(phrase)]
        trend = 1.0 + max([trending.get(e, 0) for e in ents] or [0])
        demand = st["hits"] + st["rank"]
        score = round(demand * _relevance(phrase, st["seed"]) * long_tail * multi_source * trend, 2)
        intent = classify_intent(phrase)
        out.append(Keyword(phrase, score, intent, st["hits"], sorted(st["sources"]), ents, suggest_pillar(phrase, intent)))
    out.sort(key=lambda k: -k.score)
    return out


def caption_keywords(keywords, limit=10):
    """Best phrases to weave into first lines / on-screen text (excludes pure news/gaming)."""
    return [k for k in keywords if k.intent not in ("news",)][:limit]
