import requests
import logging
from typing import Dict, Any, Tuple, List, Optional
from frontend.config import settings

logger = logging.getLogger(__name__)

class APIClient:
    """
    Centralized Frontend API Client for communicating with the CivicLens Backend.
    Handles network requests, standardized JSON unwrapping, and error capturing.
    """
    def __init__(self, base_url: str = settings.BACKEND_ROOT_URL):
        self.base_url = base_url.rstrip("/")
        
    def _handle_response(self, response: requests.Response) -> Tuple[bool, Dict[str, Any]]:
        """Standardized response handler parsing our backend's success/error format."""
        try:
            data = response.json()
        except Exception:
            data = {"message": "Invalid JSON response from server."}
            
        if response.ok and data.get("status") == "success":
            return True, data.get("data", {})
        else:
            logger.error(f"API Error: {response.status_code} - {data.get('message')}")
            return False, data
            
    def get_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Check if the backend application is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            logger.error(f"Backend connection failed: {e}")
            return False, {"message": f"Connection failed: {str(e)}"}

    def get_db_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Check if backend database is reachable."""
        try:
            response = requests.get(f"{self.base_url}/health/db", timeout=5)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": f"DB Connection failed: {str(e)}"}

    def get_budget_years(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/budget/years", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}
            
    def get_budget_departments(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/budget/departments", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_budget_schemes(self, department_id: int = None) -> Tuple[bool, Any]:
        params = {}
        if department_id is not None:
            params['department_id'] = department_id
        try:
            response = requests.get(f"{self.base_url}/api/budget/schemes", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_budget_records(self, skip: int = 0, limit: int = 50, filters: Dict = None) -> Tuple[bool, Any]:
        params = {"skip": skip, "limit": limit}
        if filters:
            for k, v in filters.items():
                if v:
                    params[k] = v
        try:
            response = requests.get(f"{self.base_url}/api/budget/records", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_budget_trend(self, budget_stage: str, department_id: int = None, scheme_id: int = None) -> Tuple[bool, Any]:
        params = {"budget_stage": budget_stage}
        if department_id is not None:
            params["department_id"] = department_id
        if scheme_id is not None:
            params["scheme_id"] = scheme_id
        try:
            response = requests.get(f"{self.base_url}/api/budget/analysis/trend", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_scheme_trends(self, budget_stage: str, department_id: int = None) -> Tuple[bool, Any]:
        params = {"budget_stage": budget_stage}
        if department_id is not None:
            params["department_id"] = department_id
        try:
            response = requests.get(f"{self.base_url}/api/budget/analysis/scheme-trends", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_ml_clustering(self, budget_stage: str, algorithm: str = 'kmeans', department_id: int = None, **kwargs) -> Tuple[bool, Any]:
        params = {
            'budget_stage': budget_stage,
            'algorithm': algorithm
        }
        if department_id is not None:
            params['department_id'] = department_id
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v
        try:
            response = requests.get(f"{self.base_url}/api/ml/budget/clustering", params=params, timeout=20)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}
            
    def get_ml_anomaly(self, budget_stage: str, contamination: str = 'auto', department_id: int = None, **kwargs) -> Tuple[bool, Any]:
        params = {
            'budget_stage': budget_stage,
            'contamination': contamination
        }
        if department_id is not None:
            params['department_id'] = department_id
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v
        try:
            response = requests.get(f"{self.base_url}/api/ml/budget/anomaly", params=params, timeout=20)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_departments(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/budget/departments", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def search_schemes(self, name=None, description=None, year=None, department_id=None, category_id=None, page=1, limit=50) -> Tuple[bool, Any]:
        params = {"page": page, "limit": limit}
        if name: params["name"] = name
        if description: params["description"] = description
        if year and year != "All": params["year"] = year
        if department_id and department_id != 0: params["department_id"] = department_id
        if category_id and category_id != 0: params["category_id"] = category_id
        
        try:
            response = requests.get(f"{self.base_url}/api/schemes/search", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_scheme(self, scheme_id) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/schemes/{scheme_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_scheme_history(self, scheme_id) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/schemes/{scheme_id}/history", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_scheme_sources(self, scheme_id) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/schemes/{scheme_id}/sources", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_scheme_categories(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/schemes/categories", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_similar_schemes(self, scheme_id, top_k=5, threshold=0.3, page=1, department_id=None, year=None, category_id=None) -> Tuple[bool, Any]:
        params = {"top_k": top_k, "threshold": threshold, "page": page}
        if department_id and department_id != 0: params["department_id"] = department_id
        if year and year != "All": params["year"] = year
        if category_id and category_id != 0: params["category_id"] = category_id
        
        try:
            response = requests.get(f"{self.base_url}/api/schemes/{scheme_id}/similar", params=params, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def semantic_search_schemes(self, query, top_k=5, threshold=0.3, page=1, department_id=None, year=None, category_id=None) -> Tuple[bool, Any]:
        params = {"query": query, "top_k": top_k, "threshold": threshold, "page": page}
        if department_id and department_id != 0: params["department_id"] = department_id
        if year and year != "All": params["year"] = year
        if category_id and category_id != 0: params["category_id"] = category_id
        
        try:
            response = requests.get(f"{self.base_url}/api/schemes/semantic_search", params=params, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def compare_schemes(self, scheme_ids: List[int]) -> Tuple[bool, Any]:
        try:
            ids_str = ",".join(map(str, scheme_ids))
            response = requests.get(f"{self.base_url}/api/schemes/compare", params={"ids": ids_str}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def analyze_scheme_themes(self, n_clusters: int = 5, department_id: int = None) -> Tuple[bool, Any]:
        params = {"n_clusters": n_clusters}
        if department_id and department_id != 0:
            params["department_id"] = department_id
            
        try:
            response = requests.get(f"{self.base_url}/api/schemes/themes", params=params, timeout=30)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # -----------------------------------------------------------------------
    # POLITICAL PROMISE TRACKER API METHODS (PHASE 3)
    # -----------------------------------------------------------------------
    def get_promise_parties(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/parties", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_elections(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/elections", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_categories(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/categories", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promises(
        self,
        party: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        language: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[bool, Any]:
        params = {"page": page, "limit": limit}
        if party and party != "All": params["party"] = party
        if year and year != "All": params["election_year"] = year
        if category and category != "All": params["category"] = category
        if status and status != "All": params["status"] = status
        if classification and classification != "All": params["classification"] = classification
        if language and language != "All": params["language"] = language
        if search: params["search"] = search

        try:
            response = requests.get(f"{self.base_url}/api/promises/", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_detail(self, promise_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/{promise_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_scheme_matches(self, promise_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/{promise_id}/scheme-matches", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_evidence_matches(self, promise_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/{promise_id}/evidence-matches", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_assessment(self, promise_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/{promise_id}/assessment", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_history(self, promise_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/{promise_id}/history", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_promise_sources(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/promises/sources", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # -----------------------------------------------------------------------
    # TAMIL NEWS ANALYZER API METHODS (PHASE 4)
    # -----------------------------------------------------------------------
    def get_news_sources(self, language: str = None, source_type: str = None, active_status: str = None) -> Tuple[bool, Any]:
        params = {}
        if language and language != "All": params["language"] = language
        if source_type and source_type != "All": params["source_type"] = source_type
        if active_status and active_status != "All": params["active_status"] = active_status
        try:
            response = requests.get(f"{self.base_url}/api/news/sources", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_articles(
        self,
        source_id: Optional[str] = None,
        language: Optional[str] = None,
        date: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        topic_id: Optional[str] = None,
        party_id: Optional[str] = None,
        person_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        event_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[bool, Any]:
        params = {"limit": limit, "offset": offset}
        if source_id and source_id != "All": params["source_id"] = source_id
        if language and language != "All": params["language"] = language
        if date: params["date"] = date
        if date_from: params["date_from"] = date_from
        if date_to: params["date_to"] = date_to
        if topic_id and topic_id != "All": params["topic"] = topic_id
        if party_id and party_id != "All": params["party"] = party_id
        if person_id and person_id != "All": params["person"] = person_id
        if entity_id and entity_id != "All": params["entity_id"] = entity_id
        if event_id and event_id != "All": params["event"] = event_id
        if search: params["search"] = search

        try:
            response = requests.get(f"{self.base_url}/api/news/articles", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_article_detail(self, article_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/news/articles/{article_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_topics(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/news/topics", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_entities(self, entity_type: str = None, search: str = None) -> Tuple[bool, Any]:
        params = {}
        if entity_type and entity_type != "All": params["entity_type"] = entity_type
        if search: params["search"] = search
        try:
            response = requests.get(f"{self.base_url}/api/news/entities", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_events(self, date: str = None, search: str = None) -> Tuple[bool, Any]:
        params = {}
        if date: params["date"] = date
        if search: params["search"] = search
        try:
            response = requests.get(f"{self.base_url}/api/news/events", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_event_detail(self, event_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/news/events/{event_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_coverage(self, source_id: str = None, time_period: str = None, topic_id: str = None) -> Tuple[bool, Any]:
        params = {}
        if source_id and source_id != "All": params["source_id"] = source_id
        if time_period: params["time_period"] = time_period
        if topic_id and topic_id != "All": params["topic_id"] = topic_id
        try:
            response = requests.get(f"{self.base_url}/api/news/coverage", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_source_comparison(self, source_a: str = None, source_b: str = None, days_window: int = 30) -> Tuple[bool, Any]:
        params = {"days_window": days_window}
        if source_a: params["source_a"] = source_a
        if source_b: params["source_b"] = source_b
        try:
            response = requests.get(f"{self.base_url}/api/news/source-comparison", params=params, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_news_bias_indicators(self, source_id: str = None, metric_type: str = None, min_confidence: float = 0.0) -> Tuple[bool, Any]:
        params = {"min_confidence": min_confidence}
        if source_id and source_id != "All": params["source_id"] = source_id
        if metric_type and metric_type != "All": params["metric_type"] = metric_type
        try:
            response = requests.get(f"{self.base_url}/api/news/bias-indicators", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def calculate_news_indicators(self, source_id: str, days_window: int = 30) -> Tuple[bool, Any]:
        try:
            response = requests.post(f"{self.base_url}/api/news/indicators/calculate", json={"source_id": source_id, "days_window": days_window}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # -----------------------------------------------------------------------
    # POLITICAL FUNDING TRANSPARENCY API METHODS (PHASE 5)
    # -----------------------------------------------------------------------
    def get_funding_parties(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/funding/parties", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_party_profile(self, party_id: str, financial_year: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        try:
            response = requests.get(f"{self.base_url}/api/funding/parties/{party_id}/profile", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_contribution_summary(self, party_id: Optional[str] = None, financial_year: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        try:
            response = requests.get(f"{self.base_url}/api/funding/contributions/summary", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_income_expenditure(self, party_id: Optional[str] = None, financial_year: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        try:
            response = requests.get(f"{self.base_url}/api/funding/metrics/income-expenditure", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_electoral_trusts(self, party_id: Optional[str] = None, financial_year: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        try:
            response = requests.get(f"{self.base_url}/api/funding/electoral-trusts", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_election_expenditure(self, party_id: Optional[str] = None, election_name: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if election_name and election_name != "All": params["election_name"] = election_name
        try:
            response = requests.get(f"{self.base_url}/api/funding/election-expenditure", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_anomalies(self, party_id: Optional[str] = None, financial_year: Optional[str] = None, review_status: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        if review_status and review_status != "All": params["review_status"] = review_status
        try:
            response = requests.get(f"{self.base_url}/api/funding/anomalies", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_cross_validation(self, party_id: Optional[str] = None, financial_year: Optional[str] = None, validation_status: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        if validation_status and validation_status != "All": params["validation_status"] = validation_status
        try:
            response = requests.get(f"{self.base_url}/api/funding/cross-validation", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_documents(self, party_id: Optional[str] = None, financial_year: Optional[str] = None, filing_type: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if party_id and party_id != "All": params["party_id"] = party_id
        if financial_year and financial_year != "All": params["financial_year"] = financial_year
        if filing_type and filing_type != "All": params["filing_type"] = filing_type
        try:
            response = requests.get(f"{self.base_url}/api/funding/documents", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_funding_sources(self) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/funding/sources", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # ---------------------------------------------------------------------------
    # PHASE 6: REPRESENTATIVES & CONSTITUENCY PERFORMANCE
    # ---------------------------------------------------------------------------
    def search_representatives(
        self,
        q: Optional[str] = None,
        rep_type: Optional[str] = None,
        party_id: Optional[str] = None,
        constituency_id: Optional[str] = None,
        active_only: bool = False
    ) -> Tuple[bool, Any]:
        params = {}
        if q: params["q"] = q
        if rep_type and rep_type != "All": params["type"] = rep_type
        if party_id and party_id != "All": params["party_id"] = party_id
        if constituency_id and constituency_id != "All": params["constituency_id"] = constituency_id
        if active_only: params["active_only"] = "true"
        try:
            response = requests.get(f"{self.base_url}/api/representatives/search", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_representative_profile(self, representative_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/{representative_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def list_constituencies(self, district: Optional[str] = None, c_type: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if district and district != "All": params["district"] = district
        if c_type and c_type != "All": params["type"] = c_type
        try:
            response = requests.get(f"{self.base_url}/api/representatives/constituencies", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_constituency_profile(self, constituency_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/constituencies/{constituency_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_representative_legislative_activity(self, representative_id: str, period: str = "2021-2026") -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/{representative_id}/legislative", params={"period": period}, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_constituency_works(
        self,
        constituency_id: Optional[str] = None,
        representative_id: Optional[str] = None,
        scheme_id: Optional[str] = None,
        status: Optional[str] = None,
        attribution: Optional[str] = None
    ) -> Tuple[bool, Any]:
        params = {}
        if constituency_id and constituency_id != "All": params["constituency_id"] = constituency_id
        if representative_id and representative_id != "All": params["representative_id"] = representative_id
        if scheme_id and scheme_id != "All": params["scheme_id"] = scheme_id
        if status and status != "All": params["status"] = status
        if attribution and attribution != "All": params["attribution"] = attribution
        try:
            response = requests.get(f"{self.base_url}/api/representatives/works", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_development_indicators(
        self,
        unit_id: Optional[str] = None,
        indicator_name: Optional[str] = None,
        baseline: str = "2011",
        current: str = "2021"
    ) -> Tuple[bool, Any]:
        params = {"baseline": baseline, "current": current}
        if unit_id and unit_id != "All": params["unit_id"] = unit_id
        if indicator_name and indicator_name != "All": params["indicator_name"] = indicator_name
        try:
            response = requests.get(f"{self.base_url}/api/representatives/indicators", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_representative_promises(self, representative_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/{representative_id}/promises", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def compare_representatives(self, representatives: List[str], cohort_type: str = "TN_ASSEMBLY_MLA", reporting_period: str = "2021-2024") -> Tuple[bool, Any]:
        payload = {
            "representatives": representatives,
            "cohort_type": cohort_type,
            "reporting_period": reporting_period
        }
        try:
            response = requests.post(f"{self.base_url}/api/representatives/compare", json=payload, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_transparent_composite(self, representative_id: str, period: str = "2021-2024") -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/{representative_id}/composite", params={"period": period}, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_data_completeness(self, representative_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/{representative_id}/completeness", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # ---------------------------------------------------------------------------
    # PHASE 6.11: EVIDENCE TRACEABILITY & AUDIT TRAIL
    # ---------------------------------------------------------------------------
    def get_source_documents(self, publisher: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if publisher and publisher != "All": params["publisher"] = publisher
        try:
            response = requests.get(f"{self.base_url}/api/representatives/sources", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_source_document_detail(self, document_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/sources/{document_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_entity_evidence(self, entity_type: str, entity_id: str) -> Tuple[bool, Any]:
        params = {"entity_type": entity_type, "entity_id": entity_id}
        try:
            response = requests.get(f"{self.base_url}/api/representatives/evidence", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_metric_lineage(self, metric_id: str) -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/representatives/metrics/{metric_id}/lineage", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_conflicting_evidence(self, entity_type: Optional[str] = None) -> Tuple[bool, Any]:
        params = {}
        if entity_type and entity_type != "All": params["entity_type"] = entity_type
        try:
            response = requests.get(f"{self.base_url}/api/representatives/conflicts", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_audit_trail(self, record_id: Optional[str] = None, limit: int = 50) -> Tuple[bool, Any]:
        params = {"limit": limit}
        if record_id: params["record_id"] = record_id
        try:
            response = requests.get(f"{self.base_url}/api/representatives/audit-trail", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # -------------------------------------------------------------------------
    # PHASE 7 — CLAIM VERIFICATION API CLIENT METHODS
    # -------------------------------------------------------------------------
    def search_claims(self, q: Optional[str] = None, category: Optional[str] = None,
                      status: Optional[str] = None, outcome: Optional[str] = None,
                      party: Optional[str] = None, speaker: Optional[str] = None,
                      language: Optional[str] = None, rep_id: Optional[str] = None,
                      promise_id: Optional[str] = None, scheme_id: Optional[int] = None,
                      news_id: Optional[str] = None, funding_id: Optional[str] = None,
                      skip: int = 0, limit: int = 50) -> Tuple[bool, Any]:
        """Search and filter claims from Phase 7 claim registry."""
        params: Dict[str, Any] = {"skip": skip, "limit": limit}
        if q: params["q"] = q
        if category and category != "All": params["category"] = category
        if status and status != "All": params["status"] = status
        if outcome and outcome != "All": params["outcome"] = outcome
        if party and party != "All": params["party"] = party
        if speaker: params["speaker"] = speaker
        if language and language != "All": params["language"] = language
        if rep_id: params["representative_id"] = rep_id
        if promise_id: params["promise_id"] = promise_id
        if scheme_id: params["scheme_id"] = scheme_id
        if news_id: params["news_article_id"] = news_id
        if funding_id: params["financial_document_id"] = funding_id
        try:
            response = requests.get(f"{self.base_url}/api/claims/search", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_detail(self, claim_id: str) -> Tuple[bool, Any]:
        """Get full details of a registered claim including cross-phase resolutions."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_atomic_claim_detail(self, claim_id: str, atomic_claim_id: str) -> Tuple[bool, Any]:
        """Get granular decomposed atomic claim profile."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/atomic/{atomic_claim_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def search_evidence(self, q: Optional[str] = None, doc_type: Optional[str] = None,
                        source_category: Optional[str] = None, publisher: Optional[str] = None,
                        skip: int = 0, limit: int = 50) -> Tuple[bool, Any]:
        """Search through verified evidence documents and passages."""
        params: Dict[str, Any] = {"skip": skip, "limit": limit}
        if q: params["q"] = q
        if doc_type and doc_type != "All": params["document_type"] = doc_type
        if source_category and source_category != "All": params["source_category"] = source_category
        if publisher: params["publisher"] = publisher
        try:
            response = requests.get(f"{self.base_url}/api/claims/evidence/search", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_evidence_document(self, document_id: str) -> Tuple[bool, Any]:
        """Get evidence document details and passages."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/evidence/documents/{document_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_relationships(self, claim_id: str) -> Tuple[bool, Any]:
        """Get claim-to-evidence relationships for all atomic propositions."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/relationships", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_verification(self, claim_id: str) -> Tuple[bool, Any]:
        """Get latest verification outcome, explanation, and evidence references."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/verification", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_history(self, claim_id: str) -> Tuple[bool, Any]:
        """Get chronological audit history of automated runs and human reviews."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/history", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def submit_claim_review(self, claim_id: str, payload: Dict[str, Any], reviewer_role: str = "SENIOR_FACT_CHECKER") -> Tuple[bool, Any]:
        """Submit a peer-reviewed human verdict revision or confirmation."""
        headers = {"X-Reviewer-Role": reviewer_role}
        try:
            response = requests.post(f"{self.base_url}/api/claims/{claim_id}/review", json=payload, headers=headers, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_source(self, source_id: str) -> Tuple[bool, Any]:
        """Get source registry information for a claim."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/sources/{source_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_provenance(self, claim_id: str) -> Tuple[bool, Any]:
        """Get full provenance record of a claim and its origin document."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/provenance", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_claim_cross_phase(self, claim_id: str) -> Tuple[bool, Any]:
        """Get cross-phase associations linked to a claim."""
        try:
            response = requests.get(f"{self.base_url}/api/claims/{claim_id}/cross-phase", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # -------------------------------------------------------------------------
    # PHASE 8: CIVIC ISSUE INTELLIGENCE ENDPOINTS
    # -------------------------------------------------------------------------
    def get_civic_issues(self, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        """List and search civic issues with multi-attribute filters."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_issue_detail(self, issue_id: str) -> Tuple[bool, Any]:
        """Get full issue details, department, area, metrics, and cross-phase links."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues/{issue_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_categories(self) -> Tuple[bool, Any]:
        """List canonical categories with SLA standards and issue counts."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/categories", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_areas(self) -> Tuple[bool, Any]:
        """List administrative areas with population and tier context."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/areas", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_departments(self) -> Tuple[bool, Any]:
        """List departments with docket counts and resolution stats."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/departments", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_department_summary(self, department_id: str) -> Tuple[bool, Any]:
        """Detailed department performance summary & SLA compliance."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/departments/{department_id}/summary", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_responses(self, issue_id: str) -> Tuple[bool, Any]:
        """Response history and action-taken reports for an issue."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues/{issue_id}/responses", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_evidence(self, issue_id: str) -> Tuple[bool, Any]:
        """Resolution evidence artifacts (empirical proof) for an issue."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues/{issue_id}/evidence", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_clusters(self) -> Tuple[bool, Any]:
        """Recurring issue hotspots by administrative area and category."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/clusters", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_trends(self, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        """Trend analytics across core metrics with guarded anomaly detection."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/analytics/trends", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_source_documents(self) -> Tuple[bool, Any]:
        """Statutory gazettes, council proceedings, and data dumps."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/source-documents", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_issue_source_documents(self, issue_id: str) -> Tuple[bool, Any]:
        """Source documents linked directly to an issue."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues/{issue_id}/source-documents", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_civic_cross_phase(self, issue_id: str) -> Tuple[bool, Any]:
        """Cross-phase associations linked to an issue."""
        try:
            response = requests.get(f"{self.base_url}/api/civic/issues/{issue_id}/cross-phase", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # =========================================================================
    # PHASE 9: UNIFIED CIVIC INTELLIGENCE AND EVIDENCE GRAPH
    # =========================================================================

    def search_graph_entities(
        self,
        query: str = "",
        entity_type: Optional[str] = None,
        source_phase: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Search canonical entities across Phases 1–8 in the Civic Evidence Graph."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            params["q"] = query
        if entity_type:
            params["entity_type"] = entity_type
        if source_phase:
            params["source_phase"] = source_phase
        try:
            response = requests.get(f"{self.base_url}/api/graph/entities/search", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_node(self, node_id: str) -> Tuple[bool, Any]:
        """Retrieve full canonical node profile, aliases, and source mappings."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/nodes/{node_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Retrieve directly connected neighbor entities and connecting edges."""
        params: Dict[str, Any] = {"direction": direction, "limit": limit, "offset": offset}
        if relationship_type:
            params["relationship_type"] = relationship_type
        if target_type:
            params["target_type"] = target_type
        try:
            response = requests.get(f"{self.base_url}/api/graph/nodes/{node_id}/neighbors", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def traverse_graph(
        self,
        start_node_id: str,
        max_depth: int = 3,
        allowed_relationship_types: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> Tuple[bool, Any]:
        """Traverse multi-hop explainable paths from a start node."""
        params: Dict[str, Any] = {
            "start_node_id": start_node_id,
            "max_depth": max_depth,
            "min_confidence": min_confidence,
            "limit": limit,
        }
        if allowed_relationship_types:
            params["allowed_relationship_types"] = allowed_relationship_types
        try:
            response = requests.get(f"{self.base_url}/api/graph/traverse", params=params, timeout=12)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def investigate_graph_mode(
        self,
        mode: str,
        start_node_id: str,
        max_depth: int = 4,
        limit: int = 20,
    ) -> Tuple[bool, Any]:
        """Execute structured investigation walkthrough (promise_delivery, claim_verification, etc.)."""
        params: Dict[str, Any] = {
            "start_node_id": start_node_id,
            "max_depth": max_depth,
            "limit": limit,
        }
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/{mode}", params=params, timeout=12)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_edges(
        self,
        relationship_type: Optional[str] = None,
        matching_method: Optional[str] = None,
        review_status: Optional[str] = None,
        source_document_id: Optional[str] = None,
        min_confidence: float = 0.0,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Filter graph edges by relationship type, review status, and document references."""
        params: Dict[str, Any] = {
            "active_only": str(active_only).lower(),
            "limit": limit,
            "offset": offset,
        }
        if relationship_type:
            params["relationship_type"] = relationship_type
        if matching_method:
            params["matching_method"] = matching_method
        if review_status:
            params["review_status"] = review_status
        if source_document_id:
            params["source_document_id"] = source_document_id
        if min_confidence > 0.0:
            params["min_confidence"] = min_confidence
        try:
            response = requests.get(f"{self.base_url}/api/graph/edges", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_edge(self, edge_id: str) -> Tuple[bool, Any]:
        """Retrieve full evidence details, source hash, and quality scorecard for an edge."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/edges/{edge_id}", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_unresolved_proposals(
        self,
        min_confidence: float = 0.0,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """List unreviewed relationship candidates pending human audit."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if min_confidence > 0.0:
            params["min_confidence"] = min_confidence
        try:
            response = requests.get(f"{self.base_url}/api/graph/proposals/unresolved", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_conflicts(
        self,
        node_id: Optional[str] = None,
        conflict_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Retrieve persistent conflicts and contradictory evidence."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if node_id:
            params["node_id"] = node_id
        if conflict_type:
            params["conflict_type"] = conflict_type
        if severity:
            params["severity"] = severity
        try:
            response = requests.get(f"{self.base_url}/api/graph/conflicts", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_disputes(
        self,
        node_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Retrieve edges with DISPUTED provenance status."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if node_id:
            params["node_id"] = node_id
        try:
            response = requests.get(f"{self.base_url}/api/graph/disputes", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_history(
        self,
        node_id: Optional[str] = None,
        edge_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[bool, Any]:
        """Retrieve audit history and review decisions."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if node_id:
            params["node_id"] = node_id
        if edge_id:
            params["edge_id"] = edge_id
        if reviewer_id:
            params["reviewer_id"] = reviewer_id
        if action:
            params["action"] = action
        try:
            response = requests.get(f"{self.base_url}/api/graph/history", params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def get_graph_original_record(self, node_id: str) -> Tuple[bool, Any]:
        """Retrieve the original underlying Phase 1–8 database record for a graph node."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/nodes/{node_id}/original-record", timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def confirm_graph_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        rationale: str,
        reviewer_role: str = "LEAD_REVIEWER",
    ) -> Tuple[bool, Any]:
        """Confirm a relationship proposal (RBAC guarded)."""
        headers = {"X-Reviewer-Role": reviewer_role}
        payload = {"reviewer_id": reviewer_id, "rationale": rationale}
        try:
            response = requests.post(
                f"{self.base_url}/api/graph/proposals/{proposal_id}/confirm",
                json=payload,
                headers=headers,
                timeout=10,
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def reject_graph_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        rationale: str,
        reviewer_role: str = "LEAD_REVIEWER",
    ) -> Tuple[bool, Any]:
        """Reject a candidate relationship proposal (RBAC guarded)."""
        headers = {"X-Reviewer-Role": reviewer_role}
        payload = {"reviewer_id": reviewer_id, "rationale": rationale}
        try:
            response = requests.post(
                f"{self.base_url}/api/graph/proposals/{proposal_id}/reject",
                json=payload,
                headers=headers,
                timeout=10,
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def defer_graph_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        rationale: str,
        reviewer_role: str = "LEAD_REVIEWER",
    ) -> Tuple[bool, Any]:
        """Defer a relationship proposal for further inquiry (RBAC guarded)."""
        headers = {"X-Reviewer-Role": reviewer_role}
        payload = {"reviewer_id": reviewer_id, "rationale": rationale}
        try:
            response = requests.post(
                f"{self.base_url}/api/graph/proposals/{proposal_id}/defer",
                json=payload,
                headers=headers,
                timeout=10,
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    # =========================================================================
    # PHASE 9.9: CROSS-PHASE INVESTIGATION WORKFLOWS AND AUDITABILITY
    # =========================================================================

    def investigate_workflow_a(self, promise_id: str) -> Tuple[bool, Any]:
        """Workflow A: Promise -> Schemes -> Budgets -> Implementation."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/workflow-a/promise", params={"id": promise_id}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def investigate_workflow_b(self, issue_id: str) -> Tuple[bool, Any]:
        """Workflow B: Civic Issue -> Response -> Status -> Resolution."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/workflow-b/civic-issue", params={"id": issue_id}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def investigate_workflow_c(self, claim_id: str) -> Tuple[bool, Any]:
        """Workflow C: Public Claim -> Supporting, Contradicting & Contextual Records."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/workflow-c/claim", params={"id": claim_id}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def investigate_workflow_d(self, representative_id: str) -> Tuple[bool, Any]:
        """Workflow D: Representative -> Constituency -> Legislative & Public Works."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/workflow-d/representative", params={"id": representative_id}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def investigate_workflow_e(self, funding_id: str) -> Tuple[bool, Any]:
        """Workflow E: Political Finance -> Source Document -> Supported Entities."""
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/workflow-e/funding", params={"id": funding_id}, timeout=15)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}

    def export_investigation_report(self, workflow: str, identifier: str, format: str = "json") -> Tuple[bool, Any]:
        """Export source-linked auditable investigation report."""
        params = {"workflow": workflow, "id": identifier, "format": format}
        try:
            response = requests.get(f"{self.base_url}/api/graph/investigate/report/export", params=params, timeout=20)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return False, {"message": str(e)}


# Global instance for use across Streamlit pages
api_client = APIClient()

