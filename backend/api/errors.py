import traceback
from flask import Blueprint
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.api.responses import error_response
from backend.core.logger import setup_logger
from backend.core.config import config

error_bp = Blueprint('errors', __name__)
logger = setup_logger("civiclens.api")

@error_bp.app_errorhandler(Exception)
def handle_unexpected_error(error):
    """Fallback handler for unhandled exceptions."""
    logger.exception("Unexpected API failure")
    details = traceback.format_exc() if config.DEBUG else None
    return error_response(message="An unexpected server error occurred.", error_details=details, status_code=500)

@error_bp.app_errorhandler(SQLAlchemyError)
def handle_database_error(error):
    """Handle database failures safely."""
    logger.exception("Database failure")
    details = str(error) if config.DEBUG else None
    return error_response(message="A database error occurred.", error_details=details, status_code=503)

@error_bp.app_errorhandler(HTTPException)
def handle_http_error(error):
    """Handle standard Werkzeug HTTP exceptions like 404 or 405."""
    logger.warning(f"HTTP Error {error.code}: {error.name}")
    return error_response(message=error.name, error_details=error.description, status_code=error.code)

@error_bp.app_errorhandler(NotImplementedError)
def handle_not_implemented(error):
    """Handle features that are explicitly stubbed out."""
    logger.info("Not implemented endpoint accessed")
    return error_response(message="This endpoint or feature is not implemented yet.", status_code=501)
