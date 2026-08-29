# lablab.ai submission — paste-ready package

## Project title

CloudRise — Autonomous Options Intelligence

## Short description

An explainable, paper-only options agent where four specialists debate each setup, eleven hard risk gates control authority, and Alpaca CLI executes atomic defined-risk spreads.

## Long description

CloudRise asks a different question: not only “can an AI agent find alpha?” but “can we prove that its authority is controlled?”

Four deterministic specialists—regime, momentum, breakout, and reversion—independently score liquid index ETF opportunities using Alpaca market data. Their weighted thesis must clear direction, confidence, and agreement thresholds. A separate options constructor selects a liquid 7–21 DTE vertical debit spread and calculates its exact maximum loss from executable quotes.

The research layer still cannot trade. Eleven non-bypassable gates enforce paper-only mode, market hours, daily loss, trade and portfolio risk, position concentration, liquidity, reward/risk, and duplicate exposure. Only after every gate passes does the execution layer use Alpaca's official CLI and Trading API to submit one atomic multi-leg limit order. Every proposal, veto, approval, command, and broker response is written to an append-only decision ledger.

The agent also owns the exit lifecycle. At the start of each cycle it reconciles open legs into spreads, then prioritizes an atomic closing MLeg at +35% return on defined risk, −45% loss, or ≤3 DTE before considering any new entry.

The result is an autonomous agent that is explainable by design, credit-free to operate, safe to demo, and directly auditable by judges. A polished dashboard makes the entire observe → debate → govern → execute loop visible in real time.

Demo replay results are synthetic and clearly labeled. Competition performance comes from the dedicated fresh $100,000 Alpaca paper account.

## Technology tags

Alpaca Trading API · Alpaca Market Data API · Alpaca CLI · Options · Multi-agent AI · Algorithmic Trading · Python · Paper Trading · Explainable AI · Risk Management

## Category tags

Options Alpha Agents · Autonomous Agents · FinTech

## Links to replace before submission

- Public GitHub repository: `ADD_PUBLIC_GITHUB_URL`
- Hosted dashboard: `ADD_APPLICATION_URL`
- Video presentation: `ADD_VIDEO_URL`
- Slide presentation: `ADD_SLIDE_URL`
- Fresh Alpaca paper account ID: `ADD_FRESH_ACCOUNT_ID`
- Social post 1: `ADD_URL`
- Social post 2: `ADD_URL`
- Social post 3: `ADD_URL`
- Social post 4: `ADD_URL`
- Social post 5: `ADD_URL`

## Final eligibility checklist

- [ ] Repository is public and uses the included MIT license.
- [ ] Fresh paper account was created only for this hackathon.
- [ ] Starting balance was set to exactly $100,000 before the first run.
- [ ] Submitted account ID matches the account used by CloudRise.
- [ ] Dashboard shows real paper data, not demo replay, during judging.
- [ ] Options orders appear as MLeg activity in the account.
- [ ] One-page write-up is attached.
- [ ] Cover image, video, and slide presentation are uploaded.
- [ ] Up to five public posts tag both lablab.ai and Alpaca.
- [ ] No API keys, secrets, `.env`, or private account data are committed.
- [ ] `python -m unittest discover -s tests -v` passes on the public commit.
