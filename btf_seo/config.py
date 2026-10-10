"""Settings and data loading.

Data lives in ``data/`` at the repo root (override with ``BTF_DATA_DIR``).
Secrets come from environment variables only:

- ``ANTHROPIC_API_KEY``: optional, enables the AI caption writer
- ``IG_ACCESS_TOKEN``: optional, Instagram API (Instagram Login) token for analytics
- ``FOOTBALL_DATA_TOKEN``: optional, football-data.org token for fixtures
"""
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def data_dir():
    return Path(os.environ.get("BTF_DATA_DIR", REPO_ROOT / "data"))


def cache_dir():
    d = Path(os.environ.get("BTF_CACHE_DIR", Path.home() / ".cache" / "btf_seo"))
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Settings:
    ai_model: str = field(default_factory=lambda: os.environ.get("BTF_AI_MODEL", "claude-opus-5-5"))
    ig_token: str = field(default_factory=lambda: os.environ.get("IG_ACCESS_TOKEN", ""))
    ig_graph_version: str = field(default_factory=lambda: os.environ.get("IG_GRAPH_VERSION", "v23.0"))
    football_data_token: str = field(default_factory=lambda: os.environ.get("FOOTBALL_DATA_TOKEN", ""))


def settings():
    return Settings()


def _load(name):
    with open(data_dir() / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def keywords():
    return _load("keywords.json")


@lru_cache(maxsize=None)
def entities():
    return _load("entities.json")


def reload():
    keywords.cache_clear()
    entities.cache_clear()
