import re

path = r'E:\CIVCLENS\backend\api\schemes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The first occurrence is the old one. The second occurrence is the new one.
# Let's split on "@schemes_bp.route('/<int:scheme_id>/similar'"
parts = content.split("@schemes_bp.route('/<int:scheme_id>/similar', methods=['GET'])")

if len(parts) == 3:
    # Parts[0] is the top of the file
    # Parts[1] is the old similar and semantic_search routes
    # Parts[2] is the new similar and semantic_search routes
    
    # We want to keep parts[0] + the new routes marker + parts[2]
    new_content = parts[0] + "@schemes_bp.route('/<int:scheme_id>/similar', methods=['GET'])" + parts[2]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed duplicates.")
else:
    print("Unexpected parts length:", len(parts))
