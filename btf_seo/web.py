"""Local dashboard: `btf serve` → http://127.0.0.1:8787 (stdlib only)."""
import datetime as dt
import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import analytics, calendar_plan, captions, fixtures, hashtags, keywords, profile, scorer, trends

STATIC = Path(__file__).parent / "static"


def _brief(d):
    return captions.Brief(
        pillar=d.get("pillar", "breakdown"), hook=d.get("hook", ""), team=d.get("team", ""),
        opponent=d.get("opponent", ""), player=d.get("player", ""), competition=d.get("competition", ""),
        topic=d.get("topic", ""), points=[p for p in d.get("points", []) if p.strip()], notes=d.get("notes", ""))


def api_caption(d):
    brief = _brief(d)
    if d.get("ai"):
        from . import ai
        try:
            return ai.build(brief).to_dict()
        except ai.AIUnavailable as e:
            pkg = captions.build(brief).to_dict()
            pkg["warning"] = f"AI unavailable ({e}); used templates"
            return pkg
    return captions.build(brief).to_dict()


def api_score(d):
    return scorer.score(d.get("caption", ""), d.get("alt_text") or None, d.get("on_screen_text") or None).to_dict()


def api_hashtags(d):
    tags = hashtags.select(d.get("pillar", "breakdown"), d.get("text", ""), d.get("team") or None,
                           d.get("player") or None, d.get("competition") or None)
    return {"hashtags": tags, "problems": hashtags.validate(tags)}


def api_trends(_q):
    errors = []
    t = trends.detect(errors=errors)
    return {"trends": [x.to_dict() for x in t[:25]], "ideas": trends.ideas(t, 12), "errors": errors}


def api_keywords(q):
    seeds = [s.strip() for s in q.get("seed", ["football tactics"])[0].split(",") if s.strip()]
    errors = []
    ks = keywords.research(seeds, deep=q.get("deep", ["0"])[0] == "1", errors=errors)
    return {"keywords": [k.to_dict() for k in ks[:60]], "errors": errors[:5]}


def api_calendar(d):
    start = dt.date.fromisoformat(d["start"]) if d.get("start") else dt.date.today()
    fx = []
    if d.get("fixtures_csv"):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(d["fixtures_csv"])
        fx = fixtures.load_csv(f.name)
        Path(f.name).unlink()
    idea_list = []
    if d.get("use_trends"):
        idea_list = trends.ideas(trends.detect(), 20)
    slots = calendar_plan.build(start, int(d.get("weeks", 2)), fx, idea_list)
    return {"slots": [s.to_dict() for s in slots], "csv": calendar_plan.to_csv(slots), "ics": calendar_plan.to_ics(slots)}


def api_analytics(d):
    posts = analytics.load_csv(d["csv"])
    r = analytics.analyze(posts)
    return r


def api_profile(d):
    return profile.audit(d.get("handle", ""), d.get("name", ""), d.get("bio", ""), d.get("link", ""))


POST_ROUTES = {"/api/caption": api_caption, "/api/score": api_score, "/api/hashtags": api_hashtags,
               "/api/calendar": api_calendar, "/api/analytics": api_analytics, "/api/profile": api_profile}
GET_ROUTES = {"/api/trends": api_trends, "/api/keywords": api_keywords}


class Handler(BaseHTTPRequestHandler):
    server_version = "btf-seo"

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _run(self, fn, arg):
        try:
            self._send(200, fn(arg))
        except (ValueError, KeyError, RuntimeError) as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # keep the dashboard alive; show the error in the UI
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html")
        if url.path in GET_ROUTES:
            return self._run(GET_ROUTES[url.path], parse_qs(url.query))
        self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path not in POST_ROUTES:
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > 20_000_000:
            return self._send(413, {"error": "payload too large"})
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid JSON"})
        self._run(POST_ROUTES[url.path], data)

    def log_message(self, fmt, *args):
        pass


def serve(host="127.0.0.1", port=8787):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Beyond The Formation SEO dashboard → http://{host}:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
