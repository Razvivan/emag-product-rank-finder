# Badge/promotion summary for emag-product-rank-finder
import pandas as pd
import streamlit as st

def show_badge_summary(df):
    summary = df.groupby(["Keyword"]).agg({
        "Promoted": "sum",
        "Sponsored": "sum"
    }).reset_index()
    st.write("### Badge/Promotion Summary")
    st.dataframe(summary)
