import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm  # progress bars

# -----------------------------
# Paths & environment
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
LOG_DIR = ROOT / "data" / "log"
LOG_DIR.mkdir(exist_ok=True)

# Load environment variables
load_dotenv(ROOT / ".env")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("Missing NOTION_API_KEY or NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# -----------------------------
# Helper: chunk list into batches
# -----------------------------
def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

# -----------------------------
# Books to process
# -----------------------------
BOOK_TITLES = [
    "Hedge Fund Market Wizards",
    # Add more book titles here
]

# -----------------------------
# Process each book
# -----------------------------
for book_idx, title in enumerate(BOOK_TITLES, start=1):
    try:
        json_file = CLEAN_DIR / f"{title}.json"
        if not json_file.exists():
            print(f"⚠️ JSON not found for book: {title}")
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            book_data = json.load(f)

        # -----------------------------
        # Find Notion page by title
        # -----------------------------
        query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        query_payload = {"filter": {"property": "Title", "title": {"equals": title}}}
        response = requests.post(query_url, headers=HEADERS, json=query_payload)
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            print(f"⚠️ No Notion page found for: {title}")
            continue

        page = results[0]
        page_id = page["id"]
        print(f"\nFound Notion page: {page_id}")

        # -----------------------------
        # Fetch existing children
        # -----------------------------
        children_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        existing_blocks = requests.get(children_url, headers=HEADERS).json().get("results", [])

        # Preserve the first block (cover), delete all others
        top_block_id = existing_blocks[0]["id"] if existing_blocks else None
        for block in existing_blocks[1:] if top_block_id else existing_blocks:
            del_resp = requests.delete(f"https://api.notion.com/v1/blocks/{block['id']}", headers=HEADERS)
            if not del_resp.ok:
                print(f"⚠️ Failed to delete block {block['id']}: {del_resp.text}")

        # -----------------------------
        # Build new blocks
        # -----------------------------
        blocks = []

        # 1️⃣ Insert Literaturverzeichnis at top (after cover)
        blocks.append({
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {}
        })

        # 2️⃣ Append chapters and annotations
        for chapter in book_data.get("annotations", []):
            heading_type = {1: "heading_1", 2: "heading_2", 3: "heading_3"}.get(
                chapter.get("heading_level", 1), "heading_2"
            )

            # Chapter heading
            blocks.append({
                "object": "block",
                "type": heading_type,
                heading_type: {
                    "rich_text": [{"type": "text", "text": {"content": chapter.get("chapter", "Unknown Chapter")}}]
                }
            })

            # Annotations
            for entry in chapter.get("entries", []):
                content = entry.get("highlight", "")
                note = entry.get("note")
                if note:
                    content += f"\nNote: {note}"
                if content.strip():
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content}}]
                        }
                    })

        # -----------------------------
        # Append blocks in batches (after cover)
        # -----------------------------
        print(f"Processing book {book_idx}/{len(BOOK_TITLES)}: {title}")
        for batch in tqdm(list(chunked(blocks, 50)), desc=f"{title} blocks", unit="batch"):
            append_resp = requests.patch(children_url, headers=HEADERS, json={"children": batch})
            append_resp.raise_for_status()

        print(f"✅ Completed {title} ({book_idx}/{len(BOOK_TITLES)})")

    except Exception as e:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"❌ Error processing '{title}' at {timestamp}: {e}")
        with open(LOG_DIR / f"error_log_{timestamp}.txt", "w") as log_file:
            log_file.write(str(e))
