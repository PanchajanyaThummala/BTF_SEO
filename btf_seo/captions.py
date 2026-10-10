"""Build a complete, keyword-optimised post package: hooks, caption, hashtags, alt text, cover title."""
from dataclasses import asdict, dataclass, field

from . import config, hashtags, hooks, scorer

PILLARS = ("breakdown", "explained", "player", "debate", "quiz")

BODIES = {
    "breakdown": (
        "{team}{vs_opponent}: here's what really decided it 📐\n\n"
        "1️⃣ {p1}\n2️⃣ {p2}\n3️⃣ {p3}\n\n"
        "Would this work against a low block? 👇\n"
        "Send this to every {team_or_fan} fan 📩"
    ),
    "explained": (
        "{topic} explained: football tactics made simple 🧠\n\n"
        "✅ Strength: {p1}\n❌ Weakness: {p2}\n🏆 Best example: {p3}\n\n"
        "Save this 📌 and send it to the mate who still thinks formations don't matter."
    ),
    "player": (
        "Why {player} is elite at the {topic} role 🧠\n\n"
        "📊 {p1}\n📊 {p2}\n📊 {p3}\n\n"
        "Who's better in this role? Drop a name 👇\n"
        "Send this to a {player_surname} fan 📩"
    ),
    "debate": (
        "{p1}\n\n{p2}\n\n"
        "Agree or disagree? 👇\n"
        "Send this to someone who'll argue 😤"
    ),
    "quiz": (
        "Guess the team from its formation 🔍\n"
        "Hint: {p1}\n\n"
        "Answer in the comments. Reveal in tomorrow's Story 👀\n"
        "Tag a mate who thinks they know tactics."
    ),
}

DEFAULT_POINTS = {
    "breakdown": ["{point 1: the shape in possession}", "{point 2: the key player/role}", "{point 3: the moment it paid off}"],
    "explained": ["{strength}", "{weakness}", "{team + manager}"],
    "player": ["{stat 1}", "{stat 2}", "{what they do off the ball}"],
    "debate": ["{your hot take}", "{2-line argument}", ""],
    "quiz": ["{hint}", "", ""],
}


@dataclass
class Brief:
    pillar: str
    hook: str = ""
    team: str = ""
    opponent: str = ""
    player: str = ""
    competition: str = ""
    topic: str = ""
    points: list = field(default_factory=list)
    notes: str = ""


@dataclass
class PostPackage:
    pillar: str
    hook_options: list
    on_screen_text: str
    caption: str
    hashtags: list
    alt_text: str
    cover_title: str
    voiceover_opening: str
    source: str = "template"
    score: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def render(self):
        s = self.score or {}
        lines = [
            f"=== POST PACKAGE ({self.pillar}, {self.source}) — SEO score {s.get('score', '?')}/100 [{s.get('grade', '?')}] ===",
            "", "HOOK OPTIONS (test 2 with Trial Reels):", *[f"  {i + 1}. {h}" for i, h in enumerate(self.hook_options)],
            "", f"ON-SCREEN TEXT (first frame): {self.on_screen_text}",
            f"COVER TITLE: {self.cover_title}",
            f"SAY IN FIRST 5s: {self.voiceover_opening}",
            "", "CAPTION:", self.caption,
            "", "ALT TEXT (Advanced settings → Accessibility):", self.alt_text,
        ]
        if s.get("fixes"):
            lines += ["", "TO IMPROVE:", *[f"  - {f}" for f in s["fixes"]]]
        return "\n".join(lines)


def _surname(name):
    return name.split()[-1] if name else ""


def _keyword_suffix(brief, line):
    """Append missing search keywords to the first line: entity + tactic keyword."""
    low = line.lower()
    extras = []
    for name in (brief.team, brief.player):
        if name and name.lower() not in low and _surname(name).lower() not in low:
            extras.append(name)
            break
    if not scorer._has_keyword(line):
        extras.append("football quiz" if brief.pillar == "quiz" else
                      "formation explained" if brief.pillar == "explained" else "tactical analysis")
    return f"{line} | {' '.join(extras)}" if extras else line


def _cover_title(brief, hook):
    who = brief.player if brief.pillar == "player" else brief.team
    base = " ".join(x for x in (who, brief.topic) if x) or hook
    words = base.upper().split()
    return " ".join(words[:5])


def build(brief):
    """Template-based package (works offline, no API key needed)."""
    if brief.pillar not in PILLARS:
        raise ValueError(f"pillar must be one of {PILLARS}")
    brand = config.keywords()["brand"]["name"]
    hook_opts = ([brief.hook] if brief.hook else []) + hooks.generate(
        brief.pillar, brief.team, brief.opponent, brief.player, brief.topic)
    hook_opts = list(dict.fromkeys(h for h in hook_opts if h))[:5] or ["{write your hook}"]
    hook = hook_opts[0]

    pts = list(brief.points) + DEFAULT_POINTS[brief.pillar][len(brief.points):]
    body = BODIES[brief.pillar].format(
        team=brief.team or "{Team}",
        vs_opponent=f" vs {brief.opponent}" if brief.opponent else "",
        team_or_fan=brief.team or "football",
        topic=(brief.topic or "This tactic").capitalize() if brief.pillar == "explained" else (brief.topic or "this"),
        player=brief.player or "{Player}",
        player_surname=_surname(brief.player) or "football",
        p1=pts[0], p2=pts[1], p3=pts[2],
    )
    tags = hashtags.select(brief.pillar, text=hook, team=brief.team or None, player=brief.player or None,
                           competition=brief.competition or None)
    line1 = _keyword_suffix(brief, hook)
    caption = f"{line1}\n\n{body}\n\n{' '.join(tags)}"

    subject = " vs ".join(x for x in (brief.team, brief.opponent) if x) or brief.player or brief.topic or "a football tactic"
    comp = f" in the {brief.competition}" if brief.competition else ""
    alt = (f"{brand} tactical graphic on a football pitch: {subject}{comp}. "
           f"{'Shows the ' + brief.topic + '. ' if brief.topic else ''}{hook}.")
    voice = f"This is a {brief.topic or 'tactical'} breakdown of {subject}{comp}." if brief.pillar != "quiz" \
        else f"Football quiz time: guess the team from its {brief.topic or 'formation'}."

    pkg = PostPackage(brief.pillar, hook_opts, hook, caption, tags, alt, _cover_title(brief, hook), voice)
    pkg.score = scorer.score(pkg.caption, pkg.alt_text, pkg.on_screen_text).to_dict()
    return pkg
