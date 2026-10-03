import requests
import logging
from typing import Dict, Any, Tuple
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

# Global instance for use across Streamlit pages
api_client = APIClient()

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
