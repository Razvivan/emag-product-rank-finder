"""
README:

Instalare:
    pip install requests beautifulsoup4 lxml rich

Exemple de rulare:
    python emag_rank.py --product-url "https://www.emag.ro/.../pd/DPN7K9MBM/" --keywords "core300s" --pages 1 --debug
    python emag_rank.py --product-url "https://www.emag.ro/.../pd/DPN7K9MBM/" --keywords "purificator aer, filtru hepa h13 purificator" --pages 0 --unbounded-cap 80 --strict-grid --ignore-sponsored --csv rezultat.csv
"""

import argparse
import csv
import random
import re
import time
import unicodedata
import urllib.parse
from typing import List, Dict, Optional, Tuple

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress

import os

console = Console()

# Constants
BASE_SEARCH_URL = "https://www.emag.ro/search/{kw_urlencoded}?ref=effective_search"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]
HEADERS = {
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Selenium helper
def get_chrome_driver(headless=True):
    chrome_options = Options()
    # Run in visible mode for manual CAPTCHA solving
    # if headless:
    #     chrome_options.add_argument('--headless')
    #     chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--lang=ro')
    chrome_options.add_argument('--user-agent=' + random.choice(USER_AGENTS))
    # Use local ChromeDriver if available
    driver_path = os.environ.get('CHROMEDRIVER_PATH', 'chromedriver.exe')
    try:
        driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    except TypeError:
        # For Selenium 4+, executable_path is deprecated, fallback to default
        driver = webdriver.Chrome(options=chrome_options)
    except WebDriverException:
        driver = webdriver.Chrome(options=chrome_options)
    return driver

def fetch_html_selenium(url: str, delay_sec: float = 2.0) -> str:
    driver = get_chrome_driver(headless=True)
    try:
        driver.get(url)
        time.sleep(delay_sec)  # Wait for page to load
        input("[yellow]If you see a CAPTCHA in the browser, please solve it now, then press Enter here to continue scraping...")
        html = driver.page_source
    finally:
        driver.quit()
    return html

# Helper functions
def extract_pd_code(product_url: str) -> str:
    match = re.search(r"/pd/([A-Za-z0-9]+)/", product_url)
    if not match:
        raise ValueError("Invalid product URL. Could not extract pd_code.")
    return match.group(1)

def build_search_url(keyword: str, page: int) -> str:
    encoded_keyword = urllib.parse.quote(keyword)
    return f"{BASE_SEARCH_URL.format(kw_urlencoded=encoded_keyword)}&page={page}"

def fetch_html(url: str, headers: dict, proxy: Optional[str] = None, delay_sec: float = 2.0) -> str:
    # Use Selenium instead of requests
    try:
        html = fetch_html_selenium(url, delay_sec=delay_sec)
        return html
    except Exception as e:
        console.print(f"[red]Error fetching URL {url} with Selenium: {e}")
        raise RuntimeError(f"Failed to fetch URL {url} with Selenium.")

def parse_cards(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    cards = []
    # Broaden to match all product card variants
    product_grid = soup.find("section", id=re.compile(r"card_grid|main-container|search-results"))
    if not product_grid:
        product_grid = soup.find("main")
    # Match all possible product card classes
    card_classes = ["card-item", "card-v2", "product-card", "product-container"]
    product_containers = []
    if product_grid:
        for cls in card_classes:
            product_containers.extend(product_grid.find_all("div", class_=re.compile(cls)))
    else:
        for cls in card_classes:
            product_containers.extend(soup.find_all("div", class_=re.compile(cls)))

    # Remove duplicates
    seen = set()
    unique_containers = []
    for c in product_containers:
        if id(c) not in seen:
            unique_containers.append(c)
            seen.add(id(c))
    product_containers = unique_containers

    for idx, container in enumerate(product_containers, start=1):
        link = container.find("a", href=re.compile(r"/pd/[A-Za-z0-9]+/"))
        if not link:
            continue
        pd_code_match = re.search(r"/pd/([A-Za-z0-9]+)/", link["href"])
        if not pd_code_match:
            continue
        pd_code = pd_code_match.group(1)
        # Try to get the product title from the card or link
        title = ""
        title_tag = container.find("h2") or container.find("h3")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            title = link.get("title", link.get_text("").strip())
        url_abs = urllib.parse.urljoin("https://www.emag.ro/", link["href"])
        is_promoted = bool(container.find(string=re.compile(r"promovat|badge|cmp|sponsor", re.I)))
        is_sponsored = bool(container.find(string=re.compile(r"sponsored|sponsorizat|reclama", re.I)))
        console.print(f"[debug] Card idx={idx}, pd_code={pd_code}, title={title}, promoted={is_promoted}, sponsored={is_sponsored}")
        cards.append({
            "idx_on_page": idx,
            "pd_code": pd_code,
            "title": title,
            "url_abs": url_abs,
            "is_promoted": is_promoted,
            "is_sponsored": is_sponsored,
        })
    return cards

def filter_cards(cards: List[Dict], strict_grid: bool, ignore_sponsored: bool) -> List[Dict]:
    filtered = cards
    # Only keep cards with a valid pd_code and a non-empty title (strict grid)
    filtered = [card for card in filtered if card["pd_code"] and card["title"].strip()]
    if ignore_sponsored:
        filtered = [card for card in filtered if not (card["is_promoted"] or card["is_sponsored"])]
    # Remove any fallback logic that could include unrelated links
    # Only keep cards that have idx_on_page in strict sequence (no gaps)
    filtered = sorted(filtered, key=lambda c: c["idx_on_page"])
    # Debugging output for filtered cards
    console.print(f"[debug] Strictly filtered cards count: {len(filtered)}")
    return filtered

def find_target(cards_filtered: List[Dict], target_pd_code: str) -> Optional[int]:
    for idx, card in enumerate(cards_filtered, start=1):
        if card["pd_code"] == target_pd_code:
            # Debugging output for target match
            console.print(f"[debug] Target found at idx={idx}, pd_code={card['pd_code']}")
            return idx
    # Debugging output if target not found
    console.print("[debug] Target not found in filtered cards")
    return None

def main():
    parser = argparse.ArgumentParser(description="eMAG Product Rank Finder")
    parser.add_argument("--product-url", required=True, help="URL complet către pagina produsului eMAG")
    parser.add_argument("--keywords", required=True, help="Listă de keyword-uri separate prin virgulă sau newline")
    parser.add_argument("--pages", type=int, default=0, help="Câte pagini să parcurgă pentru fiecare keyword")
    parser.add_argument("--unbounded-cap", type=int, default=80, help="Limita maximă de pagini când --pages=0")
    parser.add_argument("--delay-sec", type=float, default=8.0, help="Întârziere între request-uri (Selenium)")
    parser.add_argument("--strict-grid", action="store_true", help="Numără doar cardurile de produs reale")
    parser.add_argument("--ignore-sponsored", action="store_true", help="Ignoră rezultatele marcate ca Promovat/Sponsorizat")
    parser.add_argument("--csv", help="Cale fișier pentru export CSV")
    parser.add_argument("--debug", action="store_true", help="Printează informații de debug")
    args = parser.parse_args()

    target_pd_code = extract_pd_code(args.product_url)
    console.print(f"[*] Identitate produs: pd_code={target_pd_code}")

    keywords = [kw.strip() for kw in args.keywords.split(",")]
    results = []

    with Progress() as progress:
        task = progress.add_task("[cyan]Searching eMAG...", total=len(keywords))

        for keyword in keywords:
            rank_global = 0
            for page in range(1, args.pages + 1 if args.pages > 0 else args.unbounded_cap + 1):
                search_url = build_search_url(keyword, page)
                html = fetch_html(search_url, HEADERS, delay_sec=args.delay_sec)
                # Save raw HTML for inspection (only first page, first keyword)
                if page == 1 and keyword == keywords[0]:
                    with open(f"debug_emag_search_page.html", "w", encoding="utf-8") as f:
                        f.write(html)
                        console.print("[yellow]Saved raw HTML to debug_emag_search_page.html for inspection.")
                cards = parse_cards(html)
                filtered_cards = filter_cards(cards, args.strict_grid, args.ignore_sponsored)

                if args.debug:
                    console.print(f"[debug] Page {page}: {len(filtered_cards)} rezultate filtrate")

                rank_global += len(filtered_cards)
                position_on_page = find_target(filtered_cards, target_pd_code)

                if position_on_page:
                    results.append({
                        "keyword": keyword,
                        "page": page,
                        "position_on_page": position_on_page,
                        "rank_global": rank_global - len(filtered_cards) + position_on_page,
                        "result_title": filtered_cards[position_on_page - 1]["title"],
                        "result_url": filtered_cards[position_on_page - 1]["url_abs"],
                        "page_url": search_url,
                        "pd_code": target_pd_code,
                        "promoted_html": filtered_cards[position_on_page - 1]["is_promoted"],
                        "sponsored_html": filtered_cards[position_on_page - 1]["is_sponsored"],
                    })
                    break

                if not cards:
                    break

                # Add random delay to reduce bot detection
                import random
                sleep_time = args.delay_sec + random.uniform(2, 6)
                console.print(f"[yellow]Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)

            progress.update(task, advance=1)

    def get_margin(strict_grid, filtered_count):
        if strict_grid:
            return 1
        return max(2, int(0.05 * filtered_count))

    def show_margin_warning(margin):
        if margin > 3:
            console.print(f"[yellow]Warning: Large margin for error (±{margin}) indicates possible grid anomalies or ads. Result may be less precise.")

    if args.csv:
        with open(args.csv, "w", newline="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "keyword", "page", "position_on_page", "rank_global", "result_title", "result_url", "page_url", "pd_code", "promoted_html", "sponsored_html", "position_margin_error", "rank_margin_error"
            ])
            writer.writeheader()
            for result in results:
                filtered_count = max(result['position_on_page'], 1)
                margin_error = get_margin(args.strict_grid, filtered_count)
                result_copy = result.copy()
                result_copy["position_margin_error"] = f"{result['position_on_page']} ±{margin_error}"
                result_copy["rank_margin_error"] = f"{result['rank_global']} ±{margin_error}"
                writer.writerow(result_copy)

    for result in results:
        filtered_count = max(result['position_on_page'], 1)
        margin_error = get_margin(args.strict_grid, filtered_count)
        position_with_margin = f"{result['position_on_page']} ±{margin_error}"
        rank_with_margin = f"{result['rank_global']} ±{margin_error}"
        show_margin_warning(margin_error)

        # Count excluded promoted/sponsored cards for this page
        # Re-parse the HTML for this result's page
        html = fetch_html(result['page_url'], HEADERS, delay_sec=0)
        all_cards = parse_cards(html)
        excluded_count = len([card for card in all_cards if card['is_promoted'] or card['is_sponsored']])

        console.print(
            f"[green]Keyword:[/green] {result['keyword']}\n"
            f"[blue]Page:[/blue] {result['page']}\n"
            f"[blue]Position on Page:[/blue] {position_with_margin}\n"
            f"[blue]Global Rank:[/blue] {rank_with_margin}\n"
            f"[blue]Title:[/blue] {result['result_title']}\n"
            f"[blue]Result URL:[/blue] {result['result_url']}\n"
            f"[blue]Page URL:[/blue] {result['page_url']}\n"
            f"[blue]Promoted:[/blue] {result['promoted_html']}\n"
            f"[blue]Sponsored:[/blue] {result['sponsored_html']}\n"
            f"[blue]Product Code:[/blue] {result['pd_code']}\n"
            f"[magenta]Excluded promoted/sponsored cards:[/magenta] {excluded_count}\n"
        )

if __name__ == "__main__":
    main()