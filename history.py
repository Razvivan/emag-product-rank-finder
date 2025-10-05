# Keyword history management for emag-product-rank-finder
import json
import os
from config import HISTORY_FILE


def save_keyword_history(keywords):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(keywords, f)


def load_keyword_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
