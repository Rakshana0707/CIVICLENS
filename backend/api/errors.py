from flask import Blueprint
from backend.api.responses import error_response
from werkzeug.exceptions import HTTPException

error_bp = Blueprint('errors', __name__)

@error_bp.app_errorhandler(Exception)
def handle_unexpected_error(error):
    """Fallback handler for any unhandled exceptions."""
    # In a real environment, you'd log the traceback here.
    return error_response(message="An unexpected server error occurred.", status_code=500)

@error_bp.app_errorhandler(HTTPException)
def handle_http_error(error):
    """Handle standard Werkzeug HTTP exceptions like 404 or 405."""
    return error_response(message=error.name, error_details=error.description, status_code=error.code)

@error_bp.app_errorhandler(NotImplementedError)
def handle_not_implemented(error):
    """Handle features that are explicitly stubbed out."""
    return error_response(message="This endpoint or feature is not implemented yet.", status_code=501)
