import feedparser
import yaml
from pathlib import Path

import os
import json
import urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def call_gemini(article_title, article_content):
    """
    Gemini APIを使って翻訳・要約・分類を行う
    """
    prompt = f"""
以下の記事をチーム向け日次レポート用に処理してください。

条件：
- 英語の場合は日本語に翻訳
- 日本語で3行以内に要約
- 次のカテゴリから1つ選択
  新AIツール / 既存ツールのアップデート /
  OSS / 開発者向け / ビジネス・業界動向 / 規制・社会影響

出力形式（JSON）：
{{
  "title": "",
  "summary": ["", "", ""],
  "category": ""
}}

記事タイトル：
{article_title}

記事本文：
{article_content}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return text
``

SOURCES_FILE = Path("config/sources.yml")

def load_sources():
    print("Looking for sources file at:", SOURCES_FILE.resolve())
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
        entry = feed.entries[0]print("\n--- Sending article to Gemini ---")
        content = entry.get("summary", "")

        ai_result = call_gemini(entry.title, content)
        print("\nAI Result:")
        print(ai_result)

        break  # ← STEP 8-1 なので1件だけ

        print("Latest:")
        print("  Title:", entry.title)
        print("  Link :", entry.link)

    print("\n==============================")
    print(f"Total articles fetched: {total_entries}")

if __name__ == "__main__":
    main()
