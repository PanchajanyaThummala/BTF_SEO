"""Hashtag selection and validation. Instagram allows at most 5 hashtags per post."""
from . import config
from .text import entity_hashtag, extract_hashtags, find_entities, to_hashtag

MAX_HASHTAGS = 5


def select(pillar="breakdown", text="", team=None, player=None, competition=None, extra=None):
    """Pick the best ≤5 hashtags using the slot formula:
    niche core → pillar topic → entity (player/club) → competition → brand."""
    kw = config.keywords()
    pillars = kw["pillars"]
    if pillar not in pillars:
        raise ValueError(f"Unknown pillar {pillar!r}. Choose from: {', '.join(pillars)}")
    brand = kw["brand"]["hashtag"]

    entity_tags, comp_tags = [], []
    for name in (player, team):
        if name:
            hits = find_entities(name)
            entity_tags.append(entity_hashtag(hits[0][2]) if hits else to_hashtag(name))
    if competition:
        comp_tags.append(kw["competitions"].get(competition, to_hashtag(competition)))
    for name, kind, rec in find_entities(text):
        (comp_tags if kind == "competition" else entity_tags).append(entity_hashtag(rec))

    candidates = [kw["core_hashtags"][0], pillars[pillar]["topic_hashtag"]]
    candidates += entity_tags[:2] + comp_tags[:1] + list(extra or []) + [pillars[pillar]["extra_hashtag"]]
    candidates += kw["core_hashtags"][1:]

    out = []
    for tag in candidates:
        tag = tag.lower() if tag.startswith("#") else to_hashtag(tag)
        if tag not in out and tag != brand and tag not in kw["avoid_hashtags"]:
            out.append(tag)
    return out[: MAX_HASHTAGS - 1] + [brand]


def validate(tags_or_caption):
    """Return a list of problems with a hashtag set (empty list = fine)."""
    kw = config.keywords()
    tags = extract_hashtags(tags_or_caption) if isinstance(tags_or_caption, str) else [t.lower() for t in tags_or_caption]
    problems = []
    if len(tags) > MAX_HASHTAGS:
        problems.append(f"{len(tags)} hashtags; Instagram allows {MAX_HASHTAGS}")
    if not tags:
        problems.append("No hashtags")
    dupes = {t for t in tags if tags.count(t) > 1}
    if dupes:
        problems.append(f"Duplicate hashtags: {' '.join(sorted(dupes))}")
    bad = [t for t in tags if t in kw["avoid_hashtags"]]
    if bad:
        problems.append(f"Generic/low-value hashtags: {' '.join(bad)}")
    if kw["brand"]["hashtag"] not in tags:
        problems.append(f"Missing brand hashtag {kw['brand']['hashtag']}")
    long_tags = [t for t in tags if len(t) > 30]
    if long_tags:
        problems.append(f"Overly long hashtags nobody searches: {' '.join(long_tags)}")
    return problems
