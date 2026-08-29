# CloudRise

**Autonomous options intelligence with authority separated from reasoning.**

CloudRise is a paper-only Alpaca trading agent built for the Alpaca AI Trading Agents Hackathon. Four deterministic specialist agents debate liquid index setups; a separate, non-bypassable governor applies eleven portfolio and execution gates; the official Alpaca CLI reconciles the account and submits an atomic multi-leg option order only when every check passes.

The default experience is a fully functional, clearly labeled demo replay. It needs no API key, model credits, package downloads, or real capital.

## Why this can stand out

- **Meets every core rule:** autonomous agent, options trading, Alpaca Trading API, official Alpaca CLI, paper environment.
- **Defined risk by construction:** only 7–21 DTE vertical debit spreads; no naked short options and no real-money mode.
- **Atomic execution:** both legs are submitted as one Alpaca `mleg` limit order, avoiding partial-leg exposure.
- **Autonomous lifecycle:** existing spreads are reconciled first and closed atomically at the profit target, loss limit, or expiry window.
- **Explainable multi-agent intelligence:** regime, momentum, breakout, and reversion specialists emit independent scored evidence.
- **Authority boundary:** research can propose, but only the deterministic risk governor can authorize.
- **Judge-ready evidence:** every thesis, veto, risk decision, CLI reconciliation, and order is stored in an append-only JSONL ledger.
- **Zero Python dependencies:** Python 3.10+ is enough for the dashboard and agent; paper execution adds Alpaca's official CLI.

## Architecture

```text
Alpaca IEX bars + free indicative options chain
                       │
                       ▼
     ┌────────────────────────────────────┐
     │ Specialist research committee      │
     │ Regime · Momentum · Breakout · RSI │
     └────────────────────────────────────┘
                       │ scored thesis
                       ▼
     ┌────────────────────────────────────┐
     │ Spread constructor                 │
     │ 7–21 DTE · liquid · defined loss   │
     └────────────────────────────────────┘
                       │ proposed MLeg
                       ▼
     ┌────────────────────────────────────┐
     │ Non-bypassable risk governor       │
     │ 11 gates · sizing · circuit break  │
     └────────────────────────────────────┘
                       │ approved only
                       ▼
     Alpaca CLI → Trading API → paper account
                       │
                       ▼
              Immutable decision ledger
```

## Run the zero-credit demo

From this folder:

```powershell
python -m cloudrise serve
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). Press **Run agent cycle** to see the complete observe → debate → govern → execute trace. Demo mode never contacts Alpaca and never transmits an order.

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

## Publish the judge demo

The included container runs only the zero-credential replay and reads the host platform's `PORT` value. Build it on any container host, then use the resulting HTTPS address as the submission's app URL:

```powershell
docker build -t cloudrise-demo .
docker run --rm -p 8787:8787 cloudrise-demo
```

The public server is allowed only when `CLOUDRISE_MODE=demo`. Paper mode rejects any non-local bind address, so Alpaca credentials and order authority remain on the private competition runner.

## Connect the required fresh Alpaca paper account

> For judging, create a brand-new Alpaca paper account dedicated to this hackathon and set its starting balance to **$100,000**. Do not reuse a development account. Record its account ID for the final lablab.ai submission.

1. Install the official Alpaca CLI:

   ```powershell
   go install github.com/alpacahq/cli/cmd/alpaca@latest
   alpaca version
   alpaca doctor
   ```

2. Create paper API keys in the fresh account. Set them only in the current terminal session; do not paste them into source files:

   ```powershell
   $env:CLOUDRISE_MODE="paper"
   $env:ALPACA_API_KEY="YOUR_FRESH_PAPER_KEY"
   $env:ALPACA_SECRET_KEY="YOUR_FRESH_PAPER_SECRET"
   ```

3. Verify the full safety and integration chain:

   ```powershell
   python -m cloudrise preflight
   ```

4. Preview one cycle while the market is open:

   ```powershell
   python -m cloudrise cycle
   ```

   In `paper` mode, an approved cycle can place a simulated paper order. Review the configured limits first.

5. Run autonomously every 15 minutes:

   ```powershell
   python -m cloudrise watch
   ```

6. Keep the dashboard running in another terminal:

   ```powershell
   $env:CLOUDRISE_MODE="paper"
   $env:ALPACA_API_KEY="YOUR_FRESH_PAPER_KEY"
   $env:ALPACA_SECRET_KEY="YOUR_FRESH_PAPER_SECRET"
   python -m cloudrise serve
   ```

## The trading logic

CloudRise scans `SPY`, `QQQ`, and `IWM` on 15-minute bars. Index ETFs avoid single-company earnings gaps during a seven-day competition. The committee combines:

| Specialist | Evidence | Weight |
|---|---|---:|
| Regime | 8/21 EMA separation | 38% |
| Momentum | 12-bar return | 30% |
| Breakout | Location in the prior 20-bar channel | 22% |
| Reversion | RSI exhaustion veto | 10% |

A directional thesis requires a score beyond ±0.24 and at least 60% specialist agreement. The options constructor then targets approximately 0.55-delta long and 0.30-delta short legs at the expiration nearest 12 DTE. When Greeks are unavailable on the free indicative feed, transparent moneyness targets are used instead.

The entry price is conservative: long ask minus short bid. The order is rejected if that debit is non-positive, exceeds the strike width, quotes are too wide, or reward/risk is below 0.60×.

Before looking for a new entry, every cycle groups Alpaca option positions into spreads and evaluates their return on defined risk. CloudRise submits one atomic closing `mleg` when a spread reaches **+35%**, falls to **−45%**, or enters the **≤3 DTE** expiry window. Exit management takes priority over opening new risk.

## Non-bypassable gates

1. Paper-only runtime invariant.
2. Regular market session must be open.
3. Daily loss must remain above the −1.5% circuit breaker.
4. Committee confidence must be at least 62%.
5. Directional specialist agreement must be at least 60%.
6. One contract must fit inside the 0.6% per-trade loss budget.
7. Defined portfolio risk after entry must remain below 2.5%.
8. Fewer than three spreads may be open.
9. No duplicate underlying exposure.
10. Executable quote liquidity must pass.
11. Maximum profit / maximum loss must be at least 0.60×.

Order size is capped at three spread units even if the risk budget permits more. A unique `client_order_id` makes accidental duplicate submission detectable by Alpaca.

## Safety invariants

- `CLOUDRISE_MODE` accepts only `demo` or `paper`.
- Any truthy `ALPACA_LIVE_TRADE` value aborts startup.
- The child CLI process always receives `ALPACA_LIVE_TRADE=false`.
- Paper mode binds to `127.0.0.1` only; public binding is restricted to the zero-credential demo.
- Credentials are read from environment variables and never returned by an API, logged, or written to the ledger.
- Subprocesses use argument arrays with `shell=False`.
- The dashboard remains available if Alpaca is temporarily unreachable.

## Repository map

```text
cloudrise/
  agent.py          autonomous orchestration
  alpaca_cli.py     official CLI control plane
  alpaca_data.py    market-data REST adapter with retries
  strategy.py       research committee + MLeg construction
  positions.py      autonomous spread reconciliation + exits
  risk.py           hard portfolio governor
  ledger.py         append-only audit trail
  server.py         dependency-free local dashboard/API
web/                responsive judge-facing dashboard
Dockerfile          portable public demo deployment
tests/              deterministic unit and safety tests
SUBMISSION.md       paste-ready lablab.ai submission copy
ONE_PAGE_WRITEUP.md required AI/risk/infrastructure write-up
DEMO_SCRIPT.md      90-second presentation script and shot list
SOCIAL_POSTS.md     five build-in-public drafts
```

## Important disclosure

CloudRise is for the Alpaca paper-trading environment and educational demonstration only. Demo results are synthetic and clearly labeled; they do not represent actual brokerage performance. Options are high risk. Nothing in this project is investment advice, and hypothetical performance does not guarantee future results.
