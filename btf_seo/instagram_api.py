"""Instagram API (Instagram Login) client for pulling your own posts + insights.

Setup (one-time): create a Meta app, add the Instagram product with "Instagram API with Instagram
Login", connect @beyond_the_formationn (must be a Professional account), and generate a long-lived
token with instagram_business_basic + instagram_business_manage_insights. Put it in IG_ACCESS_TOKEN.
"""
from . import config
from .analytics import Post, media_kind, parse_time
from .net import FetchError, fetch_json

MEDIA_FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"
METRICS = {
    "REELS": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "ig_reels_avg_watch_time"],
    "FEED": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
}
FALLBACK_METRICS = ["reach", "likes", "comments", "shares", "saved"]


class InstagramAPI:
    def __init__(self, token=None, version=None):
        s = config.settings()
        self.token = token or s.ig_token
        if not self.token:
            raise RuntimeError("Set IG_ACCESS_TOKEN (see btf_seo/instagram_api.py for setup)")
        self.base = f"https://graph.instagram.com/{version or s.ig_graph_version}"

    def _get(self, path_or_url, **params):
        url = path_or_url if path_or_url.startswith("http") else f"{self.base}/{path_or_url.lstrip('/')}"
        if "access_token=" not in url:
            params["access_token"] = self.token
        # ttl=0: never cache authenticated responses on disk.
        return fetch_json(url, params=params, ttl=0, timeout=30)

    def account(self):
        data = self._get("me", fields="user_id,username,name,account_type,followers_count,follows_count,media_count")
        try:
            data.update(self._get("me", fields="biography,website"))
        except FetchError:
            pass
        return data

    def media(self, limit=50):
        out, url, params = [], "me/media", {"fields": MEDIA_FIELDS, "limit": min(limit, 50)}
        while url and len(out) < limit:
            page = self._get(url, **params)
            out += page.get("data", [])
            url, params = (page.get("paging") or {}).get("next"), {}
        return out[:limit]

    def insights(self, media):
        kind = "REELS" if media.get("media_product_type") == "REELS" else "FEED"
        for metrics in (METRICS[kind], FALLBACK_METRICS):
            try:
                data = self._get(f"{media['id']}/insights", metric=",".join(metrics))
                break
            except FetchError:
                continue
        else:
            return {}
        values = {}
        for m in data.get("data", []):
            if m.get("values"):
                values[m["name"]] = m["values"][0].get("value", 0)
            elif m.get("total_value"):
                values[m["name"]] = m["total_value"].get("value", 0)
        return values

    def posts(self, limit=50):
        posts = []
        for m in self.media(limit):
            ins = self.insights(m)
            kind = "REEL" if m.get("media_product_type") == "REELS" else m.get("media_type", "")
            posts.append(Post(
                id=m["id"], caption=m.get("caption", ""), timestamp=parse_time(m.get("timestamp")),
                media_type=media_kind(kind), permalink=m.get("permalink", ""),
                reach=ins.get("reach", 0), views=ins.get("views", 0),
                likes=ins.get("likes", m.get("like_count", 0)), comments=ins.get("comments", m.get("comments_count", 0)),
                shares=ins.get("shares", 0), saves=ins.get("saved", 0),
            ).compute())
        return posts
