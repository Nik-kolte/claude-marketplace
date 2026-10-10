"""Deterministic risk gate + position sizer for trademaster. Pure stdlib.

Usage:
  python risk_calc.py FEED.json --entry 2650.5 --stop 2644.0 --tp1 2657 --tp2 2668 --grade A+
FEED.json is mt5_feed.py output, or a hand-written file with the same keys:
  {"account": {"equity", "balance", "day_start_balance", "trades_opened_today", "losses_today",
               "wins_in_row", "losses_in_row", "open_positions": []},
   "spec": {"tick_size", "tick_value", "volume_min", "volume_step", "volume_max", "spread_price"}}
Account rules come from $TRADEMASTER_HOME/account.json (default ~/.trademaster/account.json).
The verdict is final: if "allowed" is false, there is no trade.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

HOME = Path(os.environ.get("TRADEMASTER_HOME", Path.home() / ".trademaster"))

DEFAULTS = {
    "account_type": "prop_challenge",
    "initial_balance": None,          # required
    "daily_loss_limit": 0.05,         # fraction of daily_basis
    "daily_basis": "day_start_balance",   # or "initial_balance"
    "max_loss_limit": 0.10,
    "max_type": "static",             # or "trailing"
    "high_water_equity": None,        # needed when max_type == trailing
    "profit_target": None,            # fraction, e.g. 0.08
    "base_risk": 0.01,
    "max_risk": 0.015,
    "reduced_risk": 0.005,
    "max_trades_per_day": 2,
    "max_losses_per_day": 2,
    "min_rr_final": 2.0,
    "daily_room_share": 0.40,         # one trade may use at most 40% of remaining daily room
    "max_room_share": 0.25,           # ...and 25% of remaining max-drawdown room
    "daily_room_floor": 0.015,        # stop opening trades when < 1.5% of equity is left to the daily limit
    "killzones_enabled": ["Asia", "London", "NY AM", "NY PM"],  # desk mode only trades/watches these
    "local_utc_offset_min": 0,        # trader's local clock for notifications, e.g. 330 = IST
    "ntfy_topic": None,               # phone alerts via ntfy.sh
}


def load_rules():
    p = HOME / "account.json"
    if not p.exists():
        return None
    return {**DEFAULTS, **json.loads(p.read_text(encoding="utf-8"))}


def risk_tier(grade, wins_row, losses_row, r):
    if grade not in ("A+", "A"):
        return None, f"grade {grade}: only A and A+ setups are traded"
    if losses_row >= 2:
        return r["reduced_risk"], f"{losses_row} losses in a row -> reduced risk"
    if grade == "A+" and wins_row >= 2:
        return r["max_risk"], f"A+ setup after {wins_row} wins in a row -> max risk"
    if grade == "A+" and wins_row == 1:
        return (r["base_risk"] + r["max_risk"]) / 2, "A+ setup after a win -> raised risk"
    return r["base_risk"], "base risk"


def evaluate(feed, entry, stop, tp1, tp2, grade, r):
    acc, spec = feed["account"], feed["spec"]
    eq, bal = float(acc["equity"]), float(acc["balance"])
    init = float(r["initial_balance"])
    blocks, notes = [], []

    # --- prop limits ---
    basis = init if r["daily_basis"] == "initial_balance" else float(acc["day_start_balance"])
    daily_floor = float(acc["day_start_balance"]) - r["daily_loss_limit"] * basis
    if r["max_type"] == "trailing":
        hw = max(float(r["high_water_equity"] or init), eq)
        max_floor = hw * (1 - r["max_loss_limit"])
    else:
        max_floor = init * (1 - r["max_loss_limit"])
    daily_room, max_room = eq - daily_floor, eq - max_floor
    prop = {"daily_floor": round(daily_floor, 2), "daily_room": round(daily_room, 2),
            "max_floor": round(max_floor, 2), "max_room": round(max_room, 2),
            "pnl_vs_initial_pct": round((eq - init) / init * 100, 2)}
    if r["profit_target"] and eq >= init * (1 + r["profit_target"]):
        blocks.append("profit target reached: challenge passed, stop trading and request review")
    if daily_room <= r["daily_room_floor"] * eq:
        blocks.append(f"only {daily_room:.2f} left before the daily loss limit: done for today")
    if max_room <= 0 or daily_room <= 0:
        blocks.append("drawdown limit breached or at the limit")

    # --- discipline ---
    if acc.get("open_positions"):
        blocks.append("a position is already open: one trade at a time")
    if acc["trades_opened_today"] >= r["max_trades_per_day"]:
        blocks.append(f"{acc['trades_opened_today']} trades already today (max {r['max_trades_per_day']})")
    if acc["losses_today"] >= r["max_losses_per_day"]:
        blocks.append(f"{acc['losses_today']} losses today: done for the day")

    # --- geometry ---
    dist = abs(entry - stop)
    long = entry > stop
    if dist <= 0:
        blocks.append("stop equals entry")
        dist = 1e-9
    rr1 = (tp1 - entry) / dist * (1 if long else -1) if tp1 is not None else None
    rr2 = (tp2 - entry) / dist * (1 if long else -1) if tp2 is not None else None
    if rr2 is None:
        blocks.append("no final target (TP2) given")
    elif rr2 < r["min_rr_final"]:
        blocks.append(f"final target is only {rr2:.2f}R (min {r['min_rr_final']}R)")
    if rr1 is not None and rr1 <= 0:
        blocks.append("TP1 is on the wrong side of entry")

    # --- size ---
    pct, why = risk_tier(grade, acc.get("wins_in_row", 0), acc.get("losses_in_row", 0), r)
    if pct is None:
        blocks.append(why)
        pct = 0.0
    budget = min(pct * min(eq, bal), r["daily_room_share"] * max(daily_room, 0), r["max_room_share"] * max(max_room, 0))
    if budget < pct * min(eq, bal):
        notes.append(f"risk capped to {budget:.2f} by prop drawdown room")
    eff = dist + float(spec.get("spread_price") or 0)          # spread is paid on the way out too
    loss_per_lot = eff / spec["tick_size"] * spec["tick_value"]
    step = spec["volume_step"]
    lots = math.floor(budget / loss_per_lot / step + 1e-9) * step if loss_per_lot > 0 else 0
    lots = round(min(lots, spec["volume_max"]), 8)
    if pct and lots < spec["volume_min"]:
        blocks.append(f"min lot {spec['volume_min']} would risk {spec['volume_min'] * loss_per_lot:.2f} > budget {budget:.2f}")
        lots = 0.0
    half = math.floor(lots / 2 / step + 1e-9) * step
    partial_ok = half >= spec["volume_min"] and lots - half >= spec["volume_min"]
    if lots and not partial_ok:
        notes.append("position too small to split: no partial at TP1, move stop to break-even at TP1 instead")

    allowed = not blocks
    return {
        "allowed": allowed,
        "blocks": blocks,
        "lots": lots if allowed else 0.0,
        "tp1_close_lots": round(half, 8) if allowed and partial_ok else 0.0,
        "risk_pct_of_equity": round(lots * loss_per_lot / eq * 100, 3) if allowed else 0.0,
        "risk_amount": round(lots * loss_per_lot, 2) if allowed else 0.0,
        "rr_tp1": round(rr1, 2) if rr1 is not None else None,
        "rr_tp2": round(rr2, 2) if rr2 is not None else None,
        "tier": why,
        "notes": notes,
        "prop": prop,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed")
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--stop", type=float, required=True)
    ap.add_argument("--tp1", type=float)
    ap.add_argument("--tp2", type=float)
    ap.add_argument("--grade", required=True, choices=["A+", "A", "B", "C"])
    a = ap.parse_args()
    rules = load_rules()
    if not rules or not rules.get("initial_balance"):
        print(json.dumps({"allowed": False, "blocks": [f"no account config at {HOME / 'account.json'}: run setup first"]}))
        return 1
    feed = json.loads(Path(a.feed).read_text(encoding="utf-8"))
    if "error" in feed:
        print(json.dumps({"allowed": False, "blocks": [f"feed error: {feed['error']}"]}))
        return 1
    print(json.dumps(evaluate(feed, a.entry, a.stop, a.tp1, a.tp2, a.grade, rules), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
