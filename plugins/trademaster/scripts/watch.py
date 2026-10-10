"""Trademaster alarm clock. Claude arms it with the levels IT chose; it exits (waking Claude) on the first event.

  python watch.py XAUUSD --when close_above:4143.31 --when above:4148.34 --cancel above:4170.22 --until-ny 10:00
  python watch.py XAUUSD --until-killzone            # sleep until the next enabled killzone starts

Conditions (--when = trigger, --cancel = invalidation; repeatable):
  above:P / below:P              bid trades at/through P
  close_above:P / close_below:P  a CLOSED bar on --tf (default M5) closes beyond P
Deadlines: --until-ny HH:MM (New York), --minutes N, --until-killzone. Without any, it exits at the end of the
current enabled killzone, or at the next killzone start if none is active.
Always exits on: an open-position change (trade taken/closed), MT5 failure, or market close.
Prints exactly one JSON line. Only one watcher runs at a time: starting a new one stops the old one.
Read-only: never sends orders.
"""
import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mt5_feed as F  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

HOME = Path(os.environ.get("TRADEMASTER_HOME", Path.home() / ".trademaster"))
PIDFILE = HOME / "watch.pid"
TFMAP = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15}


def emit(event, **kw):
    now = datetime.now(timezone.utc)
    print(json.dumps({"event": event, "ny": F.to_ny(now).strftime("%a %H:%M"), **kw}), flush=True)


def parse(conds):
    out = []
    for c in conds or []:
        kind, _, p = c.partition(":")
        if kind not in ("above", "below", "close_above", "close_below"):
            raise SystemExit(f"bad condition {c}")
        out.append((kind, float(p)))
    return out


def hit(kind, level, bid, last_close):
    return ((kind == "above" and bid >= level) or (kind == "below" and bid <= level)
            or (kind == "close_above" and last_close is not None and last_close > level)
            or (kind == "close_below" and last_close is not None and last_close < level))


def claim_singleton():
    HOME.mkdir(parents=True, exist_ok=True)
    if PIDFILE.exists():
        try:
            old = int(PIDFILE.read_text().split()[0])
            if old != os.getpid():
                os.kill(old, signal.SIGTERM)
        except (ValueError, OSError):
            pass
    PIDFILE.write_text(f"{os.getpid()} {' '.join(sys.argv[1:])}")


def deadline(args, zones):
    now = datetime.now(timezone.utc)
    ny = F.to_ny(now)
    if args.minutes:
        return now + timedelta(minutes=args.minutes), f"{args.minutes} min elapsed"
    if args.until_ny:
        h, m = map(int, args.until_ny.split(":"))
        t = ny.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= ny:
            t += timedelta(days=1)
        return now + (t - ny), f"reached {args.until_ny} NY"
    kz = F.killzone(ny, zones)
    if kz and not args.until_killzone:
        end = next((z for z in zones if z[0] == kz))
        t = ny.replace(hour=end[3], minute=end[4], second=0, microsecond=0)
        return now + (t - ny), f"{kz} killzone ended"
    nk = F.next_killzone(ny, zones)
    return now + timedelta(minutes=nk["starts_in_min"]), f"{nk['name']} killzone starting"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--when", action="append")
    ap.add_argument("--cancel", action="append")
    ap.add_argument("--tf", default="M5", choices=list(TFMAP))
    ap.add_argument("--until-ny")
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--until-killzone", action="store_true")
    ap.add_argument("--poll", type=float, default=5.0)
    a = ap.parse_args()
    triggers, cancels = parse(a.when), parse(a.cancel)
    zones = F.enabled_killzones()
    claim_singleton()
    end, end_reason = deadline(a, zones)

    if not mt5.initialize():
        emit("ERROR", reason=f"MT5 init failed {mt5.last_error()}")
        return 1
    try:
        sym = F.resolve(a.symbol.upper())
        if not sym:
            emit("ERROR", reason=f"symbol {a.symbol} not found")
            return 1
        positions0 = {p.ticket for p in (mt5.positions_get() or [])}
        last_bar_t, last_close = None, None
        while True:
            now = datetime.now(timezone.utc)
            if now >= end:
                emit("DEADLINE", reason=end_reason, symbol=sym)
                return 0
            if F.market_closed(F.to_ny(now)):
                emit("MARKET_CLOSED", symbol=sym)
                return 0
            tick = mt5.symbol_info_tick(sym)
            if tick is None:
                emit("ERROR", reason=f"lost MT5 connection {mt5.last_error()}")
                return 1
            pos = {p.ticket for p in (mt5.positions_get() or [])}
            if pos != positions0:
                emit("POSITION_CHANGE", opened=len(pos - positions0), closed=len(positions0 - pos), symbol=sym)
                return 0
            r = mt5.copy_rates_from_pos(sym, TFMAP[a.tf], 1, 1)
            if r is not None and len(r) and r[0]["time"] != last_bar_t:
                # close conditions only count bars that close AFTER arming
                last_close = float(r[0]["close"]) if last_bar_t is not None else None
                last_bar_t = r[0]["time"]
            for kind, lvl in cancels:
                if hit(kind, lvl, tick.bid, last_close):
                    emit("CANCEL", cond=f"{kind}:{lvl}", bid=tick.bid, last_close=last_close, symbol=sym)
                    return 0
            for kind, lvl in triggers:
                if hit(kind, lvl, tick.bid, last_close):
                    emit("TRIGGER", cond=f"{kind}:{lvl}", bid=tick.bid, last_close=last_close, symbol=sym)
                    return 0
            time.sleep(a.poll)
    finally:
        mt5.shutdown()
        try:
            if PIDFILE.exists() and PIDFILE.read_text().split()[0] == str(os.getpid()):
                PIDFILE.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
