"""Scroll-stopping hook generator for the first 2 seconds of a Reel."""

FORMULAS = {
    "breakdown": [
        "How {team} broke {opponent}'s {topic}",
        "The tactical change that decided {team} vs {opponent}",
        "Nobody is talking about what {team} did with the {topic}",
        "{opponent} had no answer to this {team} {topic}",
        "3 tactical reasons {team} beat {opponent}",
    ],
    "explained": [
        "{topic} explained in 60 seconds",
        "Why every top team uses the {topic} now",
        "The {topic}: the tactic that changed modern football",
        "You've seen the {topic}. Here's how it actually works",
        "{topic} explained with {team} as the example",
    ],
    "player": [
        "Why {player} is the best {topic} in the world right now",
        "{player} does this every game and nobody notices",
        "The {topic} role that makes {player} elite",
        "Stop judging {player} on goals. Watch this",
        "What {player} does without the ball is ridiculous",
    ],
    "debate": [
        "{team}'s {topic} is the best in Europe. Change my mind",
        "Hot take: the {topic} is overrated",
        "{team} don't need a new striker. They need to fix the {topic}",
        "Is {player} actually good at the {topic}? Let's check",
    ],
    "quiz": [
        "Guess the team from its formation",
        "Only real tactics fans get 5/5 on this",
        "Name the team that played this {topic}",
        "Which {topic} would win? Pick one",
    ],
}


def generate(pillar, team=None, opponent=None, player=None, topic=None, limit=5):
    fills = {
        "team": team or "",
        "opponent": opponent or "",
        "player": player or "",
        "topic": topic or "system",
    }
    out = []
    for f in FORMULAS[pillar]:
        needed = [k for k in ("team", "opponent", "player") if "{" + k + "}" in f]
        if any(not fills[k] for k in needed):
            continue
        out.append(f.format(**fills))
    return out[:limit]
