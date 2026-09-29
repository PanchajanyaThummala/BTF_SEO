# Beyond The Formation — Instagram SEO Engine

A complete playbook plus small tools to make **Beyond The Formation** ([@beyond_the_formationn](https://www.instagram.com/beyond_the_formationn/)) the go-to football tactics page on Instagram:
found in search, recommended in Explore/Reels, and shared in DMs.

> **Positioning:** *the page that explains the game behind the goals.* Tactics, formations, player roles and match analysis in short Reels. This niche beats "generic highlights" pages because it is original, gets saved, and gets sent in DMs.

## How Instagram ranking works (2026)

| Surface | What gets you found | What keeps you ranking |
|---|---|---|
| **Search** | Name field, @handle, bio keywords, caption keywords, on-screen text, spoken audio (auto-transcribed), alt text, ≤5 hashtags | Profile taps, follows from search |
| **Reels / Explore** | Topic signals from captions, audio, visuals | **Sends per reach** (DM shares), watch time, rewatches, likes per reach |
| **Feed** | Existing followers | Comments, saves, replies to Stories |
| **Google** | Public posts from professional accounts are indexed | Descriptive captions and alt text read like web text |

Key rules:
- **Originality wins.** Reposting other creators' clips gets suppressed. Add your own voiceover, edit, analysis or graphic.
- **Keywords beat hashtags.** Write captions like search queries ("Arsenal vs Chelsea highlights and tactical breakdown"). Instagram now caps hashtags at **5 per post**, so pick relevant ones.
- **The first 3 seconds decide reach.** Put the hook as on-screen text, and say it out loud too.
- **Sends are the strongest signal.** Make content people DM to a mate ("tag the mate who…", hot takes, "which XI would win").

## Top 5 fixes to do today

1. **Name field** → `Beyond The Formation | Football Tactics`. It's searchable, and the double-n handle is hard to find.
2. **Bio** → start with "Football tactics explained in 60 seconds".
3. **First line of every caption** = team/player + tactic keyword, e.g. *"How Arsenal broke Chelsea's high press"*.
4. **Hashtags: 5 at most**, always ending with `#beyondtheformation`. Drop `#football #fyp #viral`.
5. **Post within 2–6 hours after big matches**, and end every Reel with a "send this to…" CTA.

## What's in this repo

| Path | Contents |
|---|---|
| [`docs/01-profile-optimization.md`](docs/01-profile-optimization.md) | Handle fix, name field, bio, highlights, pinned posts |
| [`docs/02-keyword-and-hashtag-strategy.md`](docs/02-keyword-and-hashtag-strategy.md) | Keyword tiers, the 5-hashtag formula, weekly research |
| [`docs/03-content-pillars.md`](docs/03-content-pillars.md) | What to post and why each type ranks |
| [`docs/04-reels-playbook.md`](docs/04-reels-playbook.md) | Hooks, structure, production checklist, trial reels |
| [`docs/05-caption-templates.md`](docs/05-caption-templates.md) | Copy-paste caption templates |
| [`docs/06-posting-calendar.md`](docs/06-posting-calendar.md) | Weekly schedule built around the match calendar |
| [`docs/07-growth-and-engagement.md`](docs/07-growth-and-engagement.md) | Collabs, comments, Stories, broadcast channel |
| [`docs/08-analytics-kpis.md`](docs/08-analytics-kpis.md) | Which metrics matter and weekly targets |
| [`docs/90-day-plan.md`](docs/90-day-plan.md) | Step-by-step plan for the first 90 days |
| [`data/keywords.json`](data/keywords.json) | Keyword and hashtag bank (edit this) |
| [`tools/caption_builder.py`](tools/caption_builder.py) | Builds an SEO caption, 5 hashtags and alt text |
| [`tools/seo_check.py`](tools/seo_check.py) | Scores a caption before you post it |

## Quick start

```bash
# Build a caption + alt text for a tactical-breakdown Reel
# pillars: breakdown | explained | player | debate | quiz
python3 tools/caption_builder.py --pillar breakdown \
  --team "Arsenal" --opponent "Chelsea" --competition "Premier League" \
  --hook "How Arsenal broke Chelsea's high press" \
  --point "Full-back tucks in to make a 2-3-5" \
  --point "Rice drops between the CBs" \
  --point "Saka isolates the left-back"

# Score any caption (exit code 0 when score ≥ 80)
python3 tools/seo_check.py --file my_caption.txt
python3 tools/seo_check.py "Arsenal vs Chelsea tactical analysis ... #beyondtheformation"
```

Python 3.8+ only. No dependencies.
