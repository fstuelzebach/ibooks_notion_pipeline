from pathlib import Path
import os
import json
import requests
from dotenv import load_dotenv

# Resolve project root (ibooks_notion_pipeline/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"  # or ".env" if you rename it later

loaded = load_dotenv(ENV_PATH)

if not loaded:
    raise RuntimeError(f"Failed to load env file at {ENV_PATH}")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY is missing or empty")

if not NOTION_DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID is missing or empty")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

response = requests.post(url, headers=HEADERS)
response.raise_for_status()

print("Successfully connected to Notion!")
print(json.dumps(response.json(), indent=2))
