"""Shared helpers for the BTF SEO tools."""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "keywords.json"
MAX_HASHTAGS = 5


def load_keywords(path=DATA):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def to_hashtag(text):
    """'Man City' -> '#mancity'."""
    return "#" + re.sub(r"[^0-9a-z]", "", text.lower())


def extract_hashtags(caption):
    return re.findall(r"#\w+", caption.lower())
