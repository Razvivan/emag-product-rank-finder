# Basic error reporting for emag-product-rank-finder
import streamlit as st

def show_error_report(errors):
    if errors:
        st.error("Errors encountered during analysis:")
        for err in errors:
            st.write(f"- {err}")
    else:
        st.success("No errors encountered.")
