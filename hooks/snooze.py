#!/usr/bin/env python3
"""
snooze.py — temporarily extend today's token quota
Writes a snooze file that adds extra tokens to all limits until midnight.

Set TOKEN_QUOTA_SNOOZE_TOKENS to change the snooze amount (default: 1,000,000).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from quota_store import QuotaStore


def main():
    store = QuotaStore()
    store.write_snooze(store.snooze_tokens)
    print(f"Quota snoozed: +{store.snooze_tokens:,} tokens added to all limits for today.")
    print(f"Expires at midnight. Set TOKEN_QUOTA_SNOOZE_TOKENS to change the amount.")


if __name__ == "__main__":
    main()
