import re

path = r'E:\CIVCLENS\backend\api\schemes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the old similar and semantic_search routes if they exist
match = re.search(r'@schemes_bp.route\(''/<int:scheme_id>/similar''', content)
if match:
    content = content[:match.start()]
    
content += '''
@schemes_bp.route('/<int:scheme_id>/similar', methods=['GET'])
def get_similar_schemes(scheme_id: int):
    try:
        db: Session = next(get_db())
    except Exception as e:
        return error_response(f"Database error: {str(e)}", status_code=500)
        
    top_k = request.args.get('top_k', 5, type=int)
    threshold = request.args.get('threshold', 0.3, type=float)
    page = request.args.get('page', 1, type=int)
    department_id = request.args.get('department_id', type=int)
    year = request.args.get('year', type=str)
    category_id = request.args.get('category_id', type=int)
    
    if page < 1: return error_response("Page must be >= 1", status_code=400)
    if top_k < 1 or top_k > 100: return error_response("top_k must be between 1 and 100", status_code=400)
    
    try:
        from backend.nlp.similarity import SemanticSchemeSearcher
        searcher = SemanticSchemeSearcher(db)
        results = searcher.search_by_scheme_id(
            scheme_id, top_k=top_k, threshold=threshold, page=page,
            department_id=department_id, year=year, category_id=category_id
        )
        return success_response(results)
    except ValueError as ve:
        return error_response(str(ve), status_code=404)
    except Exception as e:
        return error_response(f"Similarity search failed: {str(e)}", status_code=500)

@schemes_bp.route('/semantic_search', methods=['GET'])
def semantic_text_search():
    try:
        db: Session = next(get_db())
    except Exception as e:
        return error_response(f"Database error: {str(e)}", status_code=500)
        
    query = request.args.get('query', type=str)
    if not query:
        return error_response("Query parameter is required.", status_code=400)
        
    top_k = request.args.get('top_k', 5, type=int)
    threshold = request.args.get('threshold', 0.3, type=float)
    page = request.args.get('page', 1, type=int)
    department_id = request.args.get('department_id', type=int)
    year = request.args.get('year', type=str)
    category_id = request.args.get('category_id', type=int)
    
    if page < 1: return error_response("Page must be >= 1", status_code=400)
    if top_k < 1 or top_k > 100: return error_response("top_k must be between 1 and 100", status_code=400)
    
    try:
        from backend.nlp.similarity import SemanticSchemeSearcher
        searcher = SemanticSchemeSearcher(db)
        results = searcher.search_by_text(
            query, top_k=top_k, threshold=threshold, page=page,
            department_id=department_id, year=year, category_id=category_id
        )
        return success_response(results)
    except Exception as e:
        return error_response(f"Semantic search failed: {str(e)}", status_code=500)
'''

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
