import streamlit as st
import pandas as pd
import time
from emag_rank import extract_pd_code, build_search_url, fetch_html, parse_cards, filter_cards, find_target

st.set_page_config(page_title="eMAG Product Rank Finder", layout="wide")
st.title("eMAG Product Rank Finder")

with st.form("input_form"):
    product_url = st.text_input("Product URL", "https://www.emag.ro/purificator-de-aer-smart-levoit-core-300s-wi-fi-filtru-3-in-1-true-hepa-carbon-activ-senzor-calitate-aer-mod-auto-alexa-google-home-panou-comanda-touch-screen-control-remote-alb-core300s/pd/DPN7K9MBM/")
    keywords = st.text_area("Keywords (comma or newline separated)", "levoit core 300s, purificator aer levoit, core300s")
    pages = st.number_input("Pages to search per keyword (0=auto)", min_value=0, max_value=20, value=1)
    unbounded_cap = st.number_input("Max pages if auto", min_value=1, max_value=80, value=10)
    delay_sec = st.number_input("Delay between requests (seconds)", min_value=1.0, max_value=20.0, value=8.0)
    strict_grid = st.checkbox("Strict grid filtering", value=True)
    ignore_sponsored = st.checkbox("Ignore sponsored/promoted", value=True)
    debug = st.checkbox("Show debug info", value=False)
    submit = st.form_submit_button("Run Analysis")

if submit:
    st.info("Running analysis. Please solve any CAPTCHAs in the browser window if prompted.")
    target_pd_code = extract_pd_code(product_url)
    kw_list = [kw.strip() for kw in keywords.replace("\n", ",").split(",") if kw.strip()]
    results = []
    progress_bar = st.progress(0)
    for i, keyword in enumerate(kw_list):
        rank_global = 0
        found = False
        for page in range(1, pages + 1 if pages > 0 else unbounded_cap + 1):
            search_url = build_search_url(keyword, page)
            html = fetch_html(search_url, {}, delay_sec=delay_sec)
            cards = parse_cards(html)
            filtered_cards = filter_cards(cards, strict_grid, ignore_sponsored)
            if debug:
                st.write(f"Keyword: {keyword}, Page: {page}, Filtered cards: {len(filtered_cards)}")
            rank_global += len(filtered_cards)
            position_on_page = find_target(filtered_cards, target_pd_code)
            if position_on_page:
                filtered_count = len(filtered_cards)
                margin_error = max(2, int(0.05 * filtered_count))
                results.append({
                    "Keyword": keyword,
                    "Page": page,
                    "Position on Page": f"{position_on_page} ±{margin_error}",
                    "Global Rank": f"{rank_global - len(filtered_cards) + position_on_page} ±{margin_error}",
                    "Title": filtered_cards[position_on_page - 1]["title"],
                    "Result URL": filtered_cards[position_on_page - 1]["url_abs"],
                    "Page URL": search_url,
                    "Promoted": filtered_cards[position_on_page - 1]["is_promoted"],
                    "Sponsored": filtered_cards[position_on_page - 1]["is_sponsored"],
                    "Product Code": target_pd_code,
                })
                found = True
                break
            if not cards:
                break
            time.sleep(delay_sec)
        progress_bar.progress((i + 1) / len(kw_list))
    if results:
        df = pd.DataFrame(results)
        st.success("Results:")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "emag_results.csv", "text/csv")
    else:
        st.warning("No results found for the given keywords.")
