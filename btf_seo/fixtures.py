"""Match fixtures: from a CSV you maintain or the football-data.org API (free token)."""
import csv
import datetime as dt
from dataclasses import asdict, dataclass

from . import config
from .net import fetch_json
from .text import find_entities

API = "https://api.football-data.org/v4/matches"
COMPETITION_NAMES = {"PL": "Premier League", "CL": "Champions League", "PD": "La Liga", "SA": "Serie A",
                     "BL1": "Bundesliga", "FL1": "Ligue 1", "EL": "Europa League", "PPL": "Primeira Liga",
                     "WC": "World Cup", "EC": "Euros", "FAC": "FA Cup"}


@dataclass
class Fixture:
    date: dt.date
    home: str
    away: str
    competition: str = ""
    kickoff: str = ""

    @property
    def big(self):
        """Both sides are 'big' clubs, or it's a Champions League knockout-level name."""
        bigs = {c["name"] for c in config.entities()["clubs"] if c.get("big")}
        names = {n for n, k, _ in find_entities(f"{self.home} {self.away}") if k == "club"}
        return len(names & bigs) >= 2

    def title(self):
        return f"{self.home} vs {self.away}"

    def to_dict(self):
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["big"] = self.big
        return d


def load_csv(path):
    """CSV columns: date (YYYY-MM-DD), home, away, competition (optional), kickoff (optional)."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("date") or not row.get("home"):
                continue
            out.append(Fixture(dt.date.fromisoformat(row["date"][:10]), row["home"], row.get("away", ""),
                               row.get("competition", ""), row.get("kickoff", "")))
    return out


def from_api(start, days=14, token=None):
    token = token or config.settings().football_data_token
    if not token:
        raise RuntimeError("Set FOOTBALL_DATA_TOKEN (free at football-data.org) or pass a fixtures CSV")
    end = start + dt.timedelta(days=days)
    data = fetch_json(API, params={"dateFrom": start.isoformat(), "dateTo": end.isoformat()},
                      headers={"X-Auth-Token": token}, ttl=6 * 3600)
    out = []
    for m in data.get("matches", []):
        when = dt.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        code = (m.get("competition") or {}).get("code", "")
        out.append(Fixture(when.date(), m["homeTeam"].get("shortName") or m["homeTeam"]["name"],
                           m["awayTeam"].get("shortName") or m["awayTeam"]["name"],
                           COMPETITION_NAMES.get(code, (m.get("competition") or {}).get("name", "")),
                           when.strftime("%H:%M UTC")))
    return out
