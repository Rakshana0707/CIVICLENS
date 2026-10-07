import os
import re
import time
import json
import hashlib
import urllib.robotparser
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse, urljoin
import requests

from backend.core.logger import setup_logger
from backend.acquisition.news_registry import SourceConfig, NewsSourceRegistry
from backend.acquisition.news_adapters import adapter_registry, BaseSourceAdapter

logger = setup_logger("civiclens.acquisition.news_scraper_framework")

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratch", "cache", "http")


class RateLimiter:
    """Per-domain rate limiter enforcing polite crawl delays."""
    def __init__(self, default_delay: float = 2.0):
        self.default_delay = default_delay
        self.last_fetch: Dict[str, float] = {}

    def wait(self, domain: str, custom_delay: Optional[float] = None) -> float:
        delay = custom_delay if custom_delay is not None else self.default_delay
        now = time.time()
        elapsed_wait = 0.0
        if domain in self.last_fetch:
            elapsed = now - self.last_fetch[domain]
            if elapsed < delay:
                elapsed_wait = delay - elapsed
                time.sleep(elapsed_wait)
        self.last_fetch[domain] = time.time()
        return elapsed_wait


class RobotsChecker:
    """Validator for domain robots.txt directives."""
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return True

        if domain not in self.parsers:
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                self.parsers[domain] = rp
            except Exception as e:
                logger.warning(f"Unable to read robots.txt for {domain}: {e}. Permissive fallback enabled.")
                return True

        return self.parsers[domain].can_fetch(self.user_agent, url)


class CacheManager:
    """Disk & memory cache manager storing HTTP responses with TTL and header validation."""
    def __init__(self, cache_dir: str = CACHE_DIR, ttl_seconds: int = 86400):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.memory_cache: Dict[str, Dict] = {}
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_key(self, url: str) -> str:
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def get(self, url: str) -> Optional[str]:
        key = self._get_key(url)
        # Check memory
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                return entry["content"]

        # Check disk
        file_path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if time.time() - data["timestamp"] < self.ttl_seconds:
                        self.memory_cache[key] = data
                        return data["content"]
            except Exception as e:
                logger.warning(f"Cache read error for {url}: {e}")

        return None

    def set(self, url: str, content: str, headers: Optional[Dict] = None) -> None:
        key = self._get_key(url)
        data = {
            "url": url,
            "timestamp": time.time(),
            "content": content,
            "headers": headers or {}
        }
        self.memory_cache[key] = data
        file_path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Cache write error for {url}: {e}")


class Fetcher:
    """HTTP client supporting retries, exponential backoff, rate limiting, and caching."""
    def __init__(self, rate_limiter: RateLimiter, cache_manager: CacheManager,
                 robots_checker: RobotsChecker, max_retries: int = 3, backoff_factor: float = 1.5):
        self.rate_limiter = rate_limiter
        self.cache_manager = cache_manager
        self.robots_checker = robots_checker
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()

    def fetch(self, url: str, source_config: Optional[SourceConfig] = None, use_cache: bool = True, timeout: int = 15) -> Optional[str]:
        if use_cache:
            cached = self.cache_manager.get(url)
            if cached:
                logger.info(f"Cache hit for URL: {url}")
                return cached

        if not self.robots_checker.is_allowed(url):
            logger.warning(f"Access blocked by robots.txt policy: {url}")
            return None

        domain = urlparse(url).netloc
        delay = source_config.rate_limit if source_config else 2.0
        self.rate_limiter.wait(domain, custom_delay=delay)

        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            try:
                headers = {"User-Agent": self.robots_checker.user_agent}
                response = self.session.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                content = response.text
                if use_cache and content:
                    self.cache_manager.set(url, content, dict(response.headers))
                return content
            except requests.RequestException as e:
                logger.warning(f"Fetch attempt {attempt}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor ** attempt
                    time.sleep(sleep_time)

        logger.error(f"Failed to fetch URL after {self.max_retries} retries: {url}")
        return None


class Deduplicator:
    """Deduplication manager tracking URLs and exact text hashes."""
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()

    def is_duplicate_url(self, url: str) -> bool:
        canonical = re.sub(r'(\?|#).*$', '', url.strip().lower())
        if canonical in self.seen_urls:
            return True
        self.seen_urls.add(canonical)
        return False

    def is_duplicate_text(self, text_hash: str) -> bool:
        if text_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(text_hash)
        return False


class ContentExtractor:
    """Extracts, cleans, and normalizes article text content."""
    @staticmethod
    def extract_clean_text(raw_paragraphs: List[str]) -> str:
        cleaned = []
        for p in raw_paragraphs:
            txt = re.sub(r'\s+', ' ', p).strip()
            if len(txt.split()) >= 4:
                cleaned.append(txt)
        return "\n\n".join(cleaned)


class MetadataExtractor:
    """Extracts metadata fields (headline, author, pubdate, canonical URL)."""
    @staticmethod
    def extract_metadata(parsed_dict: Dict, source_config: Optional[SourceConfig] = None) -> Dict[str, Any]:
        return {
            "title": parsed_dict.get("title", ""),
            "author": parsed_dict.get("author", "Staff Reporter"),
            "publication_date": parsed_dict.get("publication_date", datetime.now(timezone.utc)),
            "canonical_url": parsed_dict.get("canonical_url", parsed_dict.get("url", "")),
            "language": source_config.language if source_config else "ta"
        }


class ArticleParser:
    """Parser controller delegating parsing to registered source adapters."""
    def __init__(self):
        self.registry = adapter_registry

    def parse(self, html_content: str, url: str, source_config: Optional[SourceConfig] = None) -> Optional[Dict[str, Any]]:
        adapter_name = source_config.parser_type if source_config else "generic_adapter"
        adapter = self.registry.get_adapter(adapter_name)
        selectors = source_config.selectors if source_config else {}
        
        try:
            parsed = adapter.parse_article(html_content, url, selector_config=selectors)
            if not parsed or not parsed.get("article_text"):
                logger.warning(f"Primary adapter '{adapter_name}' yielded empty content. Falling back to generic adapter.")
                generic_adapter = self.registry.get_adapter("generic_adapter")
                parsed = generic_adapter.parse_article(html_content, url, selector_config=selectors)
            return parsed
        except Exception as e:
            logger.error(f"Parser error using adapter '{adapter_name}' on {url}: {e}")
            return None


class BaseScraper(ABC):
    """Abstract Base Class for News Scraper implementations."""
    @abstractmethod
    def crawl_source(self, source_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def scrape_article(self, url: str, source_id: str) -> Optional[Dict[str, Any]]:
        pass


class SourceScraper(BaseScraper):
    """
    Main driver orchestrating URL discovery, fetcher, cache, rate limiter,
    deduplicator, and pluggable source adapters for a target news source.
    """
    def __init__(self, registry: Optional[NewsSourceRegistry] = None, user_agent: Optional[str] = None):
        self.registry = registry or NewsSourceRegistry()
        user_agent = user_agent or "CIVICLENS-TN-NewsAnalyzer/1.0 (+https://civiclens.tn.gov.in/bot)"
        self.rate_limiter = RateLimiter()
        self.cache_manager = CacheManager()
        self.robots_checker = RobotsChecker(user_agent)
        self.fetcher = Fetcher(self.rate_limiter, self.cache_manager, self.robots_checker)
        self.deduplicator = Deduplicator()
        self.parser = ArticleParser()

    def discover_urls_from_rss(self, source_config: SourceConfig) -> List[str]:
        """Discovers article URLs from configured RSS feeds."""
        discovered = []
        for rss_url in source_config.rss_urls:
            logger.info(f"Polling RSS feed: {rss_url}")
            xml_content = self.fetcher.fetch(rss_url, source_config=source_config, use_cache=False)
            if xml_content:
                # Extract links from RSS XML
                links = re.findall(r'<link>(.*?)</link>', xml_content, re.I)
                for link in links:
                    link = link.strip()
                    if link and not link.endswith('.xml') and link != rss_url:
                        if not self.deduplicator.is_duplicate_url(link):
                            discovered.append(link)
        return discovered

    def discover_urls_from_html(self, html_content: str, base_url: str, source_config: SourceConfig) -> List[str]:
        """Discovers article links from index/category HTML pages using regex and url patterns."""
        discovered = []
        raw_links = re.findall(r'href=["\']([^"\']+)["\']', html_content, re.I)
        for rel_link in raw_links:
            full_url = urljoin(base_url, rel_link)
            # Match against article_url_patterns if specified
            is_article = False
            if source_config.article_url_patterns:
                for pattern in source_config.article_url_patterns:
                    if re.search(pattern, full_url):
                        is_article = True
                        break
            else:
                is_article = True # Fallback if no patterns specified

            if is_article and not self.deduplicator.is_duplicate_url(full_url):
                discovered.append(full_url)
        return discovered

    def scrape_article(self, url: str, source_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Scrapes and parses a single news article URL."""
        source_config = self.registry.get_source(source_id)
        if not source_config:
            logger.error(f"Source configuration '{source_id}' not found.")
            return None

        if not source_config.enabled:
            logger.warning(f"Source '{source_id}' is disabled. Skipping scrape.")
            return None

        html_content = self.fetcher.fetch(url, source_config=source_config, use_cache=use_cache)
        if not html_content:
            return None

        parsed = self.parser.parse(html_content, url, source_config=source_config)
        if not parsed:
            return None

        # Deduplication check on text hash
        if self.deduplicator.is_duplicate_text(parsed["text_hash"]):
            logger.info(f"Duplicate article content detected for URL: {url}. Skipping.")
            return None

        parsed["source_id"] = source_id
        parsed["source_name"] = source_config.source_name
        parsed["language"] = source_config.language
        return parsed

    def crawl_source(self, source_id: str, max_articles: int = 10) -> List[Dict[str, Any]]:
        """Crawls a source using RSS and homepage discovery, returning parsed articles."""
        source_config = self.registry.get_source(source_id)
        if not source_config or not source_config.enabled:
            return []

        logger.info(f"Initiating crawl for source: '{source_config.source_name}' ({source_id})")
        target_urls = self.discover_urls_from_rss(source_config)

        # Fallback to domain homepage discovery if RSS yields few links
        if len(target_urls) < 3 and source_config.official_url:
            home_html = self.fetcher.fetch(source_config.official_url, source_config=source_config)
            if home_html:
                html_urls = self.discover_urls_from_html(home_html, source_config.official_url, source_config)
                target_urls.extend(html_urls)

        scraped_articles = []
        for url in target_urls[:max_articles]:
            art = self.scrape_article(url, source_id=source_id)
            if art:
                scraped_articles.append(art)

        logger.info(f"Crawl complete for {source_id}: {len(scraped_articles)} articles scraped.")
        return scraped_articles
