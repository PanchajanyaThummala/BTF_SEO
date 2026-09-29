"""Text helpers shared by every module."""
import re
import unicodedata

from . import config

HASHTAG_RE = re.compile(r"#[\w\d_]+", re.UNICODE)
MENTION_RE = re.compile(r"@[\w.]+")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆↔-↪✅❌❗‼⁉〰〽㊗㊙⃣️]")


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def to_hashtag(text):
    """'Man City' -> '#mancity', 'Mbappé' -> '#mbappe'."""
    return "#" + re.sub(r"[^0-9a-z]", "", strip_accents(text).lower())


def extract_hashtags(caption):
    return [h.lower() for h in HASHTAG_RE.findall(caption)]


def first_line(caption):
    for line in caption.strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


def words(text):
    """Lower-cased word tokens; hyphens split words so 'full-back' == 'full back', and possessives
    are dropped so "Arsenal's" matches 'Arsenal'."""
    text = re.sub(r"['’]s\b", "", strip_accents(text).lower().replace("-", " "))
    return re.findall(r"[\w'’]+", text)


def count_emoji(text):
    return len(EMOJI_RE.findall(text))


def normalize(text):
    return " " + " ".join(words(text)) + " "


def contains_phrase(text_norm, phrase):
    """Whole-word phrase match on text already passed through ``normalize``."""
    return normalize(phrase) in text_norm


# ---------------------------------------------------------------- entities

def _entity_index():
    ents = config.entities()
    comps = config.keywords()["competitions"]
    index = []  # (alias_norm, canonical, kind, record)
    for kind in ("clubs", "players", "managers"):
        for rec in ents.get(kind, []):
            for alias in [rec["name"], *rec.get("aliases", [])]:
                index.append((normalize(alias), rec["name"], kind[:-1], rec))
    for comp, tag in comps.items():
        index.append((normalize(comp), comp, "competition", {"name": comp, "hashtag": tag}))
    # Longest aliases first so "Manchester City" wins over "City".
    index.sort(key=lambda t: -len(t[0]))
    return index


# Aliases that are ordinary English words: only count them when capitalised in the source.
AMBIGUOUS = {"city", "united", "reds", "blues", "villa", "rice", "slot", "kane", "palmer", "madrid", "milan",
             "inter", "pep", "spurs", "flick", "alonso", "rodri", "atletico"}


def find_entities(text):
    """Return canonical entity names mentioned in ``text``: [(name, kind, record)]."""
    norm = normalize(text)
    raw = strip_accents(text)
    found, seen, consumed = [], set(), norm
    for alias_norm, name, kind, rec in _entity_index():
        if alias_norm not in consumed:
            continue
        bare = alias_norm.strip()
        if bare in AMBIGUOUS and not re.search(r"\b" + re.escape(bare.title()) + r"\b", raw):
            continue
        consumed = consumed.replace(alias_norm, " ")
        if name not in seen:
            seen.add(name)
            found.append((name, kind, rec))
    return found


def entity_hashtag(rec):
    return rec.get("hashtag") or to_hashtag(rec["name"])
