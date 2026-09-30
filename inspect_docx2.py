import docx
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc = docx.Document(r'E:\CIVCLENS\CivicLens_TN_Project_Abstract.docx')

print('--- PARAGRAPHS ---')
for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if text:
        print(f'{i}: {text}')
