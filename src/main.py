import os
import json
import feedparser
import yaml
import urllib.request
from pathlib import Path

# ===== 設定 =====
SOURCES_FILE = Path("config/sources.yml")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ===== Gemini 呼び出し =====
def call_gemini(article_title, article_content):
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
        "contents": [{"parts": [{"text": prompt}]}]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))

    return data["candidates"][0]["content"]["parts"][0]["text"]

# ===== main =====
def main():
    print("=== AI News Bot: STEP 8-1 ===")

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = yaml.safe_load(f)

    source = sources[0]
    feed = feedparser.parse(source["url"])
    entry = feed.entries[0]

    print("--- Sending article to Gemini ---")
    result = call_gemini(entry.title, entry.get("summary", ""))

    print("\nAI Result:")
    print(result)

if __name__ == "__main__":
    main()
