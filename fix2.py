import os
import re

for file_name in os.listdir('frontend/pages'):
    if file_name.endswith('.py'):
        path = os.path.join('frontend/pages', file_name)
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Replace broken emoji string literals safely
        content = content.replace('\"dY\"  Previous\"', '\"< Previous\"')
        content = content.replace('\"Next dY\" \"', '\"Next >\"')
        content = content.replace('\"dY\" ', '\"')
        content = content.replace('dY\"', '')
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
