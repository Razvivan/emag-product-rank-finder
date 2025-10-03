
import streamlit as st
import pandas as pd
import time
import urllib.parse
from emag_rank import extract_pd_code, build_search_url, fetch_html, fetch_html_selenium, parse_cards, filter_cards, find_target

st.set_page_config(page_title="eMAG Product Rank Finder", layout="wide")

# Sidebar for input
with st.sidebar:
    st.title("🔍 eMAG Rank Finder")
    st.markdown("""
    <style>
    .sidebar .sidebar-content {width: 350px;}
    </style>
    """, unsafe_allow_html=True)
    with st.expander("Input Parameters", expanded=True):
        product_url = st.text_input("Product URL", "https://www.emag.ro/purificator-de-aer-smart-levoit-core-300s-wi-fi-filtru-3-in-1-true-hepa-carbon-activ-senzor-calitate-aer-mod-auto-alexa-google-home-panou-comanda-touch-screen-control-remote-alb-core300s/pd/DPN7K9MBM/")
        keywords = st.text_area("Keywords (comma or newline separated)", "levoit core 300s, purificator aer levoit, core300s")
        pages = st.number_input("Pages to search per keyword (0=auto)", min_value=0, max_value=20, value=1)
        unbounded_cap = st.number_input("Max pages if auto", min_value=1, max_value=80, value=10)
        delay_sec = st.number_input("Delay between requests (seconds)", min_value=1.0, max_value=20.0, value=8.0)
        strict_grid = st.checkbox("Strict grid filtering", value=True)
        ignore_sponsored = st.checkbox("Ignore sponsored/promoted", value=True)
        debug = st.checkbox("Show debug info", value=False)
        st.markdown("**View Type:**")
        use_grid = st.checkbox("Analyze Grid View", value=True)
        use_list = st.checkbox("Analyze List View", value=False)
        submit = st.button("Run Analysis", use_container_width=True)

st.markdown("""
<style>
.main .block-container {padding-top: 2rem;}
.stDataFrame {background: #f8f9fa; border-radius: 8px;}
.stButton>button {background: #0056b3; color: white; border-radius: 6px;}
</style>
""", unsafe_allow_html=True)

st.header("eMAG Product Rank Finder", divider="rainbow")
st.markdown("""
Easily check where your product appears for multiple keywords on eMAG. 
**Instructions:** Enter the product URL and keywords in the sidebar, adjust options, and click **Run Analysis**. Results will appear below and can be downloaded as CSV.
""")

if 'submit' in locals() and submit:
    st.info("Running analysis. Please solve any CAPTCHAs in the browser window if prompted.")
    target_pd_code = extract_pd_code(product_url)
    kw_list = [kw.strip() for kw in keywords.replace("\n", ",").split(",") if kw.strip()]
    results = []
    progress_bar = st.progress(0)
    total_tasks = len(kw_list) * ((1 if use_grid else 0) + (1 if use_list else 0))
    task_idx = 0
    for i, keyword in enumerate(kw_list):
        for view_type, ref in [("Grid", "grid"), ("List", "list")]:
            if (view_type == "Grid" and not use_grid) or (view_type == "List" and not use_list):
                continue
            for page in range(1, pages + 1 if pages > 0 else unbounded_cap + 1):
                search_url = f"https://www.emag.ro/search/{urllib.parse.quote(keyword)}?ref={ref}&page={page}"
                if view_type == "Grid":
                    html = fetch_html_selenium(search_url, delay_sec=delay_sec, force_grid=True)
                else:
                    html = fetch_html(search_url, {}, delay_sec=delay_sec)
                cards = parse_cards(html)
                filtered_cards = filter_cards(cards, strict_grid, ignore_sponsored)
                if debug:
                    st.write(f"[{view_type}] Keyword: {keyword}, Page: {page}, Filtered cards: {len(filtered_cards)}")
                # Find all occurrences of the target product
                matches = [card for card in filtered_cards if card["pd_code"] == target_pd_code]
                # Deduplicate only exact matches (same pd_code, title, promoted, sponsored)
                seen = set()
                unique_matches = []
                for card in matches:
                    key = (card["pd_code"], card["title"], card["is_promoted"], card["is_sponsored"])
                    if key not in seen:
                        seen.add(key)
                        unique_matches.append(card)
                for match_idx, card in enumerate(unique_matches, start=1):
                    margin_error = max(2, int(0.05 * len(filtered_cards)))
                    result = {
                        "Keyword": keyword,
                        "View": view_type,
                        "Page": page,
                        "Occurrence": match_idx,
                        "Position on Page": f"{card['idx_on_page']} ±{margin_error}",
                        "Global Rank": f"{card['idx_on_page']} ±{margin_error}",
                        "Title": card["title"],
                        "Result URL": card["url_abs"],
                        "Page URL": search_url,
                        "Promoted": card["is_promoted"],
                        "Sponsored": card["is_sponsored"],
                        "Product Code": target_pd_code,
                    }
                    results.append(result)
                if not cards:
                    break
                time.sleep(delay_sec)
            task_idx += 1
            progress_bar.progress(task_idx / total_tasks)
    if results:
        df = pd.DataFrame(results)
        st.success("Results:")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "emag_results.csv", "text/csv", use_container_width=True)
    else:
        st.warning("No results found for the given keywords.")
