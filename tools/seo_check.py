#!/usr/bin/env python3
"""Score an Instagram caption for search and discovery (0–100).

  python3 tools/seo_check.py "Your caption here #footballtactics"
  python3 tools/seo_check.py --file caption.txt
"""
import argparse
import sys

from _common import MAX_HASHTAGS, extract_hashtags, load_keywords

CTA_WORDS = ("send", "share", "comment", "save", "tag", "drop", "👇", "agree", "?")


def check(caption, kw):
    text = caption.lower()
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    tags = extract_hashtags(caption)
    keywords = kw["core_keywords"] + kw["topic_keywords"] + [c.lower() for c in kw["competitions"]]
    results = []

    def add(ok, points, msg_ok, msg_fix):
        results.append((ok, points, msg_ok if ok else msg_fix))

    add(any(k in first_line for k in keywords) or any(w in first_line for w in ("tactic", "formation", "explained")),
        25, "First line contains a search keyword",
        "Put a search keyword (tactic/formation/team/competition) in the FIRST line")
    add(len(first_line) <= 125, 10, "First line fits before '… more'",
        f"First line is {len(first_line)} chars, keep it ≤125")
    add(not first_line.startswith("#") and not first_line.startswith("@"), 5,
        "Caption opens with words, not tags", "Don't start the caption with a hashtag or mention")
    add(0 < len(tags) <= MAX_HASHTAGS, 15, f"{len(tags)} hashtags (≤{MAX_HASHTAGS})",
        f"Use 1–{MAX_HASHTAGS} hashtags (found {len(tags)})")
    add(kw["brand"]["hashtag"] in tags, 10, "Brand hashtag present",
        f"Add {kw['brand']['hashtag']}")
    bad = [t for t in tags if t in kw["avoid_hashtags"]]
    add(not bad, 10, "No generic/dead hashtags", f"Remove generic tags: {' '.join(bad)}")
    add(any(w in text for w in CTA_WORDS), 15, "Has a call to action (send/save/comment)",
        "Add a CTA, e.g. 'Send this to a mate who…' (sends drive reach)")
    words = len(caption.split())
    add(20 <= words <= 300, 10, f"Length OK ({words} words)",
        f"Caption has {words} words; aim for 20–300 so there's context for search")

    score = sum(p for ok, p, _ in results if ok)
    return score, results


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("caption", nargs="?")
    p.add_argument("--file")
    args = p.parse_args()
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            caption = f.read()
    elif args.caption:
        caption = args.caption
    else:
        caption = sys.stdin.read()

    score, results = check(caption, load_keywords())
    for ok, points, msg in results:
        print(f"{'✅' if ok else '❌'} [{points:>2}] {msg}")
    verdict = "Ready to post" if score >= 80 else "Fix the ❌ items before posting"
    print(f"\nSEO score: {score}/100. {verdict}")
    sys.exit(0 if score >= 80 else 1)


if __name__ == "__main__":
    main()
