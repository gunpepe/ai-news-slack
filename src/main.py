import feedparser

def main():
    print("=== AI News Bot: STEP 6 test ===")

    # テスト用：1つのRSSだけ読む
    rss_url = "https://techcrunch.com/tag/ai/feed/"
    feed = feedparser.parse(rss_url)

    print(f"Feed title: {feed.feed.get('title')}")

    if not feed.entries:
        print("No entries found.")
        return

    # 最新1件だけ表示
    entry = feed.entries[0]
    print("---- Latest Entry ----")
    print("Title:", entry.title)
    print("Link:", entry.link)

if __name__ == "__main__":
    main()
