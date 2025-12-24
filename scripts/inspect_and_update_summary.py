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
#BOOK_TITLE = "Hedgehogging"

query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

query_payload = {
    "filter": {
        "property": "Title",
        "title": {
            "equals": BOOK_TITLE
        }
    }
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
# 2️⃣ Read current Summary value
# ─────────────────────────────────────────────

summary_property = page["properties"]["Summary"]["rich_text"]

current_summary = (
    "".join(rt["plain_text"] for rt in summary_property)
    if summary_property
    else "<EMPTY>"
)

print("\nCurrent Summary:")
print(current_summary)

# ─────────────────────────────────────────────
# 3️⃣ Update Summary with random text
# ─────────────────────────────────────────────

random_summary = random.choice([
    "Test summary injected via Python.",
    "This is a temporary summary for API testing.",
    "Automated Notion update successful.",
])

update_url = f"https://api.notion.com/v1/pages/{page_id}"

update_payload = {
    "properties": {
        "Summary": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": random_summary
                    }
                }
            ]
        }
    }
}

update_response = requests.patch(
    update_url,
    headers=HEADERS,
    json=update_payload
)
update_response.raise_for_status()

print("\nUpdated Summary to:")
print(random_summary)
