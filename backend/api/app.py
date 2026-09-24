import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text
from backend.core.config import config
from backend.database.session import SessionLocal
from backend.api.routes import api_bp
from backend.api.errors import error_bp
from backend.api.responses import success_response, error_response

def create_app():
    """Application factory for configuring and starting the Flask backend."""
    app = Flask(config.APP_NAME)
    
    # Enable CORS for frontend integration
    CORS(app)
    
    # Register blueprints for routes and error handling
    app.register_blueprint(error_bp)
    app.register_blueprint(api_bp)

    @app.route('/health', methods=['GET'])
    def health_check():
        """General application health check."""
        return success_response(data={"status": "healthy"}, message="Application is running")

    @app.route('/health/db', methods=['GET'])
    def db_health_check():
        """Checks if the database is reachable."""
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return success_response(data={"db_status": "connected"}, message="Database is reachable")
        except Exception as e:
            return error_response(message="Database connection failed", error_details=str(e), status_code=503)
        finally:
            db.close()

    @app.route('/version', methods=['GET'])
    def get_version():
        """Returns the current API version."""
        return success_response(data={"version": "0.1.0"}, message="Version retrieved")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=config.API_HOST, port=config.API_PORT, debug=config.DEBUG)
