# 2. Keyword & Hashtag Strategy

Instagram search works like a search engine now. Keywords in your **caption, on-screen text, spoken audio and alt text** matter more than hashtags. Instagram caps hashtags at **5 per post**.

## Keyword tiers

| Tier | Purpose | Examples |
|---|---|---|
| **Core (brand)** | Own your niche | Beyond The Formation, football tactics, tactical analysis, formation explained |
| **Topic** | What this post is about | 4-3-3, high press, inverted full-back, false 9, low block, gegenpressing, build-up play |
| **Entity** | Trending names people search | Club, manager, player, competition: *Arsenal, Arteta, Rodri, Champions League* |
| **Moment** | Time-sensitive | *Arsenal vs Chelsea*, *El Clásico*, *derby*, *transfer deadline*, *matchweek 7* |

**Rule:** every caption's first line has **1 entity + 1 topic keyword**.
> ✅ *"How Arteta's 4-3-3 turns into a 2-3-5 in possession"*
> ❌ *"This is crazy 🤯🔥"*

## Where keywords must appear (every post)
1. **First line of the caption**. Only about 125 characters show before "more".
2. **On-screen text** in the first 3 seconds. Instagram reads on-screen text.
3. **Spoken**: say the keyword in the voiceover. Audio gets transcribed.
4. **Alt text** (Advanced settings → Accessibility): *"Tactical graphic showing Arsenal's 2-3-5 shape in possession against Chelsea"*.
5. **Cover title** on Reels.
6. **Hashtags**: 5 at most.

## The 5-hashtag formula

| Slot | Type | Example |
|---|---|---|
| 1 | Niche core | `#footballtactics` |
| 2 | Topic | `#tacticalanalysis` / `#formation` |
| 3 | Entity (club/player) | `#arsenal` |
| 4 | Competition / moment | `#premierleague` |
| 5 | Brand | `#beyondtheformation` |

- Always use `#beyondtheformation` so your content is collected in one place.
- Skip dead tags like `#football`, `#soccer`, `#fyp`, `#viral`. They're too broad to rank in and say nothing about your topic.
- Before using a new tag, search it. If "Recent" shows nothing or the posts are hidden, the tag is restricted. Don't use it.

## Keyword research workflow (weekly, 15 min)
1. Type your topic into Instagram search, e.g. "football tac…", and write down the autocomplete suggestions.
2. Check Google Trends and YouTube autocomplete for this week's names: new signings, sacked managers, derby games.
3. Update `data/keywords.json` with the hot entities.
4. Write captions with `tools/caption_builder.py`.
