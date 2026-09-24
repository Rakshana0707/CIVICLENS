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

# Global instance for use across Streamlit pages
api_client = APIClient()
