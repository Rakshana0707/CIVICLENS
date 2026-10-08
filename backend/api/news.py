from flask import Blueprint, request
from backend.database.session import SessionLocal
from backend.services.news_service import NewsService
from backend.services.event_comparison_service import EventCandidateDetector, CrossSourceEventComparer, EventComparisonService
from backend.services.bias_indicator_engine import BiasIndicatorEngine
from backend.models.news import NewsSource, Article, Topic, PoliticalEntity, PoliticalEvent, BiasIndicator, CoverageMetric, SourceComparison
from backend.api.responses import success_response, error_response

news_bp = Blueprint('news', __name__, url_prefix='/news')

@news_bp.route('/sources', methods=['GET'])
def get_sources():
    """List all registered news sources and media outlets."""
    db = SessionLocal()
    try:
        sources = db.query(NewsSource).all()
        data = [{
            "source_id": s.source_id,
            "source_name": s.source_name,
            "domain": s.domain,
            "language": s.language,
            "source_type": s.source_type.value if hasattr(s.source_type, 'value') else str(s.source_type),
            "official_url": s.official_url,
            "active_status": s.active_status.value if hasattr(s.active_status, 'value') else str(s.active_status),
            "priority": s.priority
        } for s in sources]
        return success_response(data=data, message="News sources retrieved successfully")
    finally:
        db.close()

@news_bp.route('/sources', methods=['POST'])
def register_source():
    """Register a new media outlet or government portal."""
    payload = request.get_json() or {}
    if not payload.get("source_id") or not payload.get("source_name") or not payload.get("domain"):
        return error_response(message="Missing required fields: source_id, source_name, domain", status_code=400)

    db = SessionLocal()
    try:
        service = NewsService(db)
        source = service.register_source(
            source_id=payload["source_id"],
            source_name=payload["source_name"],
            domain=payload["domain"],
            language=payload.get("language", "ta"),
            official_url=payload.get("official_url"),
            selector_config=payload.get("selector_config")
        )
        return success_response(
            data={"source_id": source.source_id, "source_name": source.source_name},
            message="News source registered successfully",
            status_code=21
        )
    except Exception as e:
        return error_response(message=f"Failed to register source: {str(e)}", status_code=500)
    finally:
        db.close()

@news_bp.route('/articles', methods=['GET'])
def get_articles():
    """Search and filter news articles by source, language, topic, entity, or search term."""
    source_id = request.args.get('source_id')
    language = request.args.get('language')
    limit = int(request.args.get('limit', 20))

    db = SessionLocal()
    try:
        query = db.query(Article)
        if source_id:
            query = query.filter(Article.source_id == source_id)
        if language:
            query = query.filter(Article.language == language)

        articles = query.order_by(Article.publication_date.desc()).limit(limit).all()
        data = [{
            "article_id": a.article_id,
            "source_id": a.source_id,
            "title": a.title,
            "url": a.url,
            "author": a.author,
            "publication_date": a.publication_date.isoformat() if a.publication_date else None,
            "language": a.language,
            "word_count": a.word_count,
            "is_test_fixture": a.is_test_fixture
        } for a in articles]
        return success_response(data=data, message="Articles retrieved successfully")
    finally:
        db.close()

@news_bp.route('/articles/<article_id>', methods=['GET'])
def get_article_detail(article_id):
    """Retrieve detailed information, NLP features, mentioned entities, and topics for an article."""
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.article_id == article_id).first()
        if not article:
            return error_response(message=f"Article '{article_id}' not found", status_code=404)

        data = {
            "article_id": article.article_id,
            "source_id": article.source_id,
            "title": article.title,
            "url": article.url,
            "author": article.author,
            "publication_date": article.publication_date.isoformat() if article.publication_date else None,
            "language": article.language,
            "article_text": article.article_text,
            "word_count": article.word_count,
            "text_hash": article.text_hash,
            "is_test_fixture": article.is_test_fixture,
            "entities": [{
                "entity_id": e.entity_id,
                "mention_count": e.mention_count,
                "prominence_score": e.prominence_score
            } for e in article.entities],
            "topics": [{
                "topic_id": t.topic_id,
                "relevance_score": t.relevance_score,
                "is_primary": t.is_primary
            } for t in article.topics],
            "features": {
                "headline_sentiment": article.features.headline_sentiment,
                "body_sentiment": article.features.body_sentiment,
                "quote_count": article.features.quote_count,
                "official_source_citation_count": article.features.official_source_citation_count,
                "vocabulary_richness": article.features.vocabulary_richness,
                "framing_indicators": article.features.framing_indicators
            } if article.features else None
        }
        return success_response(data=data, message="Article details retrieved successfully")
    finally:
        db.close()

@news_bp.route('/topics', methods=['GET'])
def get_topics():
    """Retrieve news topic taxonomy."""
    db = SessionLocal()
    try:
        topics = db.query(Topic).all()
        data = [{
            "topic_id": t.topic_id,
            "topic_code": t.topic_code,
            "topic_name": t.topic_name,
            "description": t.description
        } for t in topics]
        return success_response(data=data, message="Topics retrieved successfully")
    finally:
        db.close()

@news_bp.route('/entities', methods=['GET'])
def get_entities():
    """Retrieve political entities, persons, and parties."""
    db = SessionLocal()
    try:
        entities = db.query(PoliticalEntity).all()
        data = [{
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "name": e.name,
            "normalized_name": e.normalized_name
        } for e in entities]
        return success_response(data=data, message="Entities retrieved successfully")
    finally:
        db.close()

@news_bp.route('/events', methods=['GET'])
def get_events():
    """Retrieve political and legislative ground-truth events."""
    db = SessionLocal()
    try:
        events = db.query(PoliticalEvent).all()
        data = [{
            "event_id": e.event_id,
            "event_name": e.event_name,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "location": e.location,
            "description": e.description,
            "official_reference": e.official_reference
        } for e in events]
        return success_response(data=data, message="Political events retrieved successfully")
    finally:
        db.close()

@news_bp.route('/events/candidates', methods=['GET'])
def get_event_candidates():
    """Detect candidate political event clusters from recent articles."""
    days_window = int(request.args.get('days_window', 3))
    db = SessionLocal()
    try:
        detector = EventCandidateDetector()
        candidates = detector.find_candidates(db, days_window=days_window)
        formatted = [{
            "cluster_id": c["cluster_id"],
            "title_sample": c["title_sample"],
            "article_count": c["article_count"],
            "article_ids": c["article_ids"]
        } for c in candidates]
        return success_response(data=formatted, message="Event candidates detected successfully")
    finally:
        db.close()

@news_bp.route('/events/<event_id>/compare', methods=['GET'])
def compare_event_coverage(event_id):
    """Compare multi-dimensional coverage across media outlets for a given political event."""
    db = SessionLocal()
    try:
        comparer = CrossSourceEventComparer()
        comparison = comparer.compare_event_coverage(db, event_id)
        if "error" in comparison:
            return error_response(message=comparison["error"], status_code=404)
        return success_response(data=comparison, message="Event coverage comparison calculated successfully")
    finally:
        db.close()

@news_bp.route('/events/disparities', methods=['GET'])
def get_coverage_disparities():
    """Retrieve multi-dimensional cross-source coverage disparities across all events."""
    db = SessionLocal()
    try:
        service = EventComparisonService(db)
        results = service.run_event_analysis_pipeline()
        disparities = []
        for res in results:
            for disp in res.get("coverage_disparities", []):
                disp["event_id"] = res["event_id"]
                disp["event_name"] = res["event_name"]
                disparities.append(disp)
        return success_response(data=disparities, message="Coverage disparities retrieved successfully")
    finally:
        db.close()

@news_bp.route('/compare', methods=['GET'])
def compare_sources():
    """Cross-source comparison API across media outlets."""
    source_a = request.args.get('source_a')
    source_b = request.args.get('source_b')

    db = SessionLocal()
    try:
        service = NewsService(db)
        indicators_a = service.calculate_bias_indicators(source_a) if source_a else []
        indicators_b = service.calculate_bias_indicators(source_b) if source_b else []

        data = {
            "source_a": source_a,
            "source_b": source_b,
            "indicators_a": [{
                "indicator_id": ind.indicator_id,
                "metric_type": ind.metric_type,
                "indicator_value": ind.indicator_value,
                "interpretation_label": ind.interpretation_label
            } for ind in indicators_a],
            "indicators_b": [{
                "indicator_id": ind.indicator_id,
                "metric_type": ind.metric_type,
                "indicator_value": ind.indicator_value,
                "interpretation_label": ind.interpretation_label
            } for ind in indicators_b]
        }
        return success_response(data=data, message="Cross-source comparison calculated successfully")
    finally:
        db.close()

@news_bp.route('/bias-indicators', methods=['GET'])
def get_bias_indicators():
    """Retrieve multi-dimensional statistical indicators using neutral language."""
    source_id = request.args.get('source_id')
    db = SessionLocal()
    try:
        query = db.query(BiasIndicator)
        if source_id:
            query = query.filter(BiasIndicator.source_id == source_id)
        indicators = query.all()

        data = [{
            "indicator_id": ind.indicator_id,
            "source_id": ind.source_id,
            "compare_source_id": ind.compare_source_id,
            "metric_type": ind.metric_type,
            "indicator_value": ind.indicator_value,
            "statistical_confidence": ind.statistical_confidence,
            "interpretation_label": ind.interpretation_label,
            "methodology_version": getattr(ind, 'methodology_version', 'v1.0'),
            "calculation_version": getattr(ind, 'calculation_version', 'v1.0'),
            "metadata_json": ind.metadata_json
        } for ind in indicators]
        return success_response(data=data, message="Bias indicators retrieved successfully")
    finally:
        db.close()

@news_bp.route('/indicators/calculate', methods=['POST'])
def calculate_indicators():
    """Trigger calculation and persistence of 12 multi-dimensional bias indicators for a news source."""
    payload = request.get_json() or {}
    source_id = payload.get("source_id")
    days_window = int(payload.get("days_window", 30))
    if not source_id:
        return error_response(message="Missing required field: source_id", status_code=400)

    db = SessionLocal()
    try:
        engine = BiasIndicatorEngine(db)
        indicators = engine.generate_and_persist_source_indicators(source_id, days_window=days_window)
        data = [{
            "indicator_id": ind.indicator_id,
            "metric_type": ind.metric_type,
            "indicator_value": ind.indicator_value,
            "statistical_confidence": ind.statistical_confidence,
            "methodology_version": ind.methodology_version,
            "calculation_version": ind.calculation_version,
            "metadata": ind.metadata_json
        } for ind in indicators]
        return success_response(data=data, message="Multi-dimensional bias indicators calculated successfully")
    finally:
        db.close()

@news_bp.route('/metrics/coverage', methods=['GET'])
def get_coverage_metrics():
    """Retrieve aggregated source-level coverage metrics and topic emphasis."""
    source_id = request.args.get('source_id')
    db = SessionLocal()
    try:
        query = db.query(CoverageMetric)
        if source_id:
            query = query.filter(CoverageMetric.source_id == source_id)
        metrics = query.all()
        data = [{
            "metric_id": m.metric_id,
            "source_id": m.source_id,
            "time_period": m.time_period,
            "total_articles": m.total_articles,
            "article_frequency": m.article_frequency,
            "avg_sentiment": m.avg_sentiment,
            "methodology_version": m.methodology_version,
            "calculation_version": m.calculation_version,
            "metric_data": m.metric_data
        } for m in metrics]
        return success_response(data=data, message="Coverage metrics retrieved successfully")
    finally:
        db.close()

@news_bp.route('/comparisons', methods=['GET'])
def get_source_comparisons():
    """Retrieve or generate pairwise source comparison metrics."""
    source_a = request.args.get('source_a')
    source_b = request.args.get('source_b')
    days_window = int(request.args.get('days_window', 30))

    db = SessionLocal()
    try:
        engine = BiasIndicatorEngine(db)
        if source_a and source_b:
            comparison = engine.generate_and_persist_comparison(source_a, source_b, days_window=days_window)
            data = {
                "comparison_id": comparison.comparison_id,
                "source_a_id": comparison.source_a_id,
                "source_b_id": comparison.source_b_id,
                "wording_similarity_score": comparison.wording_similarity_score,
                "topic_emphasis_divergence": comparison.topic_emphasis_divergence,
                "entity_prominence_divergence": comparison.entity_prominence_divergence,
                "framing_divergence": comparison.framing_divergence,
                "coverage_difference_score": comparison.coverage_difference_score,
                "methodology_version": comparison.methodology_version,
                "calculation_version": comparison.calculation_version,
                "comparison_data": comparison.comparison_data
            }
        else:
            records = db.query(SourceComparison).all()
            data = [{
                "comparison_id": c.comparison_id,
                "source_a_id": c.source_a_id,
                "source_b_id": c.source_b_id,
                "wording_similarity_score": c.wording_similarity_score,
                "framing_divergence": c.framing_divergence,
                "coverage_difference_score": c.coverage_difference_score,
                "methodology_version": c.methodology_version,
                "calculation_version": c.calculation_version
            } for c in records]
        return success_response(data=data, message="Source comparisons retrieved successfully")
    finally:
        db.close()
