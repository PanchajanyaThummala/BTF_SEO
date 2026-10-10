"""Optional AI writer: Claude drafts the post package, then the engine enforces the rules
(≤5 hashtags, brand tag, keywords) and scores it.

Needs ``pip install anthropic`` and credentials (``ANTHROPIC_API_KEY`` or an ``ant auth login`` profile).
"""
import json

from . import config, hashtags, scorer
from .captions import PostPackage

SYSTEM_PROMPT = """You write Instagram posts for {name} ({handle}), a football TACTICS page: "the page that explains \
the game behind the goals". Audience: football fans aged 16-35 who like smart analysis without jargon overload.

Instagram search and recommendation rules you must follow:
- The caption's first line (≤125 characters) is the search headline. It must contain the team/player/competition \
name AND a tactics keyword (e.g. "tactical analysis", "high press", "4-3-3", "inverted full-back").
- Instagram reads on-screen text and transcribes voiceover, so the on-screen hook (≤70 chars) and the \
voiceover opening line must also contain those keywords.
- Exactly 5 hashtags: niche tactics tag, topic tag, club/player tag, competition tag, and {brand_tag} last. \
Never use generic tags like {avoid}.
- End with a call to action that makes people SEND the post to a friend (DM shares drive reach most), plus a \
question that invites comments.
- Content must be original analysis in the page's own voice, never "credit to owner" reposting. Be specific: \
roles, spaces, player names, phases of play. Don't invent statistics; if the brief has no numbers, speak \
qualitatively.
- Tone: confident, conversational, British-English football vocabulary is fine. Short lines, a few emoji at most.
- Alt text: one or two plain sentences describing the tactical graphic with the key names and tactic."""

SCHEMA = {
    "type": "object",
    "properties": {
        "hook_options": {"type": "array", "items": {"type": "string"},
                         "description": "3-5 alternative scroll-stopping hooks, best first"},
        "on_screen_text": {"type": "string"},
        "caption_without_hashtags": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "alt_text": {"type": "string"},
        "cover_title": {"type": "string", "description": "2-5 word title for the Reel cover"},
        "voiceover_opening": {"type": "string", "description": "What to say in the first 5 seconds"},
    },
    "required": ["hook_options", "on_screen_text", "caption_without_hashtags", "hashtags", "alt_text",
                 "cover_title", "voiceover_opening"],
    "additionalProperties": False,
}


class AIUnavailable(RuntimeError):
    pass


def _brief_text(brief):
    parts = [f"Pillar: {brief.pillar}"]
    for label, val in (("Hook idea", brief.hook), ("Team", brief.team), ("Opponent", brief.opponent),
                       ("Player", brief.player), ("Competition", brief.competition), ("Tactic/topic", brief.topic)):
        if val:
            parts.append(f"{label}: {val}")
    if brief.points:
        parts.append("Key points:\n" + "\n".join(f"- {p}" for p in brief.points))
    if brief.notes:
        parts.append(f"Extra notes: {brief.notes}")
    return "\n".join(parts)


def build(brief, model=None, effort="medium"):
    try:
        import anthropic
    except ImportError as e:
        raise AIUnavailable("Install the SDK first: pip install anthropic") from e

    kw = config.keywords()
    system = SYSTEM_PROMPT.format(name=kw["brand"]["name"], handle=kw["brand"]["handle"],
                                  brand_tag=kw["brand"]["hashtag"], avoid=" ".join(kw["avoid_hashtags"][:6]))
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=model or config.settings().ai_model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": "Write the post package for this brief.\n\n" + _brief_text(brief)}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
            # On a safety decline, the API retries on a fallback model inside the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise AIUnavailable("No valid Anthropic credentials (set ANTHROPIC_API_KEY or run `ant auth login`)") from e
    except anthropic.RateLimitError as e:
        raise AIUnavailable("Rate limited by the Anthropic API; try again shortly") from e
    except anthropic.APIConnectionError as e:
        raise AIUnavailable("Could not reach the Anthropic API") from e
    except anthropic.APIStatusError as e:
        raise AIUnavailable(f"Anthropic API error {e.status_code}: {e.message}") from e
    except TypeError as e:  # raised by the SDK when no credential source is configured at all
        if "authentication" not in str(e).lower():
            raise
        raise AIUnavailable("No Anthropic credentials (set ANTHROPIC_API_KEY or run `ant auth login`)") from e

    if response.stop_reason == "refusal":
        raise AIUnavailable("The model declined this brief")
    if response.stop_reason == "max_tokens":
        raise AIUnavailable("Response was cut off (max_tokens)")
    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)

    # Enforce the rules regardless of what the model returned.
    tags = []
    for t in data["hashtags"]:
        t = "#" + t.lstrip("#").lower().replace(" ", "")
        if t not in tags and t not in kw["avoid_hashtags"] and t != kw["brand"]["hashtag"]:
            tags.append(t)
    if len(tags) < hashtags.MAX_HASHTAGS - 1:
        for t in hashtags.select(brief.pillar, team=brief.team or None, player=brief.player or None,
                                 competition=brief.competition or None):
            if t not in tags and t != kw["brand"]["hashtag"]:
                tags.append(t)
    tags = tags[: hashtags.MAX_HASHTAGS - 1] + [kw["brand"]["hashtag"]]

    body = data["caption_without_hashtags"].strip()
    pkg = PostPackage(
        pillar=brief.pillar,
        hook_options=data["hook_options"][:5],
        on_screen_text=data["on_screen_text"],
        caption=f"{body}\n\n{' '.join(tags)}",
        hashtags=tags,
        alt_text=data["alt_text"],
        cover_title=data["cover_title"],
        voiceover_opening=data["voiceover_opening"],
        source=f"ai:{response.model}",
    )
    pkg.score = scorer.score(pkg.caption, pkg.alt_text, pkg.on_screen_text).to_dict()
    return pkg
