import os
import re

for file_name in os.listdir('frontend/pages'):
    if file_name.endswith('.py'):
        path = os.path.join('frontend/pages', file_name)
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if 'st.set_page_config' in line:
                # Replace the whole line with a safe version
                title = line.split('page_title="')[1].split('"')[0] if 'page_title="' in line else 'CivicLens TN'
                lines[i] = f'st.set_page_config(page_title="{title}", layout="wide")\n'
            if 'st.title' in line:
                # Clean up title line
                lines[i] = re.sub(r'dY\"[a-zA-Z%]+\"?\s*', '', lines[i])
                lines[i] = lines[i].replace('?? ', '')
                
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
