import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import re
import json
from collections import defaultdict
import shutil
import sys

# -----------------------------
# Project root & data directories
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
LOG_DIR = DATA_DIR / "log"

# Ensure directories exist
for p in (RAW_DATA_DIR, CLEAN_DIR, LOG_DIR):
    p.mkdir(parents=True, exist_ok=True)

ERROR_LOG_FILE = LOG_DIR / f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# -----------------------------
# Original iBooks DB paths
# -----------------------------
if sys.platform == "win32":
    # Adjust if you have a Windows iBooks location
    ORIG_BOOK_DB_PATH = Path("C:/path/to/BKLibrary.sqlite")
    ORIG_ANNOT_DB_PATH = Path("C:/path/to/AEAnnotation.sqlite")
else:
    ORIG_BOOK_DB_PATH = Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary-1-091020131601.sqlite"
    ORIG_ANNOT_DB_PATH = Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1727_local.sqlite"

BOOK_DB_PATH = RAW_DATA_DIR / ORIG_BOOK_DB_PATH.name
ANNOT_DB_PATH = RAW_DATA_DIR / ORIG_ANNOT_DB_PATH.name

# -----------------------------
# Helper functions
# -----------------------------
def log_error(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"ERROR: {msg}")

def copy_if_newer(src: Path, dst: Path):
    """Copy file if it does not exist in dst or src is newer."""
    try:
        if not src.exists():
            log_error(f"Source file not found: {src}")
            return False
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
            print(f"Copied {src.name} -> {dst}")
        return True
    except Exception as e:
        log_error(f"Failed to copy {src} -> {dst}: {e}")
        return False

def cocoa_timestamp_to_datetime(cocoa_ts):
    if cocoa_ts is None:
        return None
    return datetime(2001, 1, 1) + timedelta(seconds=cocoa_ts)

def normalize_chapter(chapter_name):
    match = re.search(r'(\d+)', chapter_name)
    if match:
        return f"Chapter {int(match.group(1)):02d}"
    return chapter_name or "Unknown Chapter"

def assign_heading_level(chapter_name: str) -> int:
    if not chapter_name:
        return 1
    match = re.search(r'(\d+(\.\d+)*)', chapter_name)
    if not match:
        return 1
    level = match.group(1).count(".") + 1
    return min(level, 3)

def safe_filename(name: str) -> str:
    return re.sub(r'[^\w\-_ ]', "_", name)

# -----------------------------
# Step 0: Ensure raw DB is up-to-date
# -----------------------------
if not copy_if_newer(ORIG_BOOK_DB_PATH, BOOK_DB_PATH):
    log_error("Book DB not available. Exiting.")
    sys.exit(1)

if not copy_if_newer(ORIG_ANNOT_DB_PATH, ANNOT_DB_PATH):
    log_error("Annotation DB not available. Exiting.")
    sys.exit(1)

# -----------------------------
# Step 1: Load books
# -----------------------------
books = {}
try:
    conn = sqlite3.connect(BOOK_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT ZASSETID, ZTITLE, ZAUTHOR, ZPATH FROM ZBKLIBRARYASSET;")
    for asset_id, title, author, path in cursor.fetchall():
        books[asset_id] = {
            "title": title,
            "author": author,
            "path": path,
            "annotations": []
        }
    conn.close()
except Exception as e:
    log_error(f"Failed to load books: {e}")

# -----------------------------
# Step 2: Load annotations
# -----------------------------
try:
    conn = sqlite3.connect(ANNOT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            ZANNOTATIONASSETID,
            ZANNOTATIONSELECTEDTEXT,
            ZANNOTATIONNOTE,
            ZANNOTATIONTYPE,
            ZANNOTATIONCREATIONDATE,
            ZPLLOCATIONRANGESTART,
            ZPLLOCATIONRANGEEND,
            ZANNOTATIONLOCATION
        FROM ZAEANNOTATION
        WHERE ZANNOTATIONSELECTEDTEXT IS NOT NULL OR ZANNOTATIONNOTE IS NOT NULL;
    """)
    for row in cursor.fetchall():
        asset_id, highlight, note, annot_type, created, loc_start, loc_end, loc_text = row
        if asset_id in books:
            books[asset_id]["annotations"].append({
                "highlight": highlight,
                "note": note,
                "type": annot_type,
                "created": cocoa_timestamp_to_datetime(created),
                "loc_start": loc_start,
                "loc_end": loc_end,
                "loc_text": loc_text
            })
    conn.close()
except Exception as e:
    log_error(f"Failed to load annotations: {e}")

# -----------------------------
# Step 3: Process books & export JSONs
# -----------------------------
# Define which books to focus on:
FOCUS_BOOK_TITLES = [
    "Hedge Fund Market Wizards"
]
book_data = []
for asset_id, book in books.items():
    try:
        # Skip books not in the focus list
        if book["title"] not in FOCUS_BOOK_TITLES:
            continue

        if not book.get("annotations"):
            log_error(f"No annotations found for book: {book['title']}")
            continue

        chapter_map = defaultdict(list)
        for annot in book["annotations"]:
            chapter_name = "Unknown Chapter"
            loc_text = annot.get("loc_text")
            if loc_text and "[" in loc_text and "]" in loc_text:
                chapter_name = loc_text.split("[")[1].split("]")[0]
            chapter_name = normalize_chapter(chapter_name)
            annot["chapter"] = chapter_name

            chapter_map[chapter_name].append({
                "highlight": annot["highlight"],
                "note": annot.get("note"),
                "created": annot.get("created").isoformat() if annot.get("created") else None
            })

        book_json = {
            "title": book["title"],
            "author": book.get("author", ""),
            "annotations": []
        }

        for chapter_name, entries in sorted(chapter_map.items()):
            heading_level = assign_heading_level(chapter_name)
            book_json["annotations"].append({
                "chapter": chapter_name,
                "heading_level": heading_level,
                "entries": sorted(entries, key=lambda x: x["created"] or "")
            })

        # Write JSON
        filename = safe_filename(book["title"]) + ".json"
        file_path = CLEAN_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(book_json, f, ensure_ascii=False, indent=2)

        print(f"✅ JSON written: {file_path}")
        book_data.append(book_json)

    except Exception as e:
        log_error(f"Failed to process book '{book.get('title', asset_id)}': {e}")

print(f"\nProcessing complete. {len(book_data)} books exported.")
print(f"Error log (if any) at: {ERROR_LOG_FILE}")
