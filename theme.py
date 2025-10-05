# UI theme management for emag-product-rank-finder
import streamlit as st

def set_theme(theme):
    if theme == "dark":
        st.markdown("""
            <style>
            body { background-color: #222; color: #eee; }
            .stApp { background-color: #222; }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            body { background-color: #fff; color: #222; }
            .stApp { background-color: #fff; }
            </style>
        """, unsafe_allow_html=True)
