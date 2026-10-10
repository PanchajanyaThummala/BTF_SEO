# Beyond The Formation — Instagram SEO Engine

A full SEO engine plus a strategy playbook to make **Beyond The Formation** ([@beyond_the_formationn](https://www.instagram.com/beyond_the_formationn/)) the go-to football tactics page on Instagram:
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

## The SEO engine

`btf_seo` is a Python engine that does the SEO work for every post:

| Module | What it does |
|---|---|
| **Keyword research** (`btf keywords`) | Expands your topics through Google and YouTube autocomplete (what people actually type) and ranks phrases by demand, tactics relevance, long-tail value and trending names. Each phrase gets an intent (question / explainer / versus / gaming…) and a suggested content pillar. |
| **Trend radar** (`btf trends`) | Reads BBC, Guardian, ESPN and Sky football feeds, ranks clubs, players and managers by recency-weighted mentions, spots new names, and turns the news into ideas (e.g. manager sacked → "What X need from their next manager"). |
| **Caption studio** (`btf caption`) | Builds a complete post: 5 hook options for A/B tests, on-screen text, cover title, a voiceover line for the first 5 seconds, a keyword-first caption, 5 hashtags and alt text. `--ai` has Claude write it; the engine still enforces the rules. |
| **SEO scorer** (`btf score`) | Scores a caption 0–100 on 14 checks (first-line keyword and name, length, ≤5 hashtags, brand tag, send CTA, stuffing, placeholders, alt text, on-screen text) and lists the fixes. |
| **Hashtag optimizer** (`btf hashtags`) | Picks 5 hashtags by slot: tactics tag → topic → club/player → competition → `#beyondtheformation`. Blocks dead tags like `#fyp`. |
| **Content calendar** (`btf calendar`) | Plans the week around the pillar rhythm, big fixtures (post-match slots), trending topics and evergreen explainers. Exports `.ics` (Google/Apple Calendar) or `.csv`. |
| **Analytics** (`btf analytics`) | Reads your Insights CSV export or the Instagram API. Shows KPIs against targets, results by pillar, weekday, time slot, format and SEO score, your top and bottom posts, and what to change. |
| **Profile audit** (`btf profile`) | Checks the handle (including the double-n problem), name field, bio and link, and suggests alternative handles and a bio. |
| **HTML report** (`btf report`) | Combines all of the above into one page you can share. |
| **Dashboard** (`btf serve`) | Runs all the tools in a local web app at http://127.0.0.1:8787 |

### Install

```bash
git clone https://github.com/PanchajanyaThummala/BTF_SEO && cd BTF_SEO
pip install -e .            # installs the `btf` command (no dependencies)
pip install -e ".[ai]"      # optional: Claude-powered caption writing
```
You can also skip installing and run `python3 -m btf_seo <command>` from the repo. Requires Python 3.9+.

### Daily workflow

```bash
btf trends                                   # what's hot right now + ideas
btf keywords "arsenal tactics" "false 9"     # which phrases people actually search
btf caption --pillar breakdown --team Arsenal --opponent Chelsea \
  --competition "Premier League" --topic "high press" \
  --point "Full-back tucks in to make a 2-3-5" \
  --point "Rice drops between the CBs" --point "Saka isolates the left-back"
btf score --file my_caption.txt --alt "..." --screen "..."   # exit code 0 when ≥ 80
```

### Weekly workflow

```bash
btf calendar --weeks 2 --fixtures data/sample_fixtures.csv --out week.ics
btf analytics --csv insights_export.csv
btf report --csv insights_export.csv --name "Beyond The Formation | Football Tactics" \
  --bio "⚽ Football tactics explained in 60 seconds\n🔔 New breakdown every matchday" --out report.html
btf serve                                    # or do it all in the dashboard
```

### Optional connections (environment variables)

| Variable | Enables | How to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | `btf caption --ai` (Claude writes the package; default model `claude-opus-5-5`, override with `BTF_AI_MODEL`) | console.anthropic.com, or run `ant auth login` |
| `IG_ACCESS_TOKEN` | `btf analytics --instagram`: live posts and insights | Meta app → Instagram API with Instagram Login → long-lived token with `instagram_business_basic` + `instagram_business_manage_insights` |
| `FOOTBALL_DATA_TOKEN` | `btf calendar --football-data`: automatic fixtures | Free at football-data.org |

Without these, everything else still works: templates replace AI, a CSV export replaces the API, and a fixtures CSV replaces football-data.org.

### Customise it
- `data/keywords.json`: brand, keywords, pillars, hashtags, blocked tags, news feeds.
- `data/entities.json`: the clubs, players and managers the engine recognises. Add new signings and managers here.
- `data/sample_insights.csv` / `data/sample_fixtures.csv`: example input formats.

### Tests
```bash
python3 -m unittest discover -s tests
```

## Strategy playbook

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
