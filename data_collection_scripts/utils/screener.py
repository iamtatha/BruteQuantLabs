"""
BruteQuantLabs Screener.in Fundamentals Scraper
- Persistent browser session (no re-login)
- Human-like behavior (random delays, scrolling)
- Stores data in JSON format
- Production-ready error handling
"""

import json
import time
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import re
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('screener_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))



"""
BruteQuantLabs Screener.in Fundamentals Scraper
- Persistent browser session (no re-login)
- Human-like behavior (random delays, scrolling)
- Stores data in JSON format
- Production-ready error handling
"""


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - '
           '%(filename)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('screener_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScreenerScraper:
    """
    Persistent Screener.in scraper with session management.
    
    Usage:
        scraper = ScreenerScraper(headless=False)  # headless=True for background
        data = scraper.scrape_stock('RELIANCE')
        scraper.close()  # Optional; keeps browser open by default
    """
    
    def __init__(self, headless: bool = False, data_dir: str = 'database/demo_data/screener_data'):
        """
        Initialize scraper with persistent session.
        
        Args:
            headless: Run Chrome in headless mode (no visible window)
            data_dir: Directory to store JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = 'https://www.screener.in'
        self.driver = None
        self.headless = headless
        
        # Session state tracking
        self.session_file = self.data_dir / 'session_state.json'
        self.last_activity = time.time()
        
        self._init_driver()
        logger.info(f"Scraper initialized. Data directory: {self.data_dir}")
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with human-like settings."""
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Human-like settings
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(15)
        logger.info("WebDriver initialized")
    
    def _human_delay(self, min_sec: float = 0.5, max_sec: float = 3.0):
        """Random delay to mimic human behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _scroll_page(self):
        """Random scrolling to look human-like."""
        scroll_amount = random.randint(200, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self._human_delay(0.3, 1.0)
    
    def _expand_all_rows(self):
        logger.info("Expanding collapsible rows...")

        try:
            clicked = set()
            max_attempts = 35

            for _ in range(max_attempts):
                expanded = False

                buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@onclick, 'Company.showSchedule')]"
                )

                logger.info(f"Found {len(buttons)} expandable buttons")

                for btn in buttons:
                    try:
                        onclick = btn.get_attribute("onclick")
                        text = btn.text.strip()

                        # Skip already clicked
                        if onclick in clicked:
                            continue

                        if not btn.is_displayed():
                            continue

                        # Scroll + click
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn
                        )
                        self._human_delay(0.3, 0.8)

                        self.driver.execute_script("arguments[0].click();", btn)

                        logger.info(f"Expanded: {text}")

                        clicked.add(onclick)
                        expanded = True

                        self._human_delay(1.5, 2.5)
                        break

                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        logger.debug(f"Click failed: {e}")
                        continue

                if not expanded:
                    logger.info("All rows expanded")
                    break

        except Exception as e:
            logger.warning(f"Error expanding rows: {str(e)}")



    def scrape_stock(self, stock_code: str, force_refresh: bool = False, keep_browser_open: bool = True) -> Optional[Dict]:
        """
        Scrape fundamentals for a single stock.
        
        Args:
            stock_code: NSE stock symbol (e.g., 'RELIANCE', 'INFY', 'SBIN')
            force_refresh: Ignore cached data and fetch fresh
            keep_browser_open: Keep browser open after scraping (default: True)
        
        Returns:
            Dictionary with stock fundamentals or None if failed
        """
        stock_code = stock_code.upper()
        logger.info(f"Scraping {stock_code}...")
        
        # Check cache first
        cached_data = self._load_cached_data(stock_code)
        if cached_data and not force_refresh:
            logger.info(f"{stock_code} found in cache (age: {cached_data.get('cache_age_days')}d)")
            return cached_data
        
        try:
            # Navigate to stock page
            url = f"{self.base_url}/company/{stock_code}/"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)
            
            # Check if page loaded correctly
            if "not found" in self.driver.page_source.lower():
                logger.error(f"{stock_code} not found on Screener.in")
                return None
            
            # Expand all collapsible rows (plus signs) before scraping tables
            self._expand_all_rows()
            
            # Scroll to load dynamic content
            self._scroll_page()
            self._human_delay(1.5, 3.0)
            self._scroll_page()
            self._human_delay(1.0, 2.0)
            
            # Extract data from tables
            data = {
                'stock_code': stock_code,
                'url': self.driver.current_url,
                'scraped_at': datetime.now().isoformat(),
                'company_info': self._extract_company_info(stock_code),
                'analysis': self._extract_analysis(stock_code),
                "peers": self._extract_peers(stock_code),
                'quarterly': self._extract_quarterly_financials(stock_code),
                'annual': self._extract_annual_financials(stock_code),
                'balance_sheet': self._extract_balance_sheet(stock_code),
                'cash_flow': self._extract_cash_flow(stock_code),
                'shareholding_quarterly': self._extract_shareholding(stock_code),
                'shareholding_yearly': self._extract_shareholding(stock_code, mode="yearly"),
            }
            
            # Save to JSON
            self._save_to_json(stock_code, data)
            # print(json.dumps(data, indent=2))  # Print to console for immediate visibility
            logger.info(f"{stock_code} scraped successfully")
            
            # Browser stays open by default (don't close)
            return data
            
        except Exception as e:
            logger.error(f"✗ Error scraping {stock_code}: {str(e)}")
            return None

    def _extract_company_info(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        ratios = {}
        try:
            # Look for analysis section
            section = self.driver.find_element(By.CSS_SELECTOR, "div.company-ratios")

            items = section.find_elements(By.CSS_SELECTOR, "ul#top-ratios li")

            ratios = {}

            for item in items:
                try:
                    name = item.find_element(By.CSS_SELECTOR, "span.name").text.strip()
                    value = item.find_element(By.CSS_SELECTOR, "span.value").text.strip()

                    ratios[name] = value
                except:
                    continue

            # print(ratios)
            
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return ratios


    def _extract_analysis(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        data = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#analysis"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for analysis section
            section = self.driver.find_element(By.ID, "analysis")
            blocks = section.find_elements(By.CSS_SELECTOR, "div.pros, div.cons")

            for block in blocks:
                # Title (Pros / Cons)
                title = block.find_element(By.CSS_SELECTOR, "p.title").text.strip()
                
                # List items
                items = block.find_elements(By.CSS_SELECTOR, "ul li")
                points = [item.text.strip() for item in items]

                data[title] = points

            # print(data)
            
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return data

    def _extract_peers(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        financials = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#peers"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for peers section
            section = self.driver.find_element(By.ID, "peers")

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")
            header_text = [h.text.strip() for h in headers]

            # print(f"\n\nHeaders: {header_text}")
            financials['headers'] = header_text[1:]

            # Rows
            rows = section.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            financials[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return financials

    def _extract_quarterly_financials(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        financials = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#quarters"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for quarterly results section
            section = self.driver.find_element(By.ID, "quarters")

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")
            header_text = [h.text.strip() for h in headers]

            # print(f"\n\nHeaders: {header_text}")
            financials['headers'] = header_text[1:]

            # Rows
            rows = section.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            financials[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return financials
    
    def _extract_annual_financials(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        financials = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#profit-loss"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for quarterly results section
            section = self.driver.find_element(By.ID, "profit-loss")

            # Select only tables that are NOT ranges-table
            tables = section.find_elements(By.CSS_SELECTOR, "table:not(.ranges-table)")

            # Usually the first valid table is what you want
            table = tables[0]

            # Headers (only from this table)
            headers = table.find_elements(By.CSS_SELECTOR, "thead th")
            if not headers:
                headers = table.find_elements(By.CSS_SELECTOR, "tr:first-child th")

            header_text = [h.text.strip() for h in headers]

            # print(f"\n\nHeaders: {header_text}")
            financials['headers'] = header_text[1:]

            # Rows (only from tbody if exists)
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not rows:
                rows = table.find_elements(By.CSS_SELECTOR, "tr")[1:]  # skip header row

            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            financials[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return financials

    def _extract_balance_sheet(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        financials = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#balance-sheet"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for balance sheet section
            section = self.driver.find_element(By.ID, "balance-sheet")

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")
            header_text = [h.text.strip() for h in headers]

            # print(f"\n\nHeaders: {header_text}")
            financials['headers'] = header_text[1:]

            # Rows
            rows = section.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            financials[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return financials

    def _extract_cash_flow(self, stock_code) -> Dict:
        """Extract financial statements (quarterly/annual)."""
        financials = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#cash-flow"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for cash flow section
            section = self.driver.find_element(By.ID, "cash-flow")

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")
            header_text = [h.text.strip() for h in headers]

            # print(f"\n\nHeaders: {header_text}")
            financials['headers'] = header_text[1:]

            # Rows
            rows = section.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            financials[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting financials: {str(e)}")
        
        return financials

    def _extract_shareholding(self, stock_code, mode="quarterly") -> Dict:
        """Extract shareholding pattern (promoter, FII, DII)."""
        shareholding = {}
        try:
            url = f"{self.base_url}/company/{stock_code}/#shareholding"
            self.driver.get(url)
            self._human_delay(2.0, 4.0)

            # Look for shareholding section
            section = self.driver.find_element(By.ID, "shareholding")

            h_start = 1
            h_end = 13

            if mode == "yearly":
                button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "button[data-tab-id='yearly-shp']"
                    ))
                )
                button.click()
                h_start = 14
                h_end = 24

            # Headers
            headers = section.find_elements(By.CSS_SELECTOR, "th")
            header_text = [h.text.strip() for h in headers]

            shareholding['headers'] = header_text[h_start:h_end]
            # print(f"\n\nHeaders: {header_text}")
            # print(f"\n\nHeaders: {shareholding['headers']}")

            # Rows
            rows = section.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows[:100]:  # Reasonable limit
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        metric = cells[0].text.strip()
                        values = [c.text.strip() for c in cells[1:]]
                        if metric and any(values):
                            shareholding[metric] = values
                except StaleElementReferenceException:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting shareholding: {str(e)}")

        return shareholding




    def _save_to_json(self, stock_code: str, data: Dict):
        """Save scraped data to JSON file."""
        logger.info(f"Saving data for {stock_code} to JSON")
        file_path = self.data_dir / f'{stock_code}.json'
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving JSON: {str(e)}")
    
    def _load_cached_data(self, stock_code: str) -> Optional[Dict]:
        """Load cached data if exists and is fresh."""
        file_path = self.data_dir / f'{stock_code}.json'
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check age (consider cache fresh if < 7 days)
            scraped_at = datetime.fromisoformat(data.get('scraped_at', ''))
            age_days = (datetime.now() - scraped_at).days
            
            if age_days < 7:
                data['cache_age_days'] = age_days
                return data
            else:
                logger.info(f"{stock_code} cache is {age_days} days old, will refresh")
                return None
        
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}")
            return None
    
    def batch_scrape(self, stock_codes: List[str], delay_between: float = 2.0) -> Dict[str, Optional[Dict]]:
        """
        Scrape multiple stocks in one session.
        
        Args:
            stock_codes: List of stock symbols
            delay_between: Delay between requests (seconds)
        
        Returns:
            Dictionary with results for each stock
        """
        results = {}
        total = len(stock_codes)
        
        for idx, code in enumerate(stock_codes, 1):
            logger.info(f"[{idx}/{total}] Processing {code}")
            results[code] = self.scrape_stock(code)
            
            if idx < total:  # Don't delay after last request
                self._human_delay(delay_between - 1, delay_between + 1)
        
        return results
    
    def keep_session_alive(self):
        """Keep session active (useful for long-running processes)."""
        if self.driver:
            self.driver.refresh()
            logger.info("Session refreshed")
    
    def close(self):
        """Close browser (call only when done; session is kept alive by default)."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_single_stock():
    """Scrape a single stock."""
    scraper = ScreenerScraper(headless=False)  # headless=True to hide window
    
    data = scraper.scrape_stock('TCS')
    if data:
        print(f"\n✓ Successfully scraped {data['stock_code']}")
        # print(f"Fundamentals: {data['fundamentals']}")
    
    # Browser stays open; you can manually inspect or call scraper again
    # scraper.scrape_stock('INFY')
    # scraper.scrape_stock('SBIN')
    
    # Close when done
    scraper.close()


def example_batch_scrape():
    """Scrape multiple stocks efficiently."""
    scraper = ScreenerScraper(headless=False)
    
    stocks = ['RELIANCE', 'INFY', 'SBIN', 'TCS', 'MARUTI']
    results = scraper.batch_scrape(stocks, delay_between=2.0)
    
    # Summary
    success = sum(1 for v in results.values() if v is not None)
    print(f"\n{'='*50}")
    print(f"Scraped {success}/{len(stocks)} stocks successfully")
    print(f"Data saved to: {scraper.data_dir}")
    
    scraper.close()


def example_context_manager():
    """Use as context manager (auto-closes)."""
    with ScreenerScraper(headless=False) as scraper:
        for code in ['RELIANCE', 'TCS', 'INFY']:
            scraper.scrape_stock(code)
            scraper._human_delay(1.5, 2.5)


def example_force_refresh():
    """Force refresh cached data."""
    scraper = ScreenerScraper(headless=False)
    
    # First call uses cache
    data1 = scraper.scrape_stock('RELIANCE')
    
    # Second call fetches fresh data (ignores 7-day cache)
    data2 = scraper.scrape_stock('RELIANCE', force_refresh=True)
    
    scraper.close()


# if __name__ == '__main__':
#     # Choose which example to run:
#     print("Starting Screener.in Scraper for BruteQuantLabs\n")
    
#     # Uncomment one:
#     example_single_stock()
#     # example_batch_scrape()
#     # example_context_manager()
#     # example_force_refresh()

#     print("\n✓ Scraping complete. Check 'screener_data/' for JSON files.")