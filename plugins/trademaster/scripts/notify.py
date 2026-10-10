"""Push a trade alert to the trader's phone via ntfy.sh (free; subscribe to the topic in the ntfy app).

  python notify.py "XAUUSD SHORT A+ 4151.2 SL 4156.0 TP 4123.3/4110.8 0.08 lots" --title "TRADE" --priority high
Topic: "ntfy_topic" in $TRADEMASTER_HOME/account.json. Prints "sent" / "skipped: ..." and never fails loudly,
so a notification problem can't break the desk loop.
"""
import argparse
import json
import os
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("TRADEMASTER_HOME", Path.home() / ".trademaster"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message")
    ap.add_argument("--title", default="Trademaster")
    ap.add_argument("--priority", default="default", choices=["min", "low", "default", "high", "urgent"])
    a = ap.parse_args()
    cfg_path = HOME / "account.json"
    topic = json.loads(cfg_path.read_text(encoding="utf-8")).get("ntfy_topic") if cfg_path.exists() else None
    if not topic:
        print("skipped: no ntfy_topic in account.json")
        return
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=a.message.encode("utf-8"), method="POST",
                                 headers={"Title": a.title, "Priority": a.priority, "Tags": "chart_with_upwards_trend"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        print("sent")
    except Exception as e:  # noqa: BLE001
        print(f"skipped: {e}")


if __name__ == "__main__":
    main()
