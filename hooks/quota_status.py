#!/usr/bin/env python3
"""
quota_status.py — run manually to check today's token usage
Usage:  python3 quota_status.py
        TOKEN_QUOTA_DAILY=1000000 TOKEN_QUOTA_WEEKLY=5000000 python3 quota_status.py

Set TOKEN_QUOTA_COST_PER_M to a blended dollar cost per 1M tokens to show
estimated spend alongside token counts (e.g. TOKEN_QUOTA_COST_PER_M=5.40).
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

_cost_raw = os.environ.get("TOKEN_QUOTA_COST_PER_M")
COST_PER_M = float(_cost_raw) if _cost_raw else None

RETAIN_DAYS = int(os.environ.get("TOKEN_QUOTA_RETAIN_DAYS", 31))


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


def _cost_str(tokens: int) -> str:
    """Return a formatted cost string, or empty string if cost tracking is off."""
    if COST_PER_M is None:
        return ""
    return f"  (~${tokens / 1_000_000 * COST_PER_M:.2f})"


def _render_bar(used: int, limit: int) -> tuple[str, float, str]:
    pct = (used / limit) * 100 if limit > 0 else 0
    filled = min(30, int(30 * pct / 100))
    bar = "█" * filled + "░" * (30 - filled)
    status = "✅ OK" if pct < 80 else ("⚠️  WARNING" if pct < 100 else "🚫 EXCEEDED")
    return bar, pct, status


def main():
    today = date.today()

    if MONTHLY_LIMIT is not None and RETAIN_DAYS < 31:
        print(f"  ⚠️  WARNING: TOKEN_QUOTA_RETAIN_DAYS={RETAIN_DAYS} is below 31.")
        print(f"  Monthly totals may be incomplete for 31-day months.")
        print(f"  Set TOKEN_QUOTA_RETAIN_DAYS=31 or higher to fix this.")

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
        print(f"  Used:      {used:>12,} tokens{_cost_str(used)}")
        print(f"  Remaining: {remaining:>12,} tokens{_cost_str(remaining)}")
        print(f"  Limit:     {DAILY_LIMIT:>12,} tokens{_cost_str(DAILY_LIMIT)}")
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
        print(f"  Used:      {used_weekly:>12,} tokens{_cost_str(used_weekly)}")
        print(f"  Remaining: {remaining_weekly:>12,} tokens{_cost_str(remaining_weekly)}")
        print(f"  Limit:     {WEEKLY_LIMIT:>12,} tokens{_cost_str(WEEKLY_LIMIT)}")
        print(f"  Status:    {status}")

    if MONTHLY_LIMIT is not None:
        month_start = today.replace(day=1)
        used_monthly = get_period_total(month_start, today)
        remaining_monthly = max(0, MONTHLY_LIMIT - used_monthly)
        bar, pct, status = _render_bar(used_monthly, MONTHLY_LIMIT)

        print(f"\n  Monthly ({today.strftime('%B %Y')})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used_monthly:>12,} tokens{_cost_str(used_monthly)}")
        print(f"  Remaining: {remaining_monthly:>12,} tokens{_cost_str(remaining_monthly)}")
        print(f"  Limit:     {MONTHLY_LIMIT:>12,} tokens{_cost_str(MONTHLY_LIMIT)}")
        print(f"  Status:    {status}")

    print(f"\n{'─'*50}\n")


if __name__ == "__main__":
    main()
