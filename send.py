#!/usr/bin/env python3
"""
send.py — GitHub Actions 每 5 分鐘行。掃 queue/ 夠鐘嘅 message，
經 CallMeBot send 去 WhatsApp。支援重複（每 N 日/週/月/年）。

電話 / apikey 由 env（GitHub Secrets）：CALLMEBOT_PHONE / CALLMEBOT_APIKEY
一檔一 message：queue/<id>.json
  { "id", "send_at"(UTC ISO,下次), "text", "created", "repeat": {"freq","interval"} | null }
  freq: daily | weekly | monthly | yearly ; interval: 1-9（每 N）
送完：
  - 一次性（repeat 冇）→ 移去 sent/<id>.json（加 sent_at）
  - 重複 → 留喺 queue，send_at 推去下一次
"""

import os
import sys
import json
import glob
import calendar
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

REPO = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(REPO, "queue")
SENT_DIR = os.path.join(REPO, "sent")
API_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(text, phone, apikey):
    params = urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey})
    req = urllib.request.Request(f"{API_URL}?{params}", headers={"User-Agent": "wa-presend"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status == 200, resp.read().decode("utf-8", "replace").strip()[:200]


def add_months(dt, n):
    m = dt.month - 1 + n
    y = dt.year + m // 12
    m = m % 12 + 1
    d = min(dt.day, calendar.monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=d)


def step(dt, freq, interval):
    if freq == "daily":
        return dt + timedelta(days=interval)
    if freq == "weekly":
        return dt + timedelta(weeks=interval)
    if freq == "monthly":
        return add_months(dt, interval)
    if freq == "yearly":
        return add_months(dt, 12 * interval)
    return None


def next_occurrence(dt, repeat, now):
    """由 dt 推去下一個 > now 嘅時間。"""
    freq = repeat.get("freq")
    interval = max(1, min(9, int(repeat.get("interval", 1))))
    nxt = step(dt, freq, interval)
    if nxt is None:
        return None
    guard = 0
    while nxt <= now and guard < 2000:
        nxt = step(nxt, freq, interval)
        guard += 1
    return nxt


def main():
    phone = os.environ.get("CALLMEBOT_PHONE", "").strip()
    apikey = os.environ.get("CALLMEBOT_APIKEY", "").strip()
    if not phone or not apikey:
        print("::error::CALLMEBOT_PHONE / CALLMEBOT_APIKEY 未設定（GitHub Secrets）")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    files = sorted(glob.glob(os.path.join(QUEUE_DIR, "*.json")))
    if not files:
        print("queue 冇嘢，收工。")
        return

    sent = repeated = kept = failed = 0
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                msg = json.load(f)
            send_at = datetime.fromisoformat(msg["send_at"])
            if send_at.tzinfo is None:
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

        if not ok:
            failed += 1
            print(f"::warning::send 失敗，留低再試: {os.path.basename(path)} | {info}")
            continue

        repeat = msg.get("repeat")
        if repeat and repeat.get("freq"):
            nxt = next_occurrence(send_at, repeat, now)
            if nxt:
                msg["send_at"] = nxt.replace(microsecond=0).isoformat()
                msg["last_sent_at"] = now.replace(microsecond=0).isoformat()
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(msg, f, ensure_ascii=False, indent=2)
                repeated += 1
                print(f"🔁 sent + 下次 {msg['send_at']}: {msg['text'][:50]}")
                continue

        # 一次性：移去 sent/
        os.makedirs(SENT_DIR, exist_ok=True)
        msg["sent_at"] = now.replace(microsecond=0).isoformat()
        with open(os.path.join(SENT_DIR, os.path.basename(path)), "w", encoding="utf-8") as f:
            json.dump(msg, f, ensure_ascii=False, indent=2)
        os.remove(path)
        sent += 1
        print(f"✅ sent: {msg['text'][:50]}")

    print(f"總結 — 一次性送 {sent} / 重複送 {repeated} / 留低 {kept} / 失敗 {failed}")


if __name__ == "__main__":
    main()
