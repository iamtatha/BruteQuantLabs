"""
BruteQuantLabs MC.in Fundamentals Scraper
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
        logging.FileHandler('mc_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - '
           '%(filename)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('mc_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MCScraper:
    """
    Persistent MC.in scraper with session management.
    
    Usage:
        scraper = MCScraper(headless=False)  # headless=True for background
        data = scraper.scrape_stock('RELIANCE')
        scraper.close()  # Optional; keeps browser open by default
    """
    
    def __init__(self, headless: bool = False, data_dir: str = 'database/demo_data/mc_data'):
        """
        Initialize scraper with persistent session.
        
        Args:
            headless: Run Chrome in headless mode (no visible window)
            data_dir: Directory to store JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_url = 'https://www.moneycontrol.com/india/stockpricequote/'
        self.driver = None
        self.headless = headless
        
        # Session state tracking
        self.session_file = self.data_dir / 'session_state.json'
        self.last_activity = time.time()

        with open("database/static_data/company-sector.json",'r') as infile:
            self.company_sector = json.load(infile)['companies']
        
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
        options.page_load_strategy = 'eager'
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(15)
        logger.info("WebDriver initialized")
    
    def get_url(self, stock_code):
        sector = self.company_sector.get(stock_code, "Unknown")
        url = f"{self.base_url}{sector.lower().replace(' ', '')}/{stock_code.lower()}/"
        return url

    def _human_delay(self, min_sec: float = 0.5, max_sec: float = 3.0):
        """Random delay to mimic human behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _scroll_page(self):
        """Random scrolling to look human-like."""
        scroll_amount = random.randint(200, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self._human_delay(0.3, 1.0)
    

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
            url = self.get_url(stock_code)
            self.driver.get(url)
            self._human_delay(2.0, 4.0)
            
            # Check if page loaded correctly
            if "not found" in self.driver.page_source.lower():
                logger.error(f"{stock_code} not found on MC.in")
                return None
            
            
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
                'forecast1': self._extract_forecast(stock_code),
                'forecast2': self._extract_analyst_consensus(),
                'analyst_rating': self.scrape_analyst_rating()
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

    def _extract_forecast(self, stock_code) -> dict:
        data = []

        # Get all forecast boxes
        boxes = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div.forecast_list .forecast_list_box"
        )

        for box in boxes:
            item = {}

            # Title (each box has its own h3)
            try:
                item["title"] = box.find_element(By.CSS_SELECTOR, "h3").text.strip()
            except:
                item["title"] = None

            # Timeline (x-axis labels inside THIS box only)
            labels = box.find_elements(
                By.CSS_SELECTOR,
                ".highcharts-xaxis-labels span div"
            )
            item["timeline"] = [l.text.strip() for l in labels if l.text.strip()]

            # Forecast tags (HIGH / MEAN / LOW)
            tags = box.find_elements(
                By.CSS_SELECTOR,
                ".highcharts-data-labels span"
            )
            item["labels"] = [t.text.strip() for t in tags if t.text.strip()]

            data.append(item)

        return data

    def scrape_analyst_rating(self):
        data = {}

        container = self.driver.find_element(By.ID, "anRatingGraph")

        # Final recommendation (center circle)
        try:
            data["final_rating"] = container.find_element(
                By.ID, "anFinalRating"
            ).text.strip()
        except:
            data["final_rating"] = None

        # Individual ratings
        blocks = container.find_elements(By.CSS_SELECTOR, ".graphblock")

        ratings = {}

        for block in blocks:
            try:
                name = block.find_element(By.CSS_SELECTOR, ".heading").text.strip()
                value = block.find_element(By.CSS_SELECTOR, ".percentage").text.strip()

                ratings[name.lower()] = value
            except:
                continue

        data["ratings"] = ratings

        return data



    def _extract_analyst_consensus(self) -> Dict:
        """
        Extract analyst consensus ratings from Highcharts stacked bar chart.
        
        Returns:
            {
                'months': ['Jan 2026', 'Feb 2026', ...],
                'ratings': {
                    'buy': [20, 18, 17, 18, 18],
                    'outperform': [12, 12, 13, 11, 11],
                    'hold': [10, 10, 9, 9, 9],
                    'underperform': [1, 1, 1, 1, 1],
                    'sell': [3, 4, 4, 4, 4]
                },
                'total_analysts': [46, 45, 44, 43, 43]
            }
        """
        consensus_data = {
            'months': [],
            'ratings': {},
            'total_analysts': []
        }
        
        try:
            self._human_delay(1.0, 2.0)
            consensus = self.driver.find_elements(By.ID, "consensus_graph")

            # Find the chart container (look for highcharts-specific elements)
            try:
                # Try to find axis labels for months
                month_labels = consensus[0].find_elements(By.CSS_SELECTOR,
                    "g.highcharts-xaxis-labels text")
                print(f"Found {len(month_labels)} month labels")
                
                if month_labels:
                    for label in month_labels:
                        text = label.text.strip()
                        if text:
                            consensus_data['months'].append(text)
                    logger.info(f"Found {len(consensus_data['months'])} months")
            except NoSuchElementException:
                logger.warning("Could not find month labels")
                return consensus_data
            
            # Extract data from the stacked bar chart
            # Ratings order: Buy (dark green), Outperform (light green), Hold (gray), 
            #               Underperform (red), Sell (dark red)
            rating_labels = {
                0: 'buy',           # #2C7C47 (dark green)
                1: 'outperform',    # #50B973 (light green)
                2: 'hold',          # #747474 (gray)
                3: 'underperform',  # #E2525B (red)
                4: 'sell'           # #9C2028 (dark red)
            }
            
            # Find all data label text elements (numbers on the bars)
            data_labels_groups = consensus[0].find_elements(By.CSS_SELECTOR,
                "div.highcharts-data-labels")
            
            if len(data_labels_groups) >= 5:  # Should have 5 series (Buy, Outperform, Hold, Underperform, Sell)
                for series_idx in range(5):
                    rating_name = rating_labels[series_idx]
                    consensus_data['ratings'][rating_name] = []
                    print(f"Extracting {rating_name} data in series {series_idx}")

                    try:
                        # Get all span elements with numbers for this series
                        group = data_labels_groups[series_idx]
                        numbers = group.find_elements(By.CSS_SELECTOR, "span")
                        print(f"Found {len(numbers)} numbers for {rating_name} in series {series_idx}")

                        for num_elem in numbers:
                            print(f"\n{num_elem.text.strip()}\n")
                            text = num_elem.text.strip()
                            print(f"Found {text} for {rating_name} in series {series_idx}")
                            if text and text.isdigit():
                                consensus_data['ratings'][rating_name].append(int(text))
                        
                        if consensus_data['ratings'][rating_name]:
                            logger.info(f"  {rating_name}: {consensus_data['ratings'][rating_name]}")
                    except Exception as e:
                        logger.warning(f"Error extracting {rating_name}: {str(e)}")
                        consensus_data['ratings'][rating_name] = []
            
            # Extract total analysts (stack labels at top)
            try:
                stack_labels = self.driver.find_elements(By.CSS_SELECTOR,
                    "g.highcharts-stack-labels text")
                
                for label in stack_labels:
                    text = label.text.strip()
                    if text and text.isdigit():
                        consensus_data['total_analysts'].append(int(text))
                
                if consensus_data['total_analysts']:
                    logger.info(f"  Total analysts per month: {consensus_data['total_analysts']}")
            except Exception as e:
                logger.warning(f"Error extracting total analysts: {str(e)}")
            
            # Validate data consistency
            num_months = len(consensus_data['months'])
            if num_months > 0:
                for rating, values in consensus_data['ratings'].items():
                    if len(values) != num_months:
                        logger.warning(f"{rating} has {len(values)} values but {num_months} months")
        
        except Exception as e:
            logger.warning(f"Error extracting analyst consensus: {str(e)}")
        
        return consensus_data





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
        return None
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
    scraper = MCScraper(headless=False)  # headless=True to hide window
    
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
    scraper = MCScraper(headless=False)
    
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
    with MCScraper(headless=False) as scraper:
        for code in ['RELIANCE', 'TCS', 'INFY']:
            scraper.scrape_stock(code)
            scraper._human_delay(1.5, 2.5)


def example_force_refresh():
    """Force refresh cached data."""
    scraper = MCScraper(headless=False)
    
    # First call uses cache
    data1 = scraper.scrape_stock('RELIANCE')
    
    # Second call fetches fresh data (ignores 7-day cache)
    data2 = scraper.scrape_stock('RELIANCE', force_refresh=True)
    
    scraper.close()


if __name__ == '__main__':
    # Choose which example to run:
    print("Starting MC.in Scraper for BruteQuantLabs\n")
    
    # Uncomment one:
    example_single_stock()
    # example_batch_scrape()
    # example_context_manager()
    # example_force_refresh()

    print("\n✓ Scraping complete. Check 'mc_data/' for JSON files.")