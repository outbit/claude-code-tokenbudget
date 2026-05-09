#!/usr/bin/env python3
"""
track_tokens.py — Stop hook
Reads token usage from the session transcript and appends it to today's ledger.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from quota_store import QuotaStore


def get_last_usage(transcript_path: str) -> dict | None:
    """Read the transcript JSONL and return usage from the last assistant message."""
    try:
        path = Path(transcript_path)
        if not path.exists():
            return None
        lines = path.read_text().splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            entry = json.loads(line)
            usage = entry.get("message", {}).get("usage")
            if usage:
                return usage
    except Exception:
        pass
    return None


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    usage = get_last_usage(transcript_path)
    if not usage:
        sys.exit(0)

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    total = input_tokens + output_tokens + cache_write + cache_read

    if total == 0:
        sys.exit(0)

    store = QuotaStore()
    ledger = store.load_ledger()
    ledger["total_tokens"] += total
    ledger["sessions"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_write_tokens": cache_write,
            "cache_read_tokens": cache_read,
        }
    )
    store.save_ledger(ledger)

    print(f"[token-quota] +{total:,} tokens this turn | today total: {ledger['total_tokens']:,}", file=sys.stderr)
    store.cleanup_old_ledgers()


if __name__ == "__main__":
    main()
