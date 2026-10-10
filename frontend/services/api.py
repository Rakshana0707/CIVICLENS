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


# Global instance for use across Streamlit pages
api_client = APIClient()
