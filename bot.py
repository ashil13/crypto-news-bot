import json
import os
import time

import feedparser
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen.json"
MAX_SEEN = 5000

FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "The Block": "https://www.theblock.co/rss.xml",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "Blockworks": "https://blockworks.co/feed",
    "DL News": "https://www.dlnews.com/arc/outboundfeeds/rss/",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "The Defiant": "https://thedefiant.io/api/feed",
    "Ethereum Foundation": "https://blog.ethereum.org/feed.xml",
    "Solana": "https://solana.com/news/rss.xml",
}

UA = "Mozilla/5.0 (compatible; CryptoNewsBot/1.0)"


def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for _ in range(3):
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=30)
        if r.status_code == 200:
            return True
        if r.status_code == 429:
            wait = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(wait + 1)
            continue
        print("Telegram error:", r.status_code, r.text)
        return False
    return False


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f), False
    return [], True


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen[-MAX_SEEN:], f)


def main():
    seen, first_run = load_seen()
    seen_set = set(seen)
    new_items = []

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, agent=UA)
            if not feed.entries:
                print(f"[!] {source}: no entries (feed may be broken or blocked)")
                continue
            print(f"[ok] {source}: {len(feed.entries)} entries")
            for e in feed.entries:
                uid = e.get("id") or e.get("link")
                if not uid or uid in seen_set:
                    continue
                title = (e.get("title") or "").strip()
                link = e.get("link", "")
                new_items.append((source, title, link, uid))
        except Exception as ex:
            print(f"[!] {source}: error {ex}")

    if first_run:
        # First run: just remember current items so we don't flood the chat
        for _, _, _, uid in new_items:
            seen.append(uid)
        save_seen(seen)
        send("✅ ربات اخبار کریپتو فعال شد. از این به بعد خبرهای جدید می‌رسن.")
        print(f"First run: stored {len(new_items)} items")
        return

    # Oldest first is not guaranteed across feeds, so just send in order found
    for source, title, link, uid in reversed(new_items):
        ok = send(f"📰 {source}\n{title}\n{link}")
        if ok:
            seen.append(uid)
            seen_set.add(uid)
            time.sleep(1)
        else:
            print("Failed to send, will retry next run:", title)

    save_seen(seen)
    print(f"Sent {len(new_items)} new items")


if __name__ == "__main__":
    main()
