---
name: trading-recovery-protocol
description: Strategic parameters and risk management for XAUUSD recovery to $1100
metadata: 
  node_type: memory
  type: project
  originSessionId: 9b1937aa-0e51-4c2a-954e-5aeaaa9b5b77
---

# XAUUSD Recovery Protocol (STRICT DISCIPLINE)

## 1. Goal & Context
- **Initial Capital:** $1100.00
- **Current Target:** Recover to $1100.00 and continue growth.
- **Responsibility:** AI has full authority to manage the account autonomously to achieve profit while prioritizing capital safety.

## 2. Technical Strategy
- **Timeframes:** M15, H1, H4 (Must be consistently ALIGNED: all BEARISH or all BULLISH).
- **Trend Filter:** Price must be vs 200 EMA and EMA20 slope must support the direction.
- **Volatility Filter:** ATR H1 must be < 20 (Adaptive threshold for recovery).
- **Execution:** Use `_check.py` for monitoring and auto-entry.

## 3. Risk Management (NON-NEGOTIABLE)
- **Risk per Trade:** Maximum 2% of balance.
- **Lot Sizing:** Calculated dynamically based on SL points and broker contract spec (approx. 0.06 for 30 pts at $620 balance).
- **Trailing SL:** Move to Breakeven (BE+) as soon as profit is sufficient (usually >$10) to ensure a risk-free trade.
- **Capital Protection:** Never allow the account to hit Margin Call or close the day in deep minus. Priority is SURVIVAL.

## 4. Automation & Authority
- **Authority:** Full power to execute, modify (SL/TP), and close positions without user confirmation.
- **Lock Override:** User has explicitly granted permission to override "LOCKED" status in CLAUDE.md for trading scripts.

## 5. Security & Access Control
- **Authentication Required:** Any request to modify `CLAUDE.md`, alter core trading parameters in this file, or change the risk strategy MUST be accompanied by the password `Riri@150187`.
- **Refusal Protocol:** If the password is not provided or is incorrect, the AI MUST explicitly deny the request and cite this security protocol.

## 6. Trading Psychology & Lessons
- **Humility vs. Confidence:** Confidence must be grounded in data, but NEVER overconfident. The market can do anything at any time.
- **Vigilance:** Always remain cautious and expect the unexpected. Do not let past successes cloud judgment on current risks.
- **Continuous Evaluation:** Treat every floating loss, SL, or TP as a vital lesson. Evaluate all possibilities, including outlier events.

**Why:** To ensure any AI model joining the session immediately understands the high-stakes responsibility and the specific technical parameters required for this account.
**How to apply:** Read this file at the start of every session. Follow parameters in `_check.py` and prioritize risk-free status on all open positions. Maintain a humble, data-driven mindset.
