"""Trademaster journal: every call (TRADE or NO TRADE) is logged so its edge can be measured.

  python journal.py log   --symbol XAUUSD --decision LONG --model 2022 --grade A+ --entry .. --stop .. --tp1 .. --tp2 .. --lots .. --reason "..."
  python journal.py log   --symbol EURUSD --decision NO_TRADE --reason "H4/D1 bias conflict"
  python journal.py close --id 7 --result-r 1.4 --note "TP1 hit, runner stopped at BE"
  python journal.py stats
File: $TRADEMASTER_HOME/journal.csv (default ~/.trademaster/journal.csv). Append-only except `close`.
"""
import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("TRADEMASTER_HOME", Path.home() / ".trademaster"))
FILE = HOME / "journal.csv"
COLS = ["id", "time_utc", "symbol", "decision", "model", "grade", "killzone", "entry", "stop", "tp1", "tp2",
        "lots", "risk_amount", "reason", "result_r", "outcome_note"]


def rows():
    if not FILE.exists():
        return []
    with FILE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_all(rs):
    with FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rs)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log")
    for c in COLS[2:14]:
        lg.add_argument(f"--{c.replace('_', '-')}", dest=c, default="")
    cl = sub.add_parser("close")
    cl.add_argument("--id", required=True)
    cl.add_argument("--result-r", required=True, type=float)
    cl.add_argument("--note", default="")
    sub.add_parser("stats")
    a = ap.parse_args()

    HOME.mkdir(parents=True, exist_ok=True)
    rs = rows()
    if a.cmd == "log":
        r = {c: getattr(a, c, "") for c in COLS}
        r["id"] = str(max((int(x["id"]) for x in rs), default=0) + 1)
        r["time_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        new = not FILE.exists()
        with FILE.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, COLS)
            if new:
                w.writeheader()
            w.writerow(r)
        print(f"logged #{r['id']}")
    elif a.cmd == "close":
        hit = [r for r in rs if r["id"] == a.id]
        if not hit:
            raise SystemExit(f"no entry #{a.id}")
        hit[0]["result_r"], hit[0]["outcome_note"] = str(a.result_r), a.note
        write_all(rs)
        print(f"closed #{a.id} at {a.result_r}R")
    else:
        trades = [r for r in rs if r["decision"] in ("LONG", "SHORT")]
        done = [float(r["result_r"]) for r in trades if r["result_r"]]
        print(f"calls: {len(rs)}  no-trade: {len(rs) - len(trades)}  trades: {len(trades)}  closed: {len(done)}")
        if done:
            wins = [x for x in done if x > 0]
            print(f"win rate: {len(wins) / len(done):.0%}  expectancy: {sum(done) / len(done):+.2f}R  total: {sum(done):+.2f}R")
            for key in ("model", "grade", "killzone", "symbol"):
                groups = {}
                for r in trades:
                    if r["result_r"]:
                        groups.setdefault(r[key] or "?", []).append(float(r["result_r"]))
                print(f"by {key}: " + ", ".join(f"{k} {sum(v) / len(v):+.2f}R (n={len(v)})" for k, v in groups.items()))
            if len(done) < 30:
                print(f"note: {len(done)} closed trades is too few to judge the edge (want 30+, ideally 100)")


if __name__ == "__main__":
    main()
