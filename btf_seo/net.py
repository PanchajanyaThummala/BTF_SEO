"""Tiny HTTP layer (stdlib only) with an on-disk cache so repeated runs stay polite."""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import cache_dir

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) btf-seo/1.0"


class FetchError(RuntimeError):
    pass


def _cache_path(url):
    return cache_dir() / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".cache")


def fetch(url, params=None, headers=None, ttl=3600, timeout=15):
    """GET ``url`` and return the body as text. Cached for ``ttl`` seconds (0 disables)."""
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params)}"
    path = _cache_path(url)
    if ttl and path.exists() and time.time() - path.stat().st_mtime < ttl:
        return path.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise FetchError(f"HTTP {e.code} for {url.split('?')[0]}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"Network error for {url.split('?')[0]}: {e}") from e
    if ttl:
        path.write_text(body, encoding="utf-8")
    return body


def fetch_json(url, params=None, headers=None, ttl=3600, timeout=15):
    body = fetch(url, params=params, headers=headers, ttl=ttl, timeout=timeout)
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"Invalid JSON from {url.split('?')[0]}") from e
