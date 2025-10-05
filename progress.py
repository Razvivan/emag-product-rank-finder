# Enhanced progress bar details for emag-product-rank-finder
import streamlit as st

def show_progress(current_keyword, current_page, total_tasks, task_idx):
    st.progress(task_idx / total_tasks)
    st.write(f"Processing keyword: {current_keyword}, page: {current_page}")
