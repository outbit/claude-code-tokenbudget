#!/usr/bin/env python3
"""
quota_status.py — run manually to check today's token usage
Usage:  python3 quota_status.py
        TOKEN_QUOTA_DAILY=1000000 TOKEN_QUOTA_WEEKLY=5000000 python3 quota_status.py
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

LEDGER_DIR = Path(os.environ.get("TOKEN_QUOTA_DIR", Path.home() / ".claude-token-quota"))
DAILY_LIMIT = int(os.environ.get("TOKEN_QUOTA_DAILY", 1_000_000))

_weekly_raw = os.environ.get("TOKEN_QUOTA_WEEKLY")
WEEKLY_LIMIT = int(_weekly_raw) if _weekly_raw else None

_monthly_raw = os.environ.get("TOKEN_QUOTA_MONTHLY")
MONTHLY_LIMIT = int(_monthly_raw) if _monthly_raw else None


def get_period_total(start: date, end: date) -> int:
    total = 0
    current = start
    while current <= end:
        p = LEDGER_DIR / f"{current.isoformat()}.json"
        if p.exists():
            try:
                data = json.loads(p.read_text())
                total += data.get("total_tokens", 0)
            except Exception:
                pass
        current += timedelta(days=1)
    return total


def _render_bar(used: int, limit: int) -> tuple[str, float, str]:
    pct = (used / limit) * 100 if limit > 0 else 0
    filled = min(30, int(30 * pct / 100))
    bar = "█" * filled + "░" * (30 - filled)
    status = "✅ OK" if pct < 80 else ("⚠️  WARNING" if pct < 100 else "🚫 EXCEEDED")
    return bar, pct, status


def main():
    today = date.today()

    print(f"\n{'─'*50}")
    print(f"  Claude Code Token Quota — {today.isoformat()}")
    print(f"{'─'*50}")

    ledger_file = LEDGER_DIR / f"{today.isoformat()}.json"
    if not ledger_file.exists():
        print(f"  No usage recorded today ({today.isoformat()}).")
        print(f"  Daily limit: {DAILY_LIMIT:,} tokens")
        sessions = []
    else:
        data = json.loads(ledger_file.read_text())
        used = data.get("total_tokens", 0)
        remaining = max(0, DAILY_LIMIT - used)
        sessions = data.get("sessions", [])
        bar, pct, status = _render_bar(used, DAILY_LIMIT)

        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used:>12,} tokens")
        print(f"  Remaining: {remaining:>12,} tokens")
        print(f"  Limit:     {DAILY_LIMIT:>12,} tokens")
        print(f"  Status:    {status}")
        print(f"  Turns:     {len(sessions)}")
        if sessions:
            print(f"  Last turn: {sessions[-1]['timestamp']}")

    if WEEKLY_LIMIT is not None:
        week_start = today - timedelta(days=6)
        used_weekly = get_period_total(week_start, today)
        remaining_weekly = max(0, WEEKLY_LIMIT - used_weekly)
        bar, pct, status = _render_bar(used_weekly, WEEKLY_LIMIT)

        print(f"\n  Weekly (rolling 7-day: {week_start.isoformat()} – {today.isoformat()})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used_weekly:>12,} tokens")
        print(f"  Remaining: {remaining_weekly:>12,} tokens")
        print(f"  Limit:     {WEEKLY_LIMIT:>12,} tokens")
        print(f"  Status:    {status}")

    if MONTHLY_LIMIT is not None:
        month_start = today.replace(day=1)
        used_monthly = get_period_total(month_start, today)
        remaining_monthly = max(0, MONTHLY_LIMIT - used_monthly)
        bar, pct, status = _render_bar(used_monthly, MONTHLY_LIMIT)

        print(f"\n  Monthly ({today.strftime('%B %Y')})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used_monthly:>12,} tokens")
        print(f"  Remaining: {remaining_monthly:>12,} tokens")
        print(f"  Limit:     {MONTHLY_LIMIT:>12,} tokens")
        print(f"  Status:    {status}")

    print(f"\n{'─'*50}\n")


if __name__ == "__main__":
    main()
