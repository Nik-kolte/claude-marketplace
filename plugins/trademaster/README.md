# trademaster

ICT trade desk for XAUUSD, EURUSD and GBPUSD under prop-challenge rules. It decides and plans; it never places orders.

- **Skill** `/trademaster:trademaster [XAUUSD|EURUSD|GBPUSD|setup|manage|review]`: interactive. Asks about your account, confirms equity and P&L, analyses, sizes the trade, and logs the call.
- **Agent** `trademaster`: the same decision process without questions, for background checks or `/loop`.

## Requirements

- MetaTrader 5 terminal open and logged in.
- A dedicated venv: `py -3.12 -m venv ~/.trademaster/venv && ~/.trademaster/venv/Scripts/python -m pip install MetaTrader5`.
- Optional: TradingView MCP connected, for visual confirmation and drawing levels.

## How the work is split

| Piece | Who decides |
|---|---|
| Levels, swings, FVGs, killzone, account state | `scripts/mt5_feed.py` (fixed rules) |
| Bias, model, grade | the LLM, following `references/ict-playbook.md` |
| Allowed? Lot size? Prop room? | `scripts/risk_calc.py` (fixed rules, final say) |
| Track record | `scripts/journal.py` → `~/.trademaster/journal.csv` |

The grading and models are a written-down discretionary method, not a backtested strategy. Judge it with `review` after 30–100 logged trades before trusting it with size.

## Desk mode (always-on)

```
/loop /trademaster:trademaster desk
```
Claude reads the market (compact `--brief` feed), then arms `scripts/watch.py` in the background on levels it chose itself, plus a 30-minute fallback wake. The watcher exits on a trigger, an invalidation, a position change, a deadline or the next killzone, and that wakes Claude to look again. Outside the enabled killzones nothing runs. Trade alerts go to your phone via ntfy (`ntfy_topic` in account.json; `scripts/notify.py`). Requirements: PC awake, MT5 logged in, the Claude Code session left open.
