# CloudRise — Autonomous Options Intelligence

## The idea

Most trading agents combine market interpretation and order authority inside one opaque model. CloudRise separates them. A transparent committee of specialist agents can propose a trade, but it cannot move capital. A deterministic risk governor—with rules the research layer cannot rewrite—must approve the setup before a dedicated execution layer can send an order. This makes autonomy observable, falsifiable, and safer.

CloudRise trades only liquid index ETF vertical debit spreads in Alpaca's paper environment. The approach is designed for a short competition window: 15-minute signals react within the day, while 7–21 DTE options reduce same-day expiry noise. Defined-risk spreads provide convex directional exposure with maximum loss known before entry. `SPY`, `QQQ`, and `IWM` avoid single-company earnings events and usually offer deeper options liquidity.

## AI logic

Every scan begins with adjusted 15-minute Alpaca IEX bars. Four independent specialists emit a normalized score and human-readable evidence:

- **Regime agent (38%)** measures the separation of 8- and 21-period exponential moving averages.
- **Momentum agent (30%)** measures the 12-bar return.
- **Breakout agent (22%)** locates price inside the previous 20-bar channel.
- **Reversion agent (10%)** uses RSI as an exhaustion veto.

The weighted committee must exceed ±0.24 and reach at least 60% directional agreement. Confidence incorporates signal strength, agreement, realized volatility quality, and noise. This deterministic ensemble needs no model credits, is reproducible in tests, and exposes exactly why a decision was reached.

For a bullish thesis, CloudRise proposes a bull call debit spread; for bearish, a bear put debit spread. It chooses the expiration closest to 12 days inside a 7–21 DTE window, targets approximately 0.55 delta for the long leg and 0.30 delta for the short leg, and falls back to transparent moneyness targets if Greeks are unavailable. A conservative executable debit—long ask minus short bid—is used to calculate maximum loss and profit before authorization.

## Risk gates

The separate governor applies eleven non-bypassable checks: paper-only mode, open regular session, −1.5% daily loss circuit, ≥62% confidence, ≥60% agreement, 0.6% per-trade loss budget, 2.5% total portfolio defined-risk budget, maximum three open spreads, no duplicate underlying, quote-liquidity threshold, and ≥0.60 reward/risk. Position size is capped at three spread units. A failed gate creates a timestamped no-trade record; it cannot be overridden by the committee or execution layer.

Position authority is autonomous after entry as well. Before scanning for new exposure, CloudRise reconciles open option legs into spreads and prioritizes an atomic closing order at +35% return on defined risk, −45% loss, or ≤3 days to expiration. This makes the lifecycle explicit and prevents a new signal from taking precedence over an existing risk event.

## Alpaca implementation

CloudRise uses Alpaca's Market Data API for 15-minute stock bars and the free `indicative` options chain, including quotes and Greeks when available. Before each cycle, Alpaca's official CLI reconciles the account, market clock, positions, and orders through structured JSON. Approved legs are submitted through the CLI's raw Trading API access as a single atomic `order_class: mleg` limit order with `buy_to_open` and `sell_to_open` intents. A unique client order ID reduces duplicate-submission risk.

The application rejects live mode at startup and forces `ALPACA_LIVE_TRADE=false` in every CLI child process. Credentials remain in environment variables and never enter the UI or audit trail. Every thesis, veto, risk decision, command name, and broker response is appended to a local JSONL decision ledger, creating judge-ready proof of autonomous behavior.

The polished dashboard shows paper equity, open defined-risk positions, committee votes, active gates, and the immutable reasoning trace. Its zero-credit demo replay is explicitly labeled and never transmits orders; the competition run uses a fresh $100,000 Alpaca paper account as required.
