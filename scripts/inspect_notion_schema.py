from pathlib import Path
import os
import json
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

if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY is missing or empty")

if not NOTION_DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID is missing or empty")


HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# ─────────────────────────────────────────────
# Fetch database schema
# ─────────────────────────────────────────────

url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"

response = requests.get(url, headers=HEADERS)
response.raise_for_status()

database = response.json()
properties = database.get("properties", {})


# ─────────────────────────────────────────────
# Pretty-print schema
# ─────────────────────────────────────────────

print("\n📘 Notion Database Schema\n" + "─" * 40)

for name, prop in properties.items():
    prop_type = prop["type"]

    print(f"\n• {name}")
    print(f"  Type: {prop_type}")

    # Type-specific details
    details = prop.get(prop_type)

    if isinstance(details, dict) and details:
        print("  Details:")
        for key, value in details.items():
            if key == "options":  # select / multi-select
                option_names = [opt["name"] for opt in value]
                print(f"    {key}: {option_names}")
            else:
                print(f"    {key}: {value}")


# ─────────────────────────────────────────────
# Optional: raw JSON dump (comment out if noisy)
# ─────────────────────────────────────────────

# print("\nRaw database JSON:")
# print(json.dumps(database, indent=2))
