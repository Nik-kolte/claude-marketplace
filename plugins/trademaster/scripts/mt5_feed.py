"""Read-only MT5 snapshot for the trademaster agent. NEVER sends orders.

Usage:  python mt5_feed.py XAUUSD [--out feed.json]
Prints JSON: clock/killzone (New York time), account + prop status, symbol spec,
ICT reference levels, and per-timeframe swings / FVGs / equal highs-lows / structure.
Only dependency: MetaTrader5 (pip install MetaTrader5). Bars used are CLOSED bars only.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print(json.dumps({"error": "MetaTrader5 package missing: pip install MetaTrader5"}))
    sys.exit(1)

TFS = {"D1": (mt5.TIMEFRAME_D1, 40, 8), "H4": (mt5.TIMEFRAME_H4, 90, 18), "H1": (mt5.TIMEFRAME_H1, 120, 24),
       "M15": (mt5.TIMEFRAME_M15, 192, 32), "M5": (mt5.TIMEFRAME_M5, 288, 36)}  # (tf, bars analysed, bars printed)
KILLZONES = [("Asia", 20, 0, 23, 0), ("London", 2, 0, 5, 0), ("NY AM", 7, 0, 10, 0), ("NY PM", 13, 30, 16, 0)]


# ---------- time ----------
def _nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def ny_offset(utc: datetime) -> int:
    """US DST: 2nd Sun Mar 02:00 local -> 1st Sun Nov 02:00 local."""
    y = utc.year
    start = _nth_sunday(y, 3, 2).replace(hour=7, tzinfo=timezone.utc)   # 02:00 EST = 07:00 UTC
    end = _nth_sunday(y, 11, 1).replace(hour=6, tzinfo=timezone.utc)    # 02:00 EDT = 06:00 UTC
    return -4 if start <= utc < end else -5


def to_ny(utc: datetime) -> datetime:
    return (utc + timedelta(hours=ny_offset(utc))).replace(tzinfo=None)


def load_cfg():
    """account.json from $TRADEMASTER_HOME (default ~/.trademaster); {} if absent."""
    import os
    from pathlib import Path
    p = Path(os.environ.get("TRADEMASTER_HOME", Path.home() / ".trademaster")) / "account.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def enabled_killzones(cfg=None):
    names = (cfg if cfg is not None else load_cfg()).get("killzones_enabled")
    return [k for k in KILLZONES if names is None or k[0] in names]


def market_closed(ny: datetime) -> bool:
    """FX/metals weekend: Fri 17:00 -> Sun 17:00 New York."""
    wd, h = ny.weekday(), ny.hour
    return wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 17)


def killzone(ny: datetime, zones=KILLZONES):
    if market_closed(ny):
        return None
    m = ny.hour * 60 + ny.minute
    for name, h1, m1, h2, m2 in zones:
        if h1 * 60 + m1 <= m < h2 * 60 + m2:
            return name
    return None


def next_killzone(ny: datetime, zones=KILLZONES):
    """Next killzone start (skipping the weekend) -> {name, starts_in_min, starts_ny}."""
    best = None
    for day in range(0, 4):
        for name, h, mm, _, _ in zones:
            start = ny.replace(hour=h, minute=mm, second=0, microsecond=0) + timedelta(days=day)
            if start > ny and not market_closed(start) and (best is None or start < best[1]):
                best = (name, start)
        if best:
            break
    return {"name": best[0], "starts_in_min": int((best[1] - ny).total_seconds() // 60),
            "starts_ny": best[1].strftime("%a %H:%M")} if best else None


# ---------- analytics (pure, on list-of-dict bars, oldest first) ----------
def atr(bars, n=14):
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-n:]) / min(n, len(trs)) if trs else 0.0


def swings(bars, k=2):
    hi, lo = [], []
    for i in range(k, len(bars) - k):
        win = bars[i - k:i + k + 1]
        if bars[i]["h"] == max(b["h"] for b in win):
            hi.append({"t": bars[i]["t"], "price": bars[i]["h"], "i": i})
        if bars[i]["l"] == min(b["l"] for b in win):
            lo.append({"t": bars[i]["t"], "price": bars[i]["l"], "i": i})
    for s in hi:
        s["taken"] = any(b["h"] > s["price"] for b in bars[s["i"] + 1:])
    for s in lo:
        s["taken"] = any(b["l"] < s["price"] for b in bars[s["i"] + 1:])
    return hi, lo


def fvgs(bars, a):
    out = []
    for i in range(2, len(bars)):
        p2, mid, cur = bars[i - 2], bars[i - 1], bars[i]
        disp = abs(mid["c"] - mid["o"]) >= 1.2 * a if a else False
        if cur["l"] > p2["h"]:
            lo_, hi_, d = p2["h"], cur["l"], "bullish"
            later = bars[i + 1:]
            touched = any(b["l"] <= hi_ for b in later)
            filled = any(b["l"] <= lo_ for b in later)
        elif cur["h"] < p2["l"]:
            lo_, hi_, d = cur["h"], p2["l"], "bearish"
            later = bars[i + 1:]
            touched = any(b["h"] >= lo_ for b in later)
            filled = any(b["h"] >= hi_ for b in later)
        else:
            continue
        if not filled:
            out.append({"dir": d, "t": mid["t"], "low": lo_, "high": hi_, "ce": round((lo_ + hi_) / 2, 5),
                        "state": "mitigated" if touched else "fresh", "displacement": disp})
    return out[-6:]


def equal_levels(points, tol):
    pools, live = [], [p for p in points if not p["taken"]]
    for i in range(len(live)):
        for j in range(i + 1, len(live)):
            if abs(live[i]["price"] - live[j]["price"]) <= tol:
                pools.append({"price": round(max(live[i]["price"], live[j]["price"]), 5),
                              "touches": [live[i]["t"], live[j]["t"]]})
    return pools[-4:]


def structure(bars, hi, lo, a, k=2):
    """Candle CLOSES through swing points. A break is an MSS when the swings confirmed before it showed the
    opposite order flow (bullish break after lower highs or lower lows, and vice versa); otherwise BOS."""
    def flow_before(j):
        h = [s["price"] for s in hi if s["i"] + k < j][-2:]
        l = [s["price"] for s in lo if s["i"] + k < j][-2:]
        down = (len(h) == 2 and h[1] < h[0]) or (len(l) == 2 and l[1] < l[0])
        up = (len(h) == 2 and h[1] > h[0]) or (len(l) == 2 and l[1] > l[0])
        return "bearish" if down and not up else "bullish" if up and not down else "mixed"

    events = []
    for s, d in [(x, "bullish") for x in hi] + [(x, "bearish") for x in lo]:
        for j in range(s["i"] + k + 1, len(bars)):  # swing must be confirmed before it can be broken
            b = bars[j]
            if (d == "bullish" and b["c"] > s["price"]) or (d == "bearish" and b["c"] < s["price"]):
                prior = flow_before(j)
                events.append({"j": j, "dir": d, "level": s["price"], "t": b["t"],
                               "type": "MSS" if prior not in (d, "mixed") else "BOS",
                               "displacement": abs(b["c"] - b["o"]) >= 1.2 * a if a else False})
                break
    events.sort(key=lambda e: e["j"])
    for prev, e in zip(events, events[1:]):
        if e["type"] == "MSS" and prev["dir"] == e["dir"]:
            e["type"] = "BOS"  # only the first break of a new direction is the shift
    strip = lambda e: {x: v for x, v in e.items() if x != "j"} if e else None
    return {"last_break": strip(events[-1] if events else None),
            "last_mss": strip(next((e for e in reversed(events) if e["type"] == "MSS"), None)),
            "breaks_last_10": [f"{e['dir']} {e['type']}" for e in events[-10:]]}


def analyse(bars, show):
    a = atr(bars)
    hi, lo = swings(bars)
    tol = 0.1 * a
    clean = lambda xs: [{k: v for k, v in x.items() if k != "i"} for x in xs[-5:]]
    return {
        "atr14": round(a, 5),
        "swing_highs": clean(hi), "swing_lows": clean(lo),
        "equal_highs_BSL": equal_levels(hi, tol), "equal_lows_SSL": equal_levels(lo, tol),
        "unfilled_fvgs": fvgs(bars, a),
        "structure": structure(bars, hi, lo, a),
        "range_high": max(b["h"] for b in bars[-show:]), "range_low": min(b["l"] for b in bars[-show:]),
        "bars": [[b["t"], b["o"], b["h"], b["l"], b["c"]] for b in bars[-show:]],
    }


# ---------- MT5 ----------
def resolve(base):
    if mt5.symbol_info(base):
        name = base
    else:
        cands = [s for s in (mt5.symbols_get(f"*{base}*") or []) if s.name.upper().startswith(base[:6])]
        if not cands:
            return None
        name = min(cands, key=lambda s: len(s.name)).name
    mt5.symbol_select(name, True)
    return name


def get_bars(sym, tf, n, offset_h):
    r = mt5.copy_rates_from_pos(sym, tf, 1, n)  # pos 1 = skip forming bar
    if r is None:
        return []
    out = []
    for x in r:
        utc = datetime.fromtimestamp(int(x["time"]), timezone.utc) - timedelta(hours=offset_h)
        out.append({"t": to_ny(utc).strftime("%m-%d %H:%M"), "utc": utc, "o": float(x["open"]), "h": float(x["high"]),
                    "l": float(x["low"]), "c": float(x["close"]), "sp": int(x["spread"])})
    return out


def window(bars, ny_start, ny_end):
    sel = [b for b in bars if ny_start <= to_ny(b["utc"]) < ny_end]
    return ({"high": max(b["h"] for b in sel), "low": min(b["l"] for b in sel)} if sel else None)


def account_block(now_srv):
    ai = mt5.account_info()
    day0 = now_srv.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(day0, now_srv + timedelta(hours=1)) or []
    closed_today = sum(d.profit + d.commission + d.swap for d in deals if d.entry in (1, 3))
    entries_today = len({d.position_id for d in deals if d.entry == 0})
    by_pos = {}
    for d in (mt5.history_deals_get(now_srv - timedelta(days=30), now_srv + timedelta(hours=1)) or []):
        if d.entry in (1, 3):
            p = by_pos.setdefault(d.position_id, {"pnl": 0.0, "time": d.time, "today": d.time >= day0.timestamp()})
            p["pnl"] += d.profit + d.commission + d.swap
            p["time"] = max(p["time"], d.time)
    closed = sorted(by_pos.values(), key=lambda p: p["time"])
    wins_row = losses_row = 0
    for p in reversed(closed):
        if p["pnl"] > 0 and losses_row == 0:
            wins_row += 1
        elif p["pnl"] <= 0 and wins_row == 0:
            losses_row += 1
        else:
            break
    positions = [{"symbol": p.symbol, "side": "LONG" if p.type == 0 else "SHORT", "lots": p.volume,
                  "open": p.price_open, "sl": p.sl, "tp": p.tp, "pnl": p.profit} for p in (mt5.positions_get() or [])]
    return {
        "login": ai.login, "server": ai.server, "currency": ai.currency,
        "trade_mode": {0: "demo", 1: "contest", 2: "real"}.get(ai.trade_mode, ai.trade_mode),
        "balance": ai.balance, "equity": ai.equity,
        "closed_pnl_today": round(closed_today, 2),
        "day_start_balance": round(ai.balance - closed_today, 2),
        "floating_pnl": round(ai.equity - ai.balance, 2),
        "trades_opened_today": entries_today,
        "losses_today": sum(1 for p in closed if p["today"] and p["pnl"] <= 0),
        "wins_in_row": wins_row, "losses_in_row": losses_row,
        "open_positions": positions,
    }


def brief(o):
    """Compact text view for frequent desk reads (~2k tokens). Nearest levels only."""
    c, a, sp, lv = o["clock"], o["account"], o["spec"], o["levels"]
    px = lv["price_bid"] or 0
    f = lambda v: "-" if v is None else (f"{v:.5f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))
    rng = lambda r: f"{f(r['high'])}/{f(r['low'])}" if r else "-"
    L = [f"{o['symbol']} {f(px)} | NY {c['new_york']} | local {c['local']} | KZ {c['killzone_now'] or 'none'}"
         f" | next {c['next_killzone']['name'] + ' in ' + str(c['next_killzone']['starts_in_min']) + 'm' if c['next_killzone'] else '-'}"
         f" | market {'open' if c['market_open'] else 'CLOSED'}",
         f"acct eq {a['equity']} bal {a['balance']} todayPnL {a['closed_pnl_today']} float {a['floating_pnl']}"
         f" | trades {a['trades_opened_today']} losses {a['losses_today']} | streak W{a['wins_in_row']}/L{a['losses_in_row']}"
         f" | open {[(p['symbol'], p['side'], p['lots'], p['open'], p['sl'], p['tp'], round(p['pnl'], 2)) for p in a['open_positions']] or 'none'}",
         f"spread {sp['spread_points']}pts (median {sp['spread_median_m5']})",
         f"levels midnight {f(lv['ny_midnight_open'])} ({(lv.get('price_vs_midnight_open') or '-').split(' ')[0]}) | asia {rng(lv['asia_range_8pm_12am'])}"
         f" | london {rng(lv['london_range_2_5am'])} | PDH/PDL {f(lv['PDH'])}/{f(lv['PDL'])} | PWH/PWL {f(lv['PWH'])}/{f(lv['PWL'])}"]
    for tf, t in o["timeframes"].items():
        if "error" in t:
            L.append(f"{tf}: {t['error']}")
            continue
        A = t["atr14"]
        near = lambda xs: [x for x in xs if abs(x["price"] - px) <= 4 * A]
        up = sorted([s["price"] for s in t["swing_highs"] if not s["taken"] and s["price"] > px])[:2]
        dn = sorted([s["price"] for s in t["swing_lows"] if not s["taken"] and s["price"] < px], reverse=True)[:2]
        st = t["structure"]
        lb, ms = st["last_break"], st["last_mss"]
        fv = [f"{g['dir'][:4]} {f(g['low'])}-{f(g['high'])} {g['state'][0]}{'D' if g['displacement'] else ''} @{g['t']}"
              for g in t["unfilled_fvgs"] if min(abs(g["low"] - px), abs(g["high"] - px)) <= 4 * A]
        L.append(f"{tf} atr {f(round(A, 2))} | last {lb['dir'] + ' ' + lb['type'] + ('+D' if lb['displacement'] else '') + ' ' + f(lb['level']) + ' @' + lb['t'] if lb else '-'}"
                 f" | lastMSS {ms['dir'] + ('+D' if ms['displacement'] else '') + ' ' + f(ms['level']) + ' @' + ms['t'] if ms else '-'}"
                 f" | untaken highs {up} lows {dn} | EQH {[e['price'] for e in near(t['equal_highs_BSL'])]} EQL {[e['price'] for e in near(t['equal_lows_SSL'])]}"
                 f" | FVG {fv}")
    for tf, n in (("M15", 4), ("M5", 8)):
        L.append(f"{tf} bars " + " ".join(f"[{b[0][6:]} {f(b[1])} {f(b[2])} {f(b[3])} {f(b[4])}]" for b in o["timeframes"][tf].get("bars", [])[-n:]))
    L.append("FVG state: f=fresh m=mitigated, D=displacement. Times NY.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--out")
    ap.add_argument("--brief", action="store_true", help="print a compact text summary (full JSON still goes to --out)")
    args = ap.parse_args()
    cfg = load_cfg()
    zones = enabled_killzones(cfg)

    if not mt5.initialize():
        print(json.dumps({"error": f"MT5 init failed {mt5.last_error()} - open the terminal and log in"}))
        return 1
    try:
        sym = resolve(args.symbol.upper())
        if not sym:
            print(json.dumps({"error": f"symbol {args.symbol} not found at this broker"}))
            return 1
        utc_now = datetime.now(timezone.utc)
        tick = mt5.symbol_info_tick(sym)
        tick_age_s = None
        offset_h, offset_ok = 0, False
        if tick and tick.time:
            raw = (tick.time - utc_now.timestamp()) / 3600
            offset_h = round(raw)
            tick_age_s = int(abs(raw - offset_h) * 3600)
            offset_ok = tick_age_s < 600
        now_srv = datetime.fromtimestamp(utc_now.timestamp(), timezone.utc) + timedelta(hours=offset_h)
        ny = to_ny(utc_now)
        local = utc_now + timedelta(minutes=cfg.get("local_utc_offset_min", 0))
        info = mt5.symbol_info(sym)

        tfdata, raw_bars = {}, {}
        for name, (tf, n, show) in TFS.items():
            raw_bars[name] = get_bars(sym, tf, n, offset_h)
            tfdata[name] = analyse(raw_bars[name], show) if len(raw_bars[name]) > 20 else {"error": "not enough bars"}

        m15 = raw_bars["M15"]
        # trading day rolls at 17:00 NY: from then on, the Asia range being built belongs to tomorrow
        today0 = ny.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1 if ny.hour >= 17 else 0)
        midnight = next((b for b in m15 if to_ny(b["utc"]) == today0), None)
        d1 = raw_bars["D1"]
        w1 = get_bars(sym, mt5.TIMEFRAME_W1, 3, offset_h)
        levels = {
            "price_bid": tick.bid if tick else None, "price_ask": tick.ask if tick else None,
            "ny_midnight_open": midnight["o"] if midnight else None,
            "asia_range_8pm_12am": window(m15, today0 - timedelta(hours=4), today0),
            "london_range_2_5am": window(m15, today0 + timedelta(hours=2), today0 + timedelta(hours=5)),
            "PDH": d1[-1]["h"] if d1 else None, "PDL": d1[-1]["l"] if d1 else None,
            "PWH": w1[-1]["h"] if w1 else None, "PWL": w1[-1]["l"] if w1 else None,
        }
        if levels["ny_midnight_open"] and tick:
            levels["price_vs_midnight_open"] = "above (premium of day)" if tick.bid > levels["ny_midnight_open"] else "below (discount of day)"

        out = {
            "symbol": sym,
            "clock": {"utc": utc_now.strftime("%Y-%m-%d %H:%M"), "new_york": ny.strftime("%a %Y-%m-%d %H:%M"),
                      "local": local.strftime("%a %H:%M"),
                      "killzone_now": killzone(ny, zones), "next_killzone": next_killzone(ny, zones),
                      "killzones_enabled": [z[0] for z in zones],
                      "market_open": offset_ok, "last_tick_age_s": tick_age_s,
                      "warning": None if offset_ok else "no fresh tick: market closed or feed down -> NO TRADE"},
            "account": account_block(now_srv),
            "spec": {"digits": info.digits, "point": info.point, "spread_points": info.spread,
                     "spread_price": round(info.spread * info.point, info.digits),
                     "spread_median_m5": sorted(b["sp"] for b in raw_bars["M5"])[len(raw_bars["M5"]) // 2] if raw_bars["M5"] else None,
                     "tick_size": info.trade_tick_size, "tick_value": info.trade_tick_value,
                     "contract_size": info.trade_contract_size, "volume_min": info.volume_min,
                     "volume_step": info.volume_step, "volume_max": info.volume_max},
            "levels": levels,
            "timeframes": tfdata,
            "notes": "times are New York local; bars = [time, o, h, l, c], closed bars only, oldest first",
        }
        text = json.dumps(out, indent=1, default=str)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
        print(brief(out) if args.brief else text)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
