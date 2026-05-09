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
  TOKEN_QUOTA_COST_PER_M=5.40  (optional; blended cost per 1M tokens for dollar estimates)
  TOKEN_QUOTA_SNOOZE_TOKENS=1000000 (tokens added when snoozed; default 1,000,000)
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from quota_store import QuotaStore

WARN_CRITICAL = int(os.environ.get("TOKEN_QUOTA_WARN_CRITICAL", 95))
WARN = int(os.environ.get("TOKEN_QUOTA_WARN", 85))


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass

    store = QuotaStore()
    today = date.today()
    snooze = store.get_snooze()

    used_daily = store.get_today_total()
    effective_daily = store.daily_limit + snooze
    pct_daily = (used_daily / effective_daily) * 100 if effective_daily > 0 else 0

    if used_daily >= effective_daily:
        result = {
            "decision": "block",
            "reason": (
                f"Daily token quota exceeded.\n"
                f"Used:  {used_daily:,} / {effective_daily:,} tokens ({pct_daily:.1f}%)\n"
                f"Quota resets at midnight. Edit TOKEN_QUOTA_DAILY to change the limit."
            )
        }
        print(json.dumps(result))
        sys.exit(0)

    if store.weekly_limit is not None:
        week_start = today - timedelta(days=6)
        used_weekly = store.get_period_total(week_start, today)
        effective_weekly = store.weekly_limit + snooze
        if used_weekly >= effective_weekly:
            pct = (used_weekly / effective_weekly) * 100
            result = {
                "decision": "block",
                "reason": (
                    f"Weekly token quota exceeded (rolling 7-day window).\n"
                    f"Used:  {used_weekly:,} / {effective_weekly:,} tokens ({pct:.1f}%)\n"
                    f"Edit TOKEN_QUOTA_WEEKLY to change the limit."
                )
            }
            print(json.dumps(result))
            sys.exit(0)

    if store.monthly_limit is not None:
        month_start = today.replace(day=1)
        used_monthly = store.get_period_total(month_start, today)
        effective_monthly = store.monthly_limit + snooze
        if used_monthly >= effective_monthly:
            pct = (used_monthly / effective_monthly) * 100
            result = {
                "decision": "block",
                "reason": (
                    f"Monthly token quota exceeded.\n"
                    f"Used:  {used_monthly:,} / {effective_monthly:,} tokens ({pct:.1f}%)\n"
                    f"Quota resets on the 1st. Edit TOKEN_QUOTA_MONTHLY to change the limit."
                )
            }
            print(json.dumps(result))
            sys.exit(0)

    remaining = effective_daily - used_daily
    if pct_daily >= WARN_CRITICAL:
        warning = f"Token quota at {pct_daily:.1f}% ({used_daily:,} / {effective_daily:,}). Nearly exhausted."
        result = {"decision": "allow", "reason": warning}
        print(json.dumps(result))
    elif pct_daily >= WARN:
        print(f"[token-quota] {pct_daily:.1f}% of daily quota used ({remaining:,} tokens remaining)", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
