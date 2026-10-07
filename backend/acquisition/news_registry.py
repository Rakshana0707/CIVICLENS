import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from backend.core.logger import setup_logger

logger = setup_logger("civiclens.acquisition.news_registry")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "news_sources.json")

@dataclass
class SourceConfig:
    """Dataclass holding detailed configuration for a registered news source."""
    source_id: str
    source_name: str
    domain: str
    language: str = "ta"
    article_url_patterns: List[str] = field(default_factory=list)
    pagination_rules: Dict = field(default_factory=dict)
    parser_type: str = "generic_adapter"
    rate_limit: float = 2.0
    enabled: bool = True
    access_notes: str = ""
    rss_urls: List[str] = field(default_factory=list)
    selectors: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SourceConfig":
        return cls(
            source_id=data["source_id"],
            source_name=data["source_name"],
            domain=data["domain"],
            language=data.get("language", "ta"),
            article_url_patterns=data.get("article_url_patterns", []),
            pagination_rules=data.get("pagination_rules", {}),
            parser_type=data.get("parser_type", "generic_adapter"),
            rate_limit=float(data.get("rate_limit", 2.0)),
            enabled=data.get("enabled", True),
            access_notes=data.get("access_notes", ""),
            rss_urls=data.get("rss_urls", []),
            selectors=data.get("selectors", {})
        )

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "domain": self.domain,
            "language": self.language,
            "article_url_patterns": self.article_url_patterns,
            "pagination_rules": self.pagination_rules,
            "parser_type": self.parser_type,
            "rate_limit": self.rate_limit,
            "enabled": self.enabled,
            "access_notes": self.access_notes,
            "rss_urls": self.rss_urls,
            "selectors": self.selectors
        }


class NewsSourceRegistry:
    """
    Central registry management for news outlets and media configurations.
    Loads configurations from JSON disk files and registers pluggable adapters.
    """
    def __init__(self, config_file: str = CONFIG_PATH):
        self.config_file = config_file
        self._sources: Dict[str, SourceConfig] = {}
        self.load_registry()

    def load_registry(self) -> None:
        """Loads and parses source configurations from disk."""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file not found at {self.config_file}. Initializing empty registry.")
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    src = SourceConfig.from_dict(item)
                    self._sources[src.source_id] = src
            logger.info(f"Loaded {len(self._sources)} news sources into registry.")
        except Exception as e:
            logger.error(f"Error loading news source registry: {e}")

    def get_source(self, source_id: str) -> Optional[SourceConfig]:
        """Lookup a source configuration by ID."""
        return self._sources.get(source_id)

    def get_all_sources(self, enabled_only: bool = True) -> List[SourceConfig]:
        """Returns list of registered source configurations."""
        if enabled_only:
            return [s for s in self._sources.values() if s.enabled]
        return list(self._sources.values())

    def register_source(self, config: SourceConfig, save_to_disk: bool = False) -> SourceConfig:
        """Dynamically registers or updates a news source in memory (and optionally persists to disk)."""
        self._sources[config.source_id] = config
        if save_to_disk and os.path.exists(self.config_file):
            try:
                all_dicts = [s.to_dict() for s in self._sources.values()]
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(all_dicts, f, indent=2, ensure_ascii=False)
                logger.info(f"Persisted source {config.source_id} to {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to persist registry to disk: {e}")
        return config
