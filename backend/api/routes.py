from flask import Blueprint
from backend.api.responses import error_response
from backend.api.budget import budget_bp
from backend.api.ml import ml_bp
from backend.api.schemes import schemes_bp
from backend.api.promises import promises_bp

# Central router combining all modular blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api')

def not_implemented():
    return error_response(message="Module not implemented yet.", status_code=501)

# Register real blueprints
api_bp.register_blueprint(budget_bp)
api_bp.register_blueprint(ml_bp)
api_bp.register_blueprint(schemes_bp)
api_bp.register_blueprint(promises_bp)

# Register placeholder namespaces for remaining future modules
namespaces = [
    'news', 
    'representatives', 'funding', 'claims'
]

# Provide fallback 501 for unbuilt components
for ns in namespaces:
    ns_bp = Blueprint(ns, __name__, url_prefix=f'/{ns}')
    
    @ns_bp.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
    @ns_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def handle_unimplemented(path):
        return not_implemented()
        
    api_bp.register_blueprint(ns_bp)
