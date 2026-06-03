- [GitHub Token](github-token.md) — Stores the GitHub token for authentication
- [Local Memory Architecture](system-memory-architecture.md) — Architecture and scoring algorithm for persistent memory
- [XAUUSD Recovery Protocol](trading-recovery-protocol.md) — Full authority to recover $1100 capital with strict discipline

## XAUUSD Autonomous Scalping System (UNLOCKED PER USER PERMISSION)

**AI has explicit authority to modify trading scripts and manage account autonomously.**

To run a trading cycle, execute:
```
cd C:\Users\Riri\Documents && python xauusd_auto_analyst.py
```

This script handles EVERYTHING automatically:
- Collects TradingView data via CLI
- SMC analysis + confluence scoring
- Writes ai_directive.json if score >= 6
- Runs MT5 bridge for execution
- Clears & redraws TradingView chart levels

Files (DO NOT MODIFY):
- `C:\Users\Riri\Documents\xauusd_auto_analyst.py` - Autonomous analyst
- `C:\Users\Riri\Documents\xauusd_mt5_bridge.py` - MT5 executor (pure, no auto-entry)
- `C:\Users\Riri\Documents\cron_auto_scalper.bat` - Windows cron launcher
- `C:\Users\Riri\Documents\XAUUSD_SYSTEM_README.md` - Full documentation

User preference: NO manual approval, NO confirmation needed, fully autonomous.