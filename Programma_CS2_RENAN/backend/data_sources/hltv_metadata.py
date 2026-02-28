import os
import sys
from datetime import date

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_metadata")

# F6-06: sys.path bootstrap — required only when this file is executed directly as a script.
# With proper package installation (pip install -e .) this block is a no-op.
# Technical debt: remove when entrypoints are configured in pyproject.toml/setup.py.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from playwright.sync_api import expect, sync_playwright

# --- Configuration ---
BASE_URL = "https://www.hltv.org"
DEBUG_HTML_PATH = os.path.join(os.path.dirname(project_root), "tmp", "hltv_debug.html")


def debug_save_page_source(start_date: date, end_date: date):
    """
    A simple function to navigate to a URL using Playwright and save the page source.
    """
    url = f"{BASE_URL}/results?startDate={start_date.isoformat()}&endDate={end_date.isoformat()}"
    logger.info("[DEBUG] Fetching URL for debugging: %s", url)  # F6-15

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _execute_page_save(page, browser, url)


def _execute_page_save(page, browser, url):
    try:
        logger.info("[DEBUG] Navigating to page...")  # F6-15
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        expect(page.locator("body")).to_be_visible(timeout=60000)
        _write_content(page.content())
    except Exception as e:
        _handle_save_error(page, e)
    finally:
        logger.info("[DEBUG] Closing browser.")  # F6-15
        browser.close()


def _write_content(content):
    os.makedirs(os.path.dirname(DEBUG_HTML_PATH), exist_ok=True)
    with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("[SUCCESS] Saved page HTML for debugging to: %s", DEBUG_HTML_PATH)  # F6-15


def _handle_save_error(page, e):
    logger.error("[ERROR] An error occurred during the debug save process: %s", e)  # F6-15
    try:
        with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(page.content())
        logger.info("[INFO] Saved partial page content on error to: %s", DEBUG_HTML_PATH)  # F6-15
    except Exception as e:
        logger.warning("Failed to save partial page content: %s", e)  # F6-15


if __name__ == "__main__":
    logger.info("[DEBUG] --- Running simple Playwright page source debug script ---")  # F6-15
    year = 2023
    month = 2  # February 2023, a month with a major tournament

    start_date = date(year, month, 1)
    end_date = date(year, month, 28)

    debug_save_page_source(start_date, end_date)
