import datetime as dt
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("BTF_CACHE_DIR", tempfile.mkdtemp())

from btf_seo import (analytics, calendar_plan, captions, cli, fixtures, hashtags, keywords, profile,  # noqa: E402
                     report, scorer, text, trends)

DATA = Path(__file__).resolve().parent.parent / "data"
GOOD = ("How Arsenal broke Chelsea's high press | tactical analysis\n\n"
        "Arsenal vs Chelsea: the full-back tucked in to make a 2-3-5, Rice dropped between the centre-backs "
        "and Saka isolated the left-back every time.\n\nWould this work against a low block? 👇\n"
        "Send this to every Arsenal fan 📩\n\n"
        "#footballtactics #tacticalanalysis #arsenal #premierleague #beyondtheformation")


class TextTests(unittest.TestCase):
    def test_hashtag_normalisation(self):
        self.assertEqual(text.to_hashtag("Mbappé"), "#mbappe")
        self.assertEqual(text.to_hashtag("Man City"), "#mancity")

    def test_possessive_matches_entity(self):
        names = [n for n, _, _ in text.find_entities("How Arsenal broke Chelsea's high press")]
        self.assertEqual(sorted(names), ["Arsenal", "Chelsea"])

    def test_hyphen_and_space_match(self):
        self.assertIn(text.normalize("full back"), text.normalize("the inverted full-back role"))

    def test_entities_prefer_longest_and_skip_lowercase_ambiguous(self):
        names = [n for n, _, _ in text.find_entities("Manchester City beat the city rivals")]
        self.assertEqual(names, ["Manchester City"])
        self.assertEqual(text.find_entities("rice and beans"), [])
        self.assertEqual(text.find_entities("Rice was superb")[0][0], "Declan Rice")


class HashtagTests(unittest.TestCase):
    def test_select_is_five_with_brand_last(self):
        tags = hashtags.select("breakdown", team="Man City", competition="Champions League")
        self.assertLessEqual(len(tags), 5)
        self.assertEqual(tags[-1], "#beyondtheformation")
        self.assertIn("#mancity", tags)
        self.assertIn("#championsleague", tags)
        self.assertEqual(hashtags.validate(tags), [])

    def test_validate_flags_problems(self):
        problems = " ".join(hashtags.validate("#football #fyp #a #b #c #d"))
        self.assertIn("allows 5", problems)
        self.assertIn("Generic", problems)
        self.assertIn("brand", problems)

    def test_unknown_pillar(self):
        with self.assertRaises(ValueError):
            hashtags.select("memes")


class ScorerTests(unittest.TestCase):
    def test_good_caption_scores_high(self):
        r = scorer.score(GOOD, alt_text="Tactical graphic showing Arsenal's 2-3-5 against Chelsea's high press",
                         on_screen_text="How Arsenal broke Chelsea's press")
        self.assertGreaterEqual(r.score, 90, r.fixes)

    def test_bad_caption_scores_low(self):
        r = scorer.score("#football this is crazy 🔥 #fyp #viral")
        self.assertLess(r.score, 50)
        self.assertTrue(any("FIRST line" in f for f in r.fixes))

    def test_placeholders_flagged(self):
        r = scorer.score(GOOD.replace("Saka isolated", "{point 3}"))
        self.assertIn("no_placeholders", [c.name for c in r.checks if not c.ok])

    def test_too_many_hashtags(self):
        r = scorer.score(GOOD + " #a #b")
        self.assertIn("hashtag_count", [c.name for c in r.checks if not c.ok])


class CaptionTests(unittest.TestCase):
    def test_every_pillar_builds_valid_package(self):
        for pillar in captions.PILLARS:
            pkg = captions.build(captions.Brief(pillar, team="Arsenal", opponent="Chelsea", player="Bukayo Saka",
                                                competition="Premier League", topic="4-3-3",
                                                points=["one detail", "two detail", "three detail"]))
            self.assertLessEqual(len(pkg.hashtags), 5)
            self.assertTrue(pkg.caption.endswith("#beyondtheformation"))
            self.assertGreaterEqual(pkg.score["score"], 80, (pillar, pkg.score["fixes"]))
            self.assertLessEqual(len(text.first_line(pkg.caption)), 125)

    def test_keyword_added_to_bare_hook(self):
        pkg = captions.build(captions.Brief("breakdown", hook="What a game that was", team="Liverpool"))
        line1 = text.first_line(pkg.caption)
        self.assertIn("Liverpool", line1)
        self.assertIn("tactical analysis", line1)


class AITests(unittest.TestCase):
    def test_ai_output_is_enforced(self):
        from btf_seo import ai
        payload = {"hook_options": ["How Arsenal broke the press"], "on_screen_text": "Arsenal's press-beating 2-3-5",
                   "caption_without_hashtags": "How Arsenal broke Chelsea's high press | tactical analysis\n\nSend this to a mate 📩",
                   "hashtags": ["football", "#FootballTactics", "#arsenal", "#fyp", "#beyondtheformation", "#a", "#b", "#c"],
                   "alt_text": "Tactical graphic of Arsenal's 2-3-5 shape against Chelsea's press",
                   "cover_title": "ARSENAL 2-3-5", "voiceover_opening": "This is how Arsenal beat Chelsea's press."}
        fake_resp = SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5",
                                    content=[SimpleNamespace(type="text", text=json.dumps(payload))])
        fake_client = mock.MagicMock()
        fake_client.beta.messages.create.return_value = fake_resp
        fake_mod = mock.MagicMock()
        fake_mod.Anthropic.return_value = fake_client
        with mock.patch.dict("sys.modules", {"anthropic": fake_mod}):
            pkg = ai.build(captions.Brief("breakdown", team="Arsenal", opponent="Chelsea"))
        kwargs = fake_client.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(len(pkg.hashtags), 5)
        self.assertEqual(pkg.hashtags[-1], "#beyondtheformation")
        self.assertNotIn("#football", pkg.hashtags)
        self.assertNotIn("#fyp", pkg.hashtags)
        self.assertIn("#footballtactics", pkg.hashtags)

    def test_refusal_raises(self):
        from btf_seo import ai
        fake_client = mock.MagicMock()
        fake_client.beta.messages.create.return_value = SimpleNamespace(stop_reason="refusal", content=[])
        fake_mod = mock.MagicMock()
        fake_mod.Anthropic.return_value = fake_client
        with mock.patch.dict("sys.modules", {"anthropic": fake_mod}):
            with self.assertRaises(ai.AIUnavailable):
                ai.build(captions.Brief("quiz"))


def fake_suggest(url, params=None, **kw):
    q = params["q"]
    table = {
        "inverted full back": ["inverted full back", "inverted full back explained", "inverted upside down"],
        "inverted full back explained": ["inverted full back explained", "inverted full back explained guardiola"],
    }
    return [q, table.get(q, [])]


class KeywordTests(unittest.TestCase):
    def test_research_ranks_relevant_first(self):
        with mock.patch.object(keywords, "fetch_json", side_effect=fake_suggest):
            ks = keywords.research(["inverted full back"])
        phrases = [k.phrase for k in ks]
        self.assertIn("full back", phrases[0])
        self.assertLess(phrases.index("inverted full back explained"), phrases.index("inverted upside down"))

    def test_intents(self):
        self.assertEqual(keywords.classify_intent("arsenal tactics fc 26"), "gaming")
        self.assertEqual(keywords.classify_intent("how does arsenal press"), "question")
        self.assertEqual(keywords.classify_intent("arsenal tactics this season"), "analysis")
        self.assertEqual(keywords.classify_intent("arsenal vs chelsea"), "versus")

    def test_network_errors_are_collected(self):
        from btf_seo.net import FetchError
        errors = []
        with mock.patch.object(keywords, "fetch_json", side_effect=FetchError("boom")):
            self.assertEqual(keywords.research(["x"], errors=errors), [])
        self.assertTrue(errors)


RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Arteta explains Arsenal's new press after Chelsea win</title><description>Saka starred.</description>
<pubDate>{now}</pubDate><link>https://example.com/1</link></item>
<item><title>Aston Villa sack manager after poor start</title><description>Villa are looking.</description>
<pubDate>{now}</pubDate><link>https://example.com/2</link></item>
<item><title>Arsenal and Liverpool in title race</title><description></description>
<pubDate>{old}</pubDate><link>https://example.com/3</link></item>
</channel></rss>"""


class TrendTests(unittest.TestCase):
    def setUp(self):
        from email.utils import format_datetime
        now = dt.datetime.now(dt.timezone.utc)
        self.items = trends.parse_feed(RSS.format(now=format_datetime(now), old=format_datetime(now - dt.timedelta(days=5))), "test")

    def test_detect_ranks_recent_mentions(self):
        t = trends.detect(self.items)
        self.assertEqual(t[0].name, "Arsenal")
        names = [x.name for x in t]
        self.assertIn("Mikel Arteta", names)
        self.assertGreater(t[names.index("Arsenal")].score, t[names.index("Liverpool")].score)

    def test_ideas_pick_news_angle(self):
        ideas = trends.ideas(trends.detect(self.items), 20)
        villa = next(i for i in ideas if i["entity"] == "Aston Villa")
        self.assertIn("next manager", villa["idea"])

    def test_bad_xml(self):
        self.assertEqual(trends.parse_feed("not xml"), [])


class CalendarTests(unittest.TestCase):
    def test_big_match_takes_slot_and_exports(self):
        fx = fixtures.load_csv(DATA / "sample_fixtures.csv")
        slots = calendar_plan.build(dt.date(2026, 10, 1), 1, fx)
        self.assertEqual(len(slots), 7)
        post_match = [s for s in slots if "Arsenal vs Liverpool" in s.topic]
        self.assertTrue(post_match)
        self.assertNotIn("Brighton vs Newcastle", " ".join(s.topic for s in slots))
        ics = calendar_plan.to_ics(slots)
        self.assertEqual(ics.count("BEGIN:VEVENT"), 7)
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR"))
        self.assertIn("weekday", calendar_plan.to_csv(slots).splitlines()[0])


class AnalyticsTests(unittest.TestCase):
    def test_sample_export(self):
        posts = analytics.load_csv(str(DATA / "sample_insights.csv"))
        self.assertEqual(len(posts), 40)
        self.assertEqual({p.media_type for p in posts}, {"REEL", "CAROUSEL"})
        r = analytics.analyze(posts)
        self.assertEqual(r["posts"], 40)
        self.assertTrue(r["recommendations"])
        self.assertEqual(len(r["top"]), 5)
        self.assertIn("send_rate", r["kpis"])

    def test_csv_text_with_aliases(self):
        csv_text = "id,caption,timestamp,reach,shares,saved\n1,Guess the team quiz,2026-01-01T19:00:00,1000,20,5\n"
        posts = analytics.load_csv(csv_text)
        self.assertEqual(posts[0].pillar, "quiz")
        self.assertAlmostEqual(posts[0].metrics["send_rate"], 0.02)

    def test_missing_reach_column(self):
        with self.assertRaises(ValueError):
            analytics.load_csv("id,caption\n1,x\n")


class ProfileTests(unittest.TestCase):
    def test_double_letter_handle_flagged(self):
        r = profile.audit("@beyond_the_formationn", "Beyond The Formation | Football Tactics",
                          "⚽ Football tactics explained\n🔔 New breakdown every matchday", "https://x.y")
        handle = [c for c in r["checks"] if c["area"] == "handle"]
        self.assertFalse(handle[0]["ok"])
        self.assertTrue(all(c["ok"] for c in r["checks"] if c["area"] in ("name", "bio", "link")))
        self.assertIn("@beyondtheformation", r["suggestions"][0])


class ReportAndCliTests(unittest.TestCase):
    def test_report_html(self):
        html = report.build(profile=profile.audit(), analytics=analytics.analyze(analytics.load_csv(str(DATA / "sample_insights.csv"))))
        self.assertIn("<title>BTF SEO Report</title>", html)
        self.assertIn("What to do next", html)

    def test_cli_score_exit_codes(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(cli.main(["score", GOOD]), 0)
            self.assertEqual(cli.main(["score", "#fyp"]), 1)

    def test_cli_offline_report(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stdout"):
            out = Path(d) / "r.html"
            self.assertEqual(cli.main(["report", "--offline", "--csv", str(DATA / "sample_insights.csv"), "--out", str(out)]), 0)
            self.assertIn("Performance", out.read_text())


class WebTests(unittest.TestCase):
    def test_api_endpoints(self):
        from http.server import ThreadingHTTPServer
        from btf_seo.web import Handler
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            def post(path, body):
                req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    return json.loads(r.read())
            self.assertGreaterEqual(post("/api/score", {"caption": GOOD})["score"], 80)
            pkg = post("/api/caption", {"pillar": "explained", "topic": "false 9"})
            self.assertEqual(pkg["hashtags"][-1], "#beyondtheformation")
            self.assertEqual(len(post("/api/calendar", {"start": "2026-10-01", "weeks": 1})["slots"]), 7)
            with urllib.request.urlopen(base + "/") as r:
                self.assertIn(b"SEO Engine", r.read())
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
