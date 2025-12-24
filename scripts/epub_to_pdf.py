from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from weasyprint import HTML

# -------------------------------------------------
# Paths
# -------------------------------------------------
EPUB_PATH = Path.home() / (
    "Library/Mobile Documents/iCloud~com~apple~iBooks/Documents/"
    "Hedge Fund Market Wizards.epub"
)

OUTPUT_PDF = Path.home() / "Desktop/Hedge_Fund_Market_Wizards_generated.pdf"

# -------------------------------------------------
# Step 1: Read EPUB
# -------------------------------------------------
book = epub.read_epub(str(EPUB_PATH))

html_sections = []

# -------------------------------------------------
# Step 2: Extract spine content
# -------------------------------------------------
for item in book.get_items_of_type(ITEM_DOCUMENT):
    soup = BeautifulSoup(item.get_content(), "html.parser")

    # Clean junk
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Ensure page breaks between chapters
    wrapper = f"""
    <div style="page-break-before: always;">
        {str(soup)}
    </div>
    """

    html_sections.append(wrapper)

# -------------------------------------------------
# Step 3: Wrap in full HTML document
# -------------------------------------------------
full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: Georgia, serif;
        font-size: 11pt;
        line-height: 1.5;
        margin: 2cm;
    }}
    h1, h2, h3 {{
        page-break-after: avoid;
    }}
</style>
</head>
<body>
{''.join(html_sections)}
</body>
</html>
"""

# -------------------------------------------------
# Step 4: Render to PDF
# -------------------------------------------------
HTML(string=full_html).write_pdf(str(OUTPUT_PDF))

print("PDF created at:")
print(OUTPUT_PDF)
