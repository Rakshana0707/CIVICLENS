path = r'E:\CIVCLENS\frontend\services\api.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "api_client = APIClient()":
        continue
    if line.strip() == "# Global instance for use across Streamlit pages":
        continue
    new_lines.append(line)

new_lines.append('\n# Global instance for use across Streamlit pages\n')
new_lines.append('api_client = APIClient()\n')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
