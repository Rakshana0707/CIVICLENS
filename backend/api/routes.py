from flask import Blueprint
from backend.api.responses import error_response

# Central router combining all modular blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api')

def not_implemented():
    return error_response(message="Module not implemented yet.", status_code=501)

# Register placeholder namespaces for future module routing
namespaces = [
    'budget', 'schemes', 'promises', 'news', 
    'representatives', 'funding', 'claims', 'evidence'
]

for ns in namespaces:
    bp = Blueprint(ns, __name__, url_prefix=f'/{ns}')
    # Bind a dummy route to reserve the namespace
    bp.route('/', methods=['GET'])(not_implemented)
    api_bp.register_blueprint(bp)
