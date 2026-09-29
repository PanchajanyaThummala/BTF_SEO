#!/usr/bin/env python3
"""Build a keyword-first Instagram caption with at most 5 hashtags.

Example:
  python3 tools/caption_builder.py --pillar breakdown --team Arsenal \
      --opponent Chelsea --competition "Premier League" \
      --topic "high press" --hook "How Arsenal broke Chelsea's press"
"""
import argparse

from _common import MAX_HASHTAGS, load_keywords, to_hashtag

BODIES = {
    "breakdown": (
        "{team} vs {opponent}: here's what really decided it.\n"
        "1️⃣ {point1}\n2️⃣ {point2}\n3️⃣ {point3}\n\n"
        "Would this work against anyone else? 👇\n"
        "Send this to every {team} fan 📩"
    ),
    "explained": (
        "{topic} explained, football tactics made simple.\n"
        "✅ Strength: {point1}\n❌ Weakness: {point2}\n🏆 Best example: {point3}\n\n"
        "Save this 📌 for later."
    ),
    "player": (
        "Why {player} is elite at {topic} 🧠\n"
        "📊 {point1}\n📊 {point2}\n📊 {point3}\n\n"
        "Who's better in this role? Drop a name 👇"
    ),
    "debate": (
        "{point1}\n\n"
        "Agree or disagree? Send this to someone who'll argue 😤"
    ),
    "quiz": (
        "Guess the team from its formation 🔍\n"
        "Hint: {point1}\n"
        "Answer in the comments. Reveal in tomorrow's Story 👀"
    ),
}


def build_hashtags(kw, pillar, team=None, player=None, competition=None):
    tags = [kw["core_hashtags"][0], kw["pillars"][pillar]["topic_hashtag"]]
    if player:
        tags.append(to_hashtag(player))
    if team:
        tags.append(to_hashtag(team))
    if competition:
        tags.append(kw["competitions"].get(competition, to_hashtag(competition)))
    tags.append(kw["pillars"][pillar]["extra_hashtag"])
    brand = kw["brand"]["hashtag"]
    # Keep order and drop duplicates; always finish with the brand tag.
    seen, out = set(), []
    for t in tags:
        if t not in seen and t != brand:
            seen.add(t)
            out.append(t)
    return out[: MAX_HASHTAGS - 1] + [brand]


def build_caption(args, kw):
    team = args.team or "{Team}"
    topic = args.topic or "This tactic"
    first_line = args.hook
    # Add keywords to the first line if the hook has none.
    lowered = first_line.lower()
    extras = []
    if args.team and args.team.lower() not in lowered:
        extras.append(args.team)
    if not any(k in lowered for k in ("tactic", "analysis", "explained", "formation")):
        extras.append("tactical analysis" if args.pillar != "quiz" else "football quiz")
    if extras:
        first_line = f"{first_line} | {' '.join(extras)}"

    body = BODIES[args.pillar].format(
        team=team,
        opponent=args.opponent or "{Opponent}",
        player=args.player or "{Player}",
        topic=topic,
        point1=args.points[0] if len(args.points) > 0 else "{point 1}",
        point2=args.points[1] if len(args.points) > 1 else "{point 2}",
        point3=args.points[2] if len(args.points) > 2 else "{point 3}",
    )
    tags = build_hashtags(kw, args.pillar, args.team, args.player, args.competition)
    alt = (
        f"Tactical graphic from {kw['brand']['name']}: "
        f"{args.hook}{' in ' + args.competition if args.competition else ''}."
    )
    return f"{first_line}\n\n{body}\n\n{' '.join(tags)}", alt


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pillar", choices=sorted(BODIES), required=True)
    p.add_argument("--hook", required=True, help="First line / on-screen hook")
    p.add_argument("--team")
    p.add_argument("--opponent")
    p.add_argument("--player")
    p.add_argument("--competition", help='e.g. "Premier League"')
    p.add_argument("--topic", help='e.g. "inverted full-back", "4-3-3"')
    p.add_argument("--point", dest="points", action="append", default=[], help="Repeat up to 3 times")
    args = p.parse_args()

    caption, alt = build_caption(args, load_keywords())
    print("=== CAPTION ===")
    print(caption)
    print("\n=== ALT TEXT (Advanced settings → Accessibility) ===")
    print(alt)


if __name__ == "__main__":
    main()
