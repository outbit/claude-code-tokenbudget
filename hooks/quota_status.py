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
import sys

sys.path.insert(0, str(Path(__file__).parent))
from quota_store import QuotaStore

_cost_raw = os.environ.get("TOKEN_QUOTA_COST_PER_M")
COST_PER_M = float(_cost_raw) if _cost_raw else None


def _cost_str(tokens: int) -> str:
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
    store = QuotaStore()
    today = date.today()

    if store.monthly_limit is not None and store.retain_days < 31:
        print(f"  ⚠️  WARNING: TOKEN_QUOTA_RETAIN_DAYS={store.retain_days} is below 31.")
        print(f"  Monthly totals may be incomplete for 31-day months.")
        print(f"  Set TOKEN_QUOTA_RETAIN_DAYS=31 or higher to fix this.")

    print(f"\n{'─'*50}")
    print(f"  Claude Code Token Quota — {today.isoformat()}")
    print(f"{'─'*50}")

    snooze = store.get_snooze()

    ledger_file = store.ledger_path()
    if not ledger_file.exists():
        print(f"  No usage recorded today ({today.isoformat()}).")
        print(f"  Daily limit: {store.daily_limit:,} tokens")
        sessions = []
    else:
        data = json.loads(ledger_file.read_text())
        used = data.get("total_tokens", 0)
        effective_daily = store.daily_limit + snooze
        remaining = max(0, effective_daily - used)
        sessions = data.get("sessions", [])
        bar, pct, status = _render_bar(used, effective_daily)

        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used:>12,} tokens{_cost_str(used)}")
        print(f"  Remaining: {remaining:>12,} tokens{_cost_str(remaining)}")
        print(f"  Limit:     {store.daily_limit:>12,} tokens{_cost_str(store.daily_limit)}")
        if snooze:
            print(f"  Snooze:    {snooze:>12,} tokens  (expires midnight)")
        print(f"  Status:    {status}")
        print(f"  Turns:     {len(sessions)}")
        if sessions:
            print(f"  Last turn: {sessions[-1]['timestamp']}")

    if store.weekly_limit is not None:
        week_start = today - timedelta(days=6)
        used_weekly = store.get_period_total(week_start, today)
        effective_weekly = store.weekly_limit + snooze
        remaining_weekly = max(0, effective_weekly - used_weekly)
        bar, pct, status = _render_bar(used_weekly, effective_weekly)

        print(f"\n  Weekly (rolling 7-day: {week_start.isoformat()} – {today.isoformat()})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used_weekly:>12,} tokens{_cost_str(used_weekly)}")
        print(f"  Remaining: {remaining_weekly:>12,} tokens{_cost_str(remaining_weekly)}")
        print(f"  Limit:     {store.weekly_limit:>12,} tokens{_cost_str(store.weekly_limit)}")
        if snooze:
            print(f"  Snooze:    {snooze:>12,} tokens  (expires midnight)")
        print(f"  Status:    {status}")

    if store.monthly_limit is not None:
        month_start = today.replace(day=1)
        used_monthly = store.get_period_total(month_start, today)
        effective_monthly = store.monthly_limit + snooze
        remaining_monthly = max(0, effective_monthly - used_monthly)
        bar, pct, status = _render_bar(used_monthly, effective_monthly)

        print(f"\n  Monthly ({today.strftime('%B %Y')})")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Used:      {used_monthly:>12,} tokens{_cost_str(used_monthly)}")
        print(f"  Remaining: {remaining_monthly:>12,} tokens{_cost_str(remaining_monthly)}")
        print(f"  Limit:     {store.monthly_limit:>12,} tokens{_cost_str(store.monthly_limit)}")
        if snooze:
            print(f"  Snooze:    {snooze:>12,} tokens  (expires midnight)")
        print(f"  Status:    {status}")

    print(f"\n{'─'*50}\n")


if __name__ == "__main__":
    main()
