# Utility functions for emag-product-rank-finder
import datetime
import pandas as pd

def deduplicate_cards(cards):
    """Remove exact duplicates (same pd_code, title, promoted, sponsored)."""
    seen = set()
    unique = []
    for card in cards:
        key = (card["pd_code"], card["title"], card["is_promoted"], card["is_sponsored"])
        if key not in seen:
            seen.add(key)
            unique.append(card)
    return unique

def add_timestamp(df):
    """Add a timestamp column to a DataFrame."""
    df["Timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df

def filter_columns(df, columns):
    """Return DataFrame with selected columns only."""
    return df[columns]

def get_version():
    return "v0.02"

# Add more utility functions as needed
