from pathlib import Path
import os
import json
import random
import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Environment setup
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

if not load_dotenv(ENV_PATH):
    raise RuntimeError(f"Failed to load env file at {ENV_PATH}")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("Missing NOTION_API_KEY or NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ─────────────────────────────────────────────
# 1️⃣ Query page by Title
# ─────────────────────────────────────────────
BOOK_TITLE = "Hedge Fund Market Wizards"

query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
query_payload = {
    "filter": {"property": "Title", "title": {"equals": BOOK_TITLE}}
}

response = requests.post(query_url, headers=HEADERS, json=query_payload)
response.raise_for_status()
results = response.json()["results"]

if not results:
    raise RuntimeError(f"No page found with Title == '{BOOK_TITLE}'")

page = results[0]
page_id = page["id"]
print(f"Found page: {page_id}")

# ─────────────────────────────────────────────
# 2️⃣ Fetch all page blocks (to detect cover/image block)
# ─────────────────────────────────────────────
blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
blocks_response = requests.get(blocks_url, headers=HEADERS)
blocks_response.raise_for_status()
blocks = blocks_response.json()["results"]

print("\nExisting page blocks:")
print("─" * 40)
for block in blocks:
    block_type = block["type"]
    block_data = block.get(block_type, {})
    print(f"[{block_type}] (id={block['id']})")

# ─────────────────────────────────────────────
# 3️⃣ Append Table of Contents (Inhaltsverzeichnis) after first image block
# ─────────────────────────────────────────────
# Determine insert position
insert_position = 0
for i, block in enumerate(blocks):
    if block["type"] in ("image", "file", "external"):
        insert_position = i + 1
        break

toc_block = {
    "object": "block",
    "type": "table_of_contents",
    "table_of_contents": {}
}

# Append headings + paragraph below TOC
content_blocks = [
    {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": "H1 Random Heading"}}]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "H2 Subheading"}}]
        }
    },
    {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "H3 Smaller Heading"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": "This paragraph was added via Python API."}}
            ]
        }
    },
]

# Combine TOC + content
children_to_append = [toc_block] + content_blocks

# Append to the page
append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
patch_response = requests.patch(append_url, headers=HEADERS, json={"children": children_to_append})
patch_response.raise_for_status()

print("\nTable of Contents + headings appended successfully!")
