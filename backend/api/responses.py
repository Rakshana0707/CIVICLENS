from flask import jsonify
from typing import Any, Dict, Tuple

def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> Tuple[Any, int]:
    """
    Standardize all successful API responses.
    """
    response = {"status": "success", "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def error_response(message: str, error_details: Any = None, status_code: int = 400) -> Tuple[Any, int]:
    """
    Standardize all error API responses.
    """
    response = {"status": "error", "message": message}
    if error_details:
        response["details"] = error_details
    return jsonify(response), status_code
