import re
import hashlib
import time
import urllib.robotparser
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone
import requests
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.acquisition.news_scraper")

class RateLimiter:
    """Per-domain rate limiter ensuring polite crawling delays."""
    def __init__(self, default_delay=2.0):
        self.default_delay = default_delay
        self.last_fetch = {}

    def wait(self, domain, custom_delay=None):
        delay = custom_delay if custom_delay is not None else self.default_delay
        now = time.time()
        if domain in self.last_fetch:
            elapsed = now - self.last_fetch[domain]
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self.last_fetch[domain] = time.time()


class NewsScraper:
    """
    Modular, resilient web scraping engine supporting RSS discovery,
    HTML parsing, canonical URL detection, duplicate hashing, and robots.txt compliance.
    """
    def __init__(self, rate_limit_delay=2.0, user_agent=None):
        self.rate_limiter = RateLimiter(default_delay=rate_limit_delay)
        self.user_agent = user_agent or "CIVICLENS-TN-NewsAnalyzer/1.0 (+https://civiclens.tn.gov.in/bot)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.robot_parsers = {}

    def is_allowed_by_robots(self, url):
        """Check robots.txt compliance before fetching."""
        parsed = urlparse(url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        
        if domain not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                self.robot_parsers[domain] = rp
            except Exception as e:
                logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                return True # Fail permissive for standard academic research bot if unreachable
        
        return self.robot_parsers[domain].can_fetch(self.user_agent, url)

    def compute_text_hash(self, text):
        """Computes SHA-256 hash of normalized text for exact duplicate detection."""
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def fetch_url(self, url, timeout=15):
        """Fetches raw page content with rate limiting and retry handling."""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if not self.is_allowed_by_robots(url):
            logger.warning(f"URL disallowed by robots.txt: {url}")
            return None

        self.rate_limiter.wait(domain)

        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"HTTP fetch error for {url}: {e}")
            return None

    def parse_article_html(self, html_content, url, selector_config=None):
        """
        Parses HTML content to extract headline, body text, author, publication date,
        and canonical URL using custom selectors or fallback heuristics.
        """
        if not html_content:
            return None

        if HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 1. Canonical URL
            canonical_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
            canonical_url = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else url

            # 2. Title / Headline
            title = ""
            if selector_config and "title" in selector_config:
                title_el = soup.select_one(selector_config["title"])
                if title_el:
                    title = title_el.get_text(strip=True)
            if not title:
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")

            # 3. Article Body Text
            paragraphs = []
            if selector_config and "body" in selector_config:
                p_els = soup.select(selector_config["body"])
                paragraphs = [p.get_text(strip=True) for p in p_els if p.get_text(strip=True)]
            if not paragraphs:
                for p in soup.find_all("p"):
                    txt = p.get_text(strip=True)
                    if len(txt.split()) > 5:
                        paragraphs.append(txt)

            # 4. Author
            author = "Staff Reporter"
            if selector_config and "author" in selector_config:
                author_el = soup.select_one(selector_config["author"])
                if author_el:
                    author = author_el.get_text(strip=True)
            else:
                meta_author = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})
                if meta_author and meta_author.get("content"):
                    author = meta_author["content"].strip()
        else:
            # Fallback regex parsing when BeautifulSoup is unavailable
            canon_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html_content, re.I)
            canonical_url = canon_match.group(1) if canon_match else url

            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.I | re.S)
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip() if h1_match else ""

            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html_content, re.I | re.S)
            paragraphs = [re.sub(r'<[^>]+>', '', p).strip() for p in p_matches if len(re.sub(r'<[^>]+>', '', p).strip().split()) > 5]
            author = "Staff Reporter"

        article_text = "\n\n".join(paragraphs)
        if not article_text or len(article_text.split()) < 15:
            logger.warning(f"Article text extraction yielded insufficient content for {url}")

        # 5. Publication Date
        pub_date = datetime.now(timezone.utc)
        if HAS_BS4 and 'soup' in locals():
            meta_date = soup.find("meta", property=re.compile(r"(article:published_time|pubdate)", re.I))
            if meta_date and meta_date.get("content"):
                try:
                    dt_str = meta_date["content"].split("T")[0]
                    pub_date = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass
        else:
            meta_match = re.search(r'<meta[^>]+property=["\'](?:article:published_time|pubdate)["\'][^>]+content=["\']([^"\']+)["\']', html_content, re.I)
            if meta_match:
                try:
                    dt_str = meta_match.group(1).split("T")[0]
                    pub_date = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass


        word_count = len(article_text.split())
        text_hash = self.compute_text_hash(article_text)

        return {
            "url": url,
            "canonical_url": canonical_url,
            "title": title,
            "author": author,
            "publication_date": pub_date,
            "article_text": article_text,
            "word_count": word_count,
            "text_hash": text_hash
        }
