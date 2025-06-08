import requests
from bs4 import BeautifulSoup

doc_url = "https://docs.google.com/document/d/e/2PACX-1vQPgH-0mkjK0T9Yq3IkiGqGq-KOwJEoGLpuifOaqLpk-R0H0heVxIE9kJUzQaS_0HVOqEzg4nAlfQnY/pub"
response = requests.get(doc_url)
soup = BeautifulSoup(response.content, 'html.parser')

paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

# Show first 30 lines
print("📄 First 30 non-empty lines from the document:\n")
for i, para in enumerate(paragraphs[:30]):
    print(f"{i+1:02d}: {para}")
