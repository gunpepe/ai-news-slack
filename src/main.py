"""AI News Bot - RSS収集 / Gemini要約 / Slack投稿 (STEP 8-10)"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import requests
import yaml

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

SOURCES_FILE = Path("config/sources.yml")
CATEGORIES_FILE = Path("config/categories.yml")
MAX_ARTICLES = 10
MAX_CONTENT_CHARS = 2000

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "")


# ---------------------------------------------------------------------------
# 設定ファイル読み込み
# ---------------------------------------------------------------------------

def load_config():
    with open(SOURCES_FILE, encoding="utf-8") as f:
        sources = yaml.safe_load(f)
    with open(CATEGORIES_FILE, encoding="utf-8") as f:
        categories = yaml.safe_load(f)
    return sources, categories


# ---------------------------------------------------------------------------
# RSS 取得
# ---------------------------------------------------------------------------

def fetch_articles(sources):
    articles = []
    for source in sources:
        if len(articles) >= MAX_ARTICLES:
            break
        print(f"[FETCH] {source['name']}")
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries:
                if len(articles) >= MAX_ARTICLES:
                    break
                articles.append({
                    "source": source["name"],
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "url": entry.get("link", ""),
                })
        except Exception as e:
            print(f"[WARN] {source['name']} の取得に失敗: {e}")
    return articles


# ---------------------------------------------------------------------------
# Gemini API 呼び出し
# ---------------------------------------------------------------------------

def call_gemini(title, content, categories):
    categories_str = " / ".join(categories)
    prompt = (
        "以下の記事をチーム向け日次レポート用に処理してください。\n\n"
        "条件：\n"
        "- 英語の場合は日本語に翻訳すること\n"
        "- 日本語で3行以内に要約し、各行を配列の要素として出力\n"
        "- タイトルも日本語に翻訳すること\n"
        "- カテゴリは次の中から1つだけ選択: " + categories_str + "\n\n"
        "出力形式（JSONのみ。マークダウンやコードブロック記号は不要）:\n"
        '{"title": "日本語タイトル", "summary": ["1行目", "2行目", "3行目"], "category": "カテゴリ名"}\n\n'
        "記事タイトル:\n" + title + "\n\n"
        "記事本文:\n" + content[:MAX_CONTENT_CHARS]
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
    )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 512,
        },
    }

    resp = requests.post(url, json=payload, timeout=30)
    if not resp.ok:
        print("[GEMINI ERROR] status=" + str(resp.status_code) + " body=" + resp.text[:500])
    resp.raise_for_status()
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]

    # コードフェンスを除去してJSONを抽出
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("Gemini レスポンスにJSONが見つかりません: " + raw[:200])
    return json.loads(match.group())


# ---------------------------------------------------------------------------
# Slack 投稿
# ---------------------------------------------------------------------------

def slack_post(text, thread_ts=None):
    payload = {"channel": SLACK_CHANNEL_ID, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + SLACK_BOT_TOKEN},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError("Slack API エラー: " + result.get("error", "unknown"))
    return result["ts"]


def post_report(processed):
    jst = ZoneInfo("Asia/Tokyo")
    today = datetime.now(jst).strftime("%Y年%m月%d日")

    # 親メッセージ
    parent_text = (
        ":robot_face: *AIニュース日次レポート — " + today + "*\n"
        "本日のAI関連ニュース *" + str(len(processed)) + "件* をお届けします。"
    )
    parent_ts = slack_post(parent_text)
    print("[SLACK] 親メッセージ投稿 (ts=" + parent_ts + ")")

    # カテゴリ別にグループ化
    by_category = defaultdict(list)
    for item in processed:
        by_category[item.get("category", "その他")].append(item)

    # カテゴリごとにスレッド返信
    for category, items in by_category.items():
        lines = [":newspaper: *" + category + "*"]
        for item in items:
            bullet_lines = "\n".join("　• " + s for s in item.get("summary", []))
            lines.append(
                "\n*" + item["title"] + "*\n"
                + bullet_lines + "\n"
                + "<" + item["url"] + "|元記事>"
            )
        slack_post("\n".join(lines), thread_ts=parent_ts)
        print("[SLACK] カテゴリ投稿: " + category + " (" + str(len(items)) + "件)")


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def main():
    print("=== AI News Bot: STEP 8-10 ===")

    # シークレット確認
    missing = [
        name for name, val in [
            ("GEMINI_API_KEY", GEMINI_API_KEY),
            ("SLACK_BOT_TOKEN", SLACK_BOT_TOKEN),
            ("SLACK_CHANNEL_ID", SLACK_CHANNEL_ID),
        ]
        if not val
    ]
    if missing:
        print("[ERROR] 以下の環境変数が未設定です: " + ", ".join(missing))
        sys.exit(1)

    sources, categories = load_config()

    # RSS 取得
    articles = fetch_articles(sources)
    print("[INFO] 取得記事数: " + str(len(articles)))

    if not articles:
        print("[WARN] 記事が取得できませんでした。終了します。")
        sys.exit(0)

    # Gemini で処理
    processed = []
    for article in articles:
        print("[GEMINI] 処理中: " + article["title"][:60])
        try:
            result = call_gemini(article["title"], article["content"], categories)
            result["url"] = article["url"]
            processed.append(result)
        except Exception as e:
            print("[SKIP] " + str(e))
        time.sleep(13)  # 無料枠レート制限対策 (5 RPM = 最低12秒間隔)

    print("[INFO] 処理済み記事数: " + str(len(processed)))

    if not processed:
        print("[WARN] 処理できた記事がありません。終了します。")
        sys.exit(0)

    # Slack 投稿
    post_report(processed)
    print("[DONE] 完了!")


if __name__ == "__main__":
    main()
