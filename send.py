#!/usr/bin/env python3
"""
send.py — 喺 GitHub Actions 跑。掃 queue/ 入面所有夠鐘嘅 message，
經 CallMeBot send 去 WhatsApp，send 成功就 delete 個 queue 檔。

電話 / apikey 由 env 嚟（GitHub Secrets）：
  CALLMEBOT_PHONE   例 85291234567
  CALLMEBOT_APIKEY  CallMeBot 俾你嗰個 key
"""

import os
import sys
import json
import glob
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(REPO, "queue")
SENT_DIR = os.path.join(REPO, "sent")
API_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(text, phone, apikey):
    params = urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey})
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "mk-idea-lab"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
        return resp.status == 200, body.strip()[:200]


def main():
    phone = os.environ.get("CALLMEBOT_PHONE", "").strip()
    apikey = os.environ.get("CALLMEBOT_APIKEY", "").strip()
    if not phone or not apikey:
        print("::error::CALLMEBOT_PHONE / CALLMEBOT_APIKEY 未設定 (GitHub Secrets)")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    files = sorted(glob.glob(os.path.join(QUEUE_DIR, "*.json")))
    if not files:
        print("queue 冇嘢，收工。")
        return

    sent, kept, failed = 0, 0, 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                msg = json.load(f)
            send_at = datetime.fromisoformat(msg["send_at"])
            if send_at.tzinfo is None:  # 舊檔當 UTC
                send_at = send_at.replace(tzinfo=timezone.utc)
        except Exception as e:
            print(f"::warning::跳過壞檔 {os.path.basename(path)}: {e}")
            kept += 1
            continue

        if send_at > now:
            kept += 1
            continue

        try:
            ok, info = send_whatsapp(msg["text"], phone, apikey)
        except Exception as e:
            ok, info = False, str(e)

        if ok:
            # send 成功：由 queue/ 移去 sent/（加 sent_at），等 commit step 推返上去
            os.makedirs(SENT_DIR, exist_ok=True)
            msg["sent_at"] = now.replace(microsecond=0).isoformat()
            with open(os.path.join(SENT_DIR, os.path.basename(path)), "w", encoding="utf-8") as f:
                json.dump(msg, f, ensure_ascii=False, indent=2)
            os.remove(path)
            sent += 1
            print(f"✅ sent: {msg['text'][:60]}")
        else:
            failed += 1
            print(f"::warning::send 失敗，留低再試: {os.path.basename(path)} | {info}")

    print(f"總結 — 已 send {sent} / 留低 {kept} / 失敗 {failed}")


if __name__ == "__main__":
    main()
