import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum, JSON, Date
)
from sqlalchemy.orm import relationship
from backend.database.base_class import Base

class SourceType(str, enum.Enum):
    PRINT_DIGITAL = "print_digital"
    TV_DIGITAL = "tv_digital"
    DIGITAL_NATIVE = "digital_native"
    OFFICIAL_GOV = "official_gov"
    ARCHIVE = "archive"

class ActiveStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    NEEDS_AUDIT = "needs_audit"

class NewsSource(Base):
    """
    Registry for news publishers, government media portals, and electoral feeds.
    """
    __tablename__ = "news_sources"

    source_id = Column(String, primary_key=True, index=True)
    source_name = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=False, unique=True, index=True)
    language = Column(String, default="ta")  # "ta", "en", "bilingual"
    source_type = Column(Enum(SourceType), default=SourceType.PRINT_DIGITAL)
    official_url = Column(String, nullable=True)
    robots_policy_checked = Column(Boolean, default=True)
    collection_method = Column(String, default="rss")  # "rss", "html_scraper", "official_api"
    active_status = Column(Enum(ActiveStatus), default=ActiveStatus.ACTIVE)
    priority = Column(String, default="P1")  # P1, P2, P3
    selector_config = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    articles = relationship("Article", back_populates="source", cascade="all, delete-orphan")
    coverage_metrics = relationship("CoverageMetric", back_populates="source", cascade="all, delete-orphan")
    bias_indicators = relationship("BiasIndicator", foreign_keys="[BiasIndicator.source_id]", back_populates="source", cascade="all, delete-orphan")
    snapshots = relationship("SourceSnapshot", back_populates="source", cascade="all, delete-orphan")


class Article(Base):
    """
    Core News Article entity storing ingested text, provenance, and metadata.
    """
    __tablename__ = "news_articles"

    article_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String, nullable=False, unique=True, index=True)
    canonical_url = Column(String, nullable=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True, default="Staff Reporter")
    publication_date = Column(DateTime, nullable=True, index=True)
    retrieval_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    section = Column(String, nullable=True)
    language = Column(String, default="ta")
    
    raw_html_path = Column(String, nullable=True)
    article_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    text_hash = Column(String, nullable=False, index=True)
    
    is_test_fixture = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source = relationship("NewsSource", back_populates="articles")
    versions = relationship("ArticleVersion", back_populates="article", cascade="all, delete-orphan")
    entities = relationship("ArticleEntity", back_populates="article", cascade="all, delete-orphan")
    topics = relationship("ArticleTopic", back_populates="article", cascade="all, delete-orphan")
    events = relationship("ArticleEvent", back_populates="article", cascade="all, delete-orphan")
    features = relationship("ArticleFeature", back_populates="article", uselist=False, cascade="all, delete-orphan")


class ArticleVersion(Base):
    """
    Tracks editorial changes and text revisions to published articles over time.
    """
    __tablename__ = "news_article_versions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1)
    text_hash = Column(String, nullable=False)
    article_text = Column(Text, nullable=False)
    content_diff = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article = relationship("Article", back_populates="versions")


class PoliticalParty(Base):
    """
    Political party entity in Tamil Nadu politics.
    """
    __tablename__ = "political_parties"

    party_id = Column(String, primary_key=True, index=True)
    party_name = Column(String, nullable=False, index=True)
    party_code = Column(String, nullable=False, unique=True, index=True)
    symbol = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    persons = relationship("PoliticalPerson", back_populates="party")


class PoliticalPerson(Base):
    """
    Key political figure, minister, MLA/MP, or leader.
    """
    __tablename__ = "political_persons"

    person_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    name_ta = Column(String, nullable=True)
    party_id = Column(String, ForeignKey("political_parties.party_id", ondelete="SET NULL"), nullable=True, index=True)
    designation = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    party = relationship("PoliticalParty", back_populates="persons")


class PoliticalEntity(Base):
    """
    Generalized entity registry (departments, constituencies, organizations, leaders).
    """
    __tablename__ = "political_entities"

    entity_id = Column(String, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)  # person, party, department, constituency, organization, location
    name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article_mentions = relationship("ArticleEntity", back_populates="entity", cascade="all, delete-orphan")


class PoliticalEvent(Base):
    """
    Ground-truth political and legislative events.
    """
    __tablename__ = "political_events"

    event_id = Column(String, primary_key=True, index=True)
    event_name = Column(String, nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    official_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article_links = relationship("ArticleEvent", back_populates="event", cascade="all, delete-orphan")


class Topic(Base):
    """
    Predefined news and policy topic taxonomy.
    """
    __tablename__ = "news_topics"

    topic_id = Column(String, primary_key=True, index=True)
    topic_code = Column(String, nullable=False, unique=True, index=True)
    topic_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    articles = relationship("ArticleTopic", back_populates="topic", cascade="all, delete-orphan")
    coverage_metrics = relationship("CoverageMetric", back_populates="topic", cascade="all, delete-orphan")


class ArticleEntity(Base):
    """
    Junction mapping articles to mentioned political entities with prominence and sentiment.
    """
    __tablename__ = "article_entities"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String, ForeignKey("political_entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    
    mention_count = Column(Integer, default=1)
    prominence_score = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)
    positions = Column(JSON, nullable=True)

    article = relationship("Article", back_populates="entities")
    entity = relationship("PoliticalEntity", back_populates="article_mentions")


class ArticleTopic(Base):
    """
    Junction mapping articles to civic topics.
    """
    __tablename__ = "article_topics"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String, ForeignKey("news_topics.topic_id", ondelete="CASCADE"), nullable=False, index=True)
    
    relevance_score = Column(Float, default=1.0)
    is_primary = Column(Boolean, default=True)

    article = relationship("Article", back_populates="topics")
    topic = relationship("Topic", back_populates="articles")


class ArticleEvent(Base):
    """
    Junction mapping articles to real-world political events.
    """
    __tablename__ = "article_events"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String, ForeignKey("political_events.event_id", ondelete="CASCADE"), nullable=False, index=True)
    
    relevance_score = Column(Float, default=1.0)
    role_in_event = Column(String, nullable=True)

    article = relationship("Article", back_populates="events")
    event = relationship("PoliticalEvent", back_populates="article_links")


class ArticleFeature(Base):
    """
    Extracted NLP linguistic signals and framing indicators for an article.
    """
    __tablename__ = "article_features"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    headline_sentiment = Column(Float, default=0.0)
    body_sentiment = Column(Float, default=0.0)
    stance_signals = Column(JSON, nullable=True)
    framing_indicators = Column(JSON, nullable=True)
    quote_count = Column(Integer, default=0)
    official_source_citation_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    vocabulary_richness = Column(Float, default=0.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article = relationship("Article", back_populates="features")


class CoverageMetric(Base):
    """
    Aggregated source-level metrics over time periods.
    """
    __tablename__ = "coverage_metrics"

    metric_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    time_period = Column(String, nullable=False, index=True)  # e.g., "2026-W11", "2026-03"
    topic_id = Column(String, ForeignKey("news_topics.topic_id", ondelete="SET NULL"), nullable=True, index=True)
    
    total_articles = Column(Integer, default=0)
    article_frequency = Column(Float, default=0.0)
    avg_prominence = Column(Float, default=0.0)
    avg_sentiment = Column(Float, default=0.0)
    metric_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source = relationship("NewsSource", back_populates="coverage_metrics")
    topic = relationship("Topic", back_populates="coverage_metrics")


class BiasIndicator(Base):
    """
    Multi-dimensional statistical indicators comparing news outlets.
    """
    __tablename__ = "bias_indicators"

    indicator_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    compare_source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=True, index=True)
    
    metric_type = Column(String, nullable=False, index=True)  # e.g. "framing_difference", "topic_emphasis", "entity_prominence"
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    
    indicator_value = Column(Float, nullable=False)
    statistical_confidence = Column(Float, default=1.0)
    interpretation_label = Column(String, nullable=False)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source = relationship("NewsSource", foreign_keys=[source_id], back_populates="bias_indicators")
    compare_source = relationship("NewsSource", foreign_keys=[compare_source_id])


class SourceSnapshot(Base):
    """
    Periodic point-in-time snapshot of source coverage distributions.
    """
    __tablename__ = "source_snapshots"

    snapshot_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    active_article_count = Column(Integer, default=0)
    coverage_distribution = Column(JSON, nullable=True)
    snapshot_data = Column(JSON, nullable=True)

    source = relationship("NewsSource", back_populates="snapshots")


class NewsIngestionFailure(Base):
    """
    Persistent record tracking failed article ingestion attempts (no silent drops).
    """
    __tablename__ = "news_ingestion_failures"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("news_sources.source_id", ondelete="CASCADE"), nullable=True, index=True)
    url = Column(String, nullable=False, index=True)
    failure_type = Column(String, nullable=False, index=True)  # HTTP_ERROR, PARSER_ERROR, EMPTY_CONTENT, ROBOTS_DISALLOWED, VALIDATION_ERROR
    error_details = Column(Text, nullable=True)
    raw_html_path = Column(String, nullable=True)
    failed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source = relationship("NewsSource")


class NewsProcessingQueue(Base):
    """
    Queue model managing downstream NLP analysis tasks for ingested articles.
    """
    __tablename__ = "news_processing_queue"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("news_articles.article_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="PENDING", index=True)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    attempts = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    article = relationship("Article")

