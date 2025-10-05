# CSV export logic for emag-product-rank-finder
import pandas as pd
from utils import filter_columns, add_timestamp
from config import DEFAULT_COLUMNS

def export_to_csv(df, columns=None, filename="emag_results.csv"):
    if columns is None:
        columns = DEFAULT_COLUMNS
    df = filter_columns(df, columns)
    df = add_timestamp(df)
    df.to_csv(filename, index=False, encoding="utf-8")
    return filename
