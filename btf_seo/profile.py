"""Profile audit: handle, name field, bio and link, the parts Instagram search weights most."""
import re

from . import config
from .text import contains_phrase, extract_hashtags, normalize

CTA_WORDS = ["request", "dm", "follow", "comment", "👇", "join", "subscribe", "new", "every"]


def handle_alternatives(brand):
    w = re.sub(r"[^a-z ]", "", brand.lower()).split()
    joined = "".join(w)
    alts = [joined, ".".join(w), "_".join(w), "".join(x for x in w if x != "the"),
            f"{joined}.fc", f"{joined}_tactics", f"{''.join(x[0] for x in w)}.tactics", f"the{joined}" if w[0] != "the" else ""]
    return [a for a in dict.fromkeys(alts) if a and len(a) <= 30]


def audit(handle="", name="", bio="", link="", followers=None):
    kw = config.keywords()
    brand = kw["brand"]["name"]
    handle = (handle or kw["brand"]["handle"]).lstrip("@")
    checks, suggestions = [], []

    def add(area, ok, msg_ok, msg_fix):
        checks.append({"area": area, "ok": ok, "message": msg_ok if ok else msg_fix})

    # --- handle
    brand_compact = re.sub(r"[^a-z]", "", brand.lower())
    handle_compact = re.sub(r"[^a-z]", "", handle.lower())
    typo = handle_compact != brand_compact and handle_compact.rstrip(handle_compact[-1:]) == brand_compact.rstrip(brand_compact[-1:])
    add("handle", not typo, "Handle matches the brand name",
        f"@{handle} has an extra/doubled letter vs '{brand}'. People can't find or tag it from memory")
    add("handle", handle.count("_") + handle.count(".") <= 1, "Handle is easy to type",
        "Too many underscores/dots; every separator is a chance to mistype")
    add("handle", not re.search(r"\d", handle), "No numbers in handle", "Numbers in handles look like spam and are hard to remember")
    add("handle", len(handle) <= 20, "Handle length OK", f"Handle is {len(handle)} chars; shorter is easier to tag")
    if not all(c["ok"] for c in checks if c["area"] == "handle"):
        suggestions.append("Check if any of these are free and switch (followers are kept): "
                           + ", ".join("@" + a for a in handle_alternatives(brand)))

    # --- name field
    if name:
        norm = normalize(name)
        has_kw = any(contains_phrase(norm, t) for t in kw["core_keywords"] + ["tactics", "tactical", "analysis", "football"])
        add("name", has_kw, "Name field contains a search keyword",
            "Name field has no search keyword; it's the most-weighted searchable text after the handle")
        add("name", brand.lower() in name.lower(), "Brand name in name field", f"Include '{brand}' in the name field")
        add("name", len(name) <= 64, "Name field length OK", f"Name field is {len(name)} chars (max 64)")
    else:
        add("name", False, "", "Name field not provided for audit")
    suggestions.append(f"Name field: `{brand} | Football Tactics`")

    # --- bio
    if bio:
        norm = normalize(bio)
        add("bio", len(bio) <= 150, "Bio length OK", f"Bio is {len(bio)} chars (max 150)")
        add("bio", any(contains_phrase(norm, t) for t in kw["core_keywords"] + ["tactics", "formation", "analysis"]),
            "Bio contains niche keywords", "Put 'football tactics' / 'formations' / 'analysis' in the bio")
        add("bio", any(w in bio.lower() for w in CTA_WORDS), "Bio has a call to action / promise",
            "Add a CTA or promise ('New breakdown every matchday', 'Request a team 👇')")
        add("bio", len(extract_hashtags(bio)) <= 1, "Bio isn't stuffed with hashtags",
            "Remove hashtags from bio; they send visitors away")
        add("bio", "\n" in bio, "Bio is split into scannable lines", "Split the bio into 3–4 short lines")
    else:
        add("bio", False, "", "Bio not provided for audit")
    suggestions.append("Bio:\n⚽ Football tactics explained in 60 seconds\n📐 Formations • Player roles • Match analysis\n"
                       "🔔 New breakdown every matchday\n👇 Request a team/tactic")

    add("link", bool(link), "Link in bio set", "Add a link (request form, broadcast channel, or link hub)")

    ok = sum(c["ok"] for c in checks)
    return {"handle": "@" + handle, "score": round(100 * ok / len(checks)), "checks": checks, "suggestions": suggestions,
            "followers": followers}
