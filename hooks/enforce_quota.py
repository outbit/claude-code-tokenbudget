#!/usr/bin/env python3
"""
enforce_quota.py — UserPromptSubmit hook
Reads token ledgers and blocks the prompt if any quota is exceeded.

Set limits via environment variables:
  TOKEN_QUOTA_DAILY=1000000    (default: 1,000,000 tokens)
  TOKEN_QUOTA_WEEKLY=5000000   (optional; rolling 7-day window)
  TOKEN_QUOTA_MONTHLY=15000000 (optional; current calendar month)
  TOKEN_QUOTA_DIR=~/.claude-token-quota  (default ledger location)
  TOKEN_QUOTA_WARN_CRITICAL=95 (default: warn loudly at 95% of daily limit)
  TOKEN_QUOTA_WARN=85          (default: warn quietly at 85% of daily limit)
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

LEDGER_DIR = Path(os.environ.get("TOKEN_QUOTA_DIR", Path.home() / ".claude-token-quota"))
DAILY_LIMIT = int(os.environ.get("TOKEN_QUOTA_DAILY", 1_000_000))
WARN_CRITICAL = int(os.environ.get("TOKEN_QUOTA_WARN_CRITICAL", 95))
WARN = int(os.environ.get("TOKEN_QUOTA_WARN", 85))

_weekly_raw = os.environ.get("TOKEN_QUOTA_WEEKLY")
WEEKLY_LIMIT = int(_weekly_raw) if _weekly_raw else None

_monthly_raw = os.environ.get("TOKEN_QUOTA_MONTHLY")
MONTHLY_LIMIT = int(_monthly_raw) if _monthly_raw else None


def get_today_total() -> int:
    p = LEDGER_DIR / f"{date.today().isoformat()}.json"
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text())
        return data.get("total_tokens", 0)
    except Exception:
        return 0


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


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass

    today = date.today()
    used_daily = get_today_total()
    pct_daily = (used_daily / DAILY_LIMIT) * 100 if DAILY_LIMIT > 0 else 0

    if used_daily >= DAILY_LIMIT:
        result = {
            "decision": "block",
            "reason": (
                f"Daily token quota exceeded.\n"
                f"Used:  {used_daily:,} / {DAILY_LIMIT:,} tokens ({pct_daily:.1f}%)\n"
                f"Quota resets at midnight. Edit TOKEN_QUOTA_DAILY to change the limit."
            )
        }
        print(json.dumps(result))
        sys.exit(0)

    if WEEKLY_LIMIT is not None:
        week_start = today - timedelta(days=6)
        used_weekly = get_period_total(week_start, today)
        if used_weekly >= WEEKLY_LIMIT:
            pct = (used_weekly / WEEKLY_LIMIT) * 100
            result = {
                "decision": "block",
                "reason": (
                    f"Weekly token quota exceeded (rolling 7-day window).\n"
                    f"Used:  {used_weekly:,} / {WEEKLY_LIMIT:,} tokens ({pct:.1f}%)\n"
                    f"Edit TOKEN_QUOTA_WEEKLY to change the limit."
                )
            }
            print(json.dumps(result))
            sys.exit(0)

    if MONTHLY_LIMIT is not None:
        month_start = today.replace(day=1)
        used_monthly = get_period_total(month_start, today)
        if used_monthly >= MONTHLY_LIMIT:
            pct = (used_monthly / MONTHLY_LIMIT) * 100
            result = {
                "decision": "block",
                "reason": (
                    f"Monthly token quota exceeded.\n"
                    f"Used:  {used_monthly:,} / {MONTHLY_LIMIT:,} tokens ({pct:.1f}%)\n"
                    f"Quota resets on the 1st. Edit TOKEN_QUOTA_MONTHLY to change the limit."
                )
            }
            print(json.dumps(result))
            sys.exit(0)

    remaining = DAILY_LIMIT - used_daily
    if pct_daily >= WARN_CRITICAL:
        warning = f"Token quota at {pct_daily:.1f}% ({used_daily:,} / {DAILY_LIMIT:,}). Nearly exhausted."
        result = {"decision": "allow", "reason": warning}
        print(json.dumps(result))
    elif pct_daily >= WARN:
        print(f"[token-quota] {pct_daily:.1f}% of daily quota used ({remaining:,} tokens remaining)", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
