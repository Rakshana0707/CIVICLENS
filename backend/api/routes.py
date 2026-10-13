from flask import Blueprint
from backend.api.responses import error_response
from backend.api.budget import budget_bp
from backend.api.ml import ml_bp
from backend.api.schemes import schemes_bp
from backend.api.promises import promises_bp
from backend.api.news import news_bp
from backend.api.funding import funding_bp
from backend.api.representatives import representatives_bp
from backend.api.claims import claims_bp
from backend.api.civic import civic_bp
from backend.api.entities import entities_bp
from backend.api.graph import graph_bp
from backend.api.policy_evaluation import policy_evaluation_bp

# Central router combining all modular blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api')

def not_implemented():
    return error_response(message="Module not implemented yet.", status_code=501)

# Register real blueprints
api_bp.register_blueprint(budget_bp)
api_bp.register_blueprint(ml_bp)
api_bp.register_blueprint(schemes_bp)
api_bp.register_blueprint(promises_bp)
api_bp.register_blueprint(news_bp)
api_bp.register_blueprint(funding_bp)
api_bp.register_blueprint(representatives_bp)
api_bp.register_blueprint(claims_bp)
api_bp.register_blueprint(civic_bp)
api_bp.register_blueprint(entities_bp)
api_bp.register_blueprint(graph_bp)
api_bp.register_blueprint(policy_evaluation_bp)


# Register placeholder namespaces for remaining future modules
namespaces = []


# Provide fallback 501 for unbuilt components
for ns in namespaces:
    ns_bp = Blueprint(ns, __name__, url_prefix=f'/{ns}')
    
    @ns_bp.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
    @ns_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def handle_unimplemented(path):
        return not_implemented()
        
    api_bp.register_blueprint(ns_bp)
