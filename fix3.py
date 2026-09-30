import os
import re

for file_name in os.listdir('frontend/pages'):
    if file_name.endswith('.py'):
        path = os.path.join('frontend/pages', file_name)
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Replace broken double quotes
        content = content.replace('st.info(\"\" ', 'st.info(\"')
        content = content.replace('st.warning(\"\" ', 'st.warning(\"')
        content = content.replace('st.error(\"\" ', 'st.error(\"')
        content = content.replace('st.success(\"\" ', 'st.success(\"')
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
