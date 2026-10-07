import re
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.core.logger import setup_logger

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False

logger = setup_logger("civiclens.acquisition.news_adapters")


class BaseSourceAdapter(ABC):
    """
    Abstract Base Class for source-specific article parsing adapters.
    Each adapter encapsulates domain-specific CSS/XPath rules and extraction logic.
    """

    @abstractmethod
    def parse_article(self, html_content: str, url: str, selector_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Parses raw HTML and returns a structured article dictionary or None."""
        pass

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Computes SHA-256 hash of normalized text for exact duplicate detection."""
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def extract_canonical_url(html_content: str, fallback_url: str) -> str:
        """Extracts rel="canonical" link from HTML or falls back to provided URL."""
        if HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")
            canonical_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
            if canonical_tag and canonical_tag.get("href"):
                return canonical_tag["href"]
        else:
            canon_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html_content, re.I)
            if canon_match:
                return canon_match.group(1)
        return fallback_url


class GenericSourceAdapter(BaseSourceAdapter):
    """Fallback general-purpose adapter using standard HTML heuristics."""

    def parse_article(self, html_content: str, url: str, selector_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        if not html_content:
            return None

        canonical_url = self.extract_canonical_url(html_content, url)
        title = ""
        paragraphs = []
        author = "Staff Reporter"

        if HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Selector-based or heuristic title
            if selector_config and "title" in selector_config:
                el = soup.select_one(selector_config["title"])
                if el:
                    title = el.get_text(strip=True)
            if not title:
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")

            # Selector-based or heuristic body paragraphs
            if selector_config and "body" in selector_config:
                p_els = soup.select(selector_config["body"])
                paragraphs = [p.get_text(strip=True) for p in p_els if p.get_text(strip=True)]
            if not paragraphs:
                for p in soup.find_all("p"):
                    txt = p.get_text(strip=True)
                    if len(txt.split()) > 5:
                        paragraphs.append(txt)

            if selector_config and "author" in selector_config:
                aut_el = soup.select_one(selector_config["author"])
                if aut_el:
                    author = aut_el.get_text(strip=True)
        else:
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.I | re.S)
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip() if h1_match else ""

            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html_content, re.I | re.S)
            paragraphs = [re.sub(r'<[^>]+>', '', p).strip() for p in p_matches if len(re.sub(r'<[^>]+>', '', p).strip().split()) > 5]

        # Clean title branding
        title = re.sub(r'\s*[\-|\|]\s*.*$', '', title)
        article_text = "\n\n".join(paragraphs)

        return {
            "url": url,
            "canonical_url": canonical_url,
            "title": title,
            "author": author,
            "publication_date": datetime.now(timezone.utc),
            "article_text": article_text,
            "word_count": len(article_text.split()),
            "text_hash": self.compute_text_hash(article_text)
        }


class TheHinduAdapter(GenericSourceAdapter):
    """Source adapter specialized for The Hindu news pages."""

    def parse_article(self, html_content: str, url: str, selector_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        parsed = super().parse_article(html_content, url, selector_config)
        if parsed and parsed["title"]:
            parsed["title"] = re.sub(r'\s*-\s*The Hindu$', '', parsed["title"], flags=re.I)
        return parsed


class DinamaniAdapter(GenericSourceAdapter):
    """Source adapter specialized for Dinamani Tamil news pages."""

    def parse_article(self, html_content: str, url: str, selector_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        parsed = super().parse_article(html_content, url, selector_config)
        if parsed and parsed["title"]:
            parsed["title"] = re.sub(r'\s*-\s*தினமணி$', '', parsed["title"])
        return parsed


class DinamalarAdapter(GenericSourceAdapter):
    """Source adapter specialized for Dinamalar Tamil news pages."""

    def parse_article(self, html_content: str, url: str, selector_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        parsed = super().parse_article(html_content, url, selector_config)
        if parsed and parsed["title"]:
            parsed["title"] = re.sub(r'\s*-\s*தினமலர்$', '', parsed["title"])
        return parsed


class AdapterRegistry:
    """
    Factory & Registry pattern for source-specific article parsing adapters.
    Allows registering new adapters dynamically without altering core engine.
    """

    def __init__(self):
        self._adapters: Dict[str, BaseSourceAdapter] = {}
        # Register standard built-in adapters
        self.register_adapter("generic_adapter", GenericSourceAdapter())
        self.register_adapter("thehindu_adapter", TheHinduAdapter())
        self.register_adapter("dinamani_adapter", DinamaniAdapter())
        self.register_adapter("dinamalar_adapter", DinamalarAdapter())

    def register_adapter(self, adapter_name: str, adapter_instance: BaseSourceAdapter) -> None:
        """Registers a new source adapter into the system."""
        self._adapters[adapter_name] = adapter_instance
        logger.info(f"Registered source adapter: '{adapter_name}'")

    def get_adapter(self, adapter_name: str) -> BaseSourceAdapter:
        """Retrieves adapter instance by name, falling back to generic adapter."""
        return self._adapters.get(adapter_name, self._adapters["generic_adapter"])


# Global singleton instance
adapter_registry = AdapterRegistry()
