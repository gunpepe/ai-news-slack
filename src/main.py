import feedparser
import yaml
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT_DIR / "config" / "sources.yml"

def load_sources():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    print("=== AI News Bot: STEP 7 ===")

    sources = load_sources()
    print(f"Loaded {len(sources)} sources")

    total_entries = 0

    for source in sources:
        name = source["name"]
        url = source["url"]
        language = source["language"]

        print(f"\n--- Fetching: {name} ({language}) ---")
        feed = feedparser.parse(url)

        if not feed.entries:
            print("No entries found.")
            continue

        print(f"Found {len(feed.entries)} entries")
        total_entries += len(feed.entries)

        # 最新1件だけログ表示
        entry = feed.entries[0]
        print("Latest:")
        print("  Title:", entry.title)
        print("  Link :", entry.link)

    print("\n==============================")
    print(f"Total articles fetched: {total_entries}")

if __name__ == "__main__":
    main()
