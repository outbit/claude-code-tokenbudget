"""
quota_store.py — shared data access layer for all token-quota hooks.

Encapsulates config parsing, ledger reads/writes, snooze state, and cleanup.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path


class QuotaStore:
    def __init__(self):
        self.ledger_dir = Path(os.environ.get("TOKEN_QUOTA_DIR", Path.home() / ".claude-token-quota"))
        self.daily_limit = int(os.environ.get("TOKEN_QUOTA_DAILY", 1_000_000))
        self.retain_days = int(os.environ.get("TOKEN_QUOTA_RETAIN_DAYS", 31))
        self.snooze_tokens = int(os.environ.get("TOKEN_QUOTA_SNOOZE_TOKENS", 1_000_000))

        _weekly = os.environ.get("TOKEN_QUOTA_WEEKLY")
        self.weekly_limit = int(_weekly) if _weekly else None

        _monthly = os.environ.get("TOKEN_QUOTA_MONTHLY")
        self.monthly_limit = int(_monthly) if _monthly else None

    # ── Ledger paths ──────────────────────────────────────────────────────────

    def ledger_path(self, for_date: date | None = None) -> Path:
        return self.ledger_dir / f"{(for_date or date.today()).isoformat()}.json"

    # ── Token reads ───────────────────────────────────────────────────────────

    def get_today_total(self) -> int:
        p = self.ledger_path()
        if not p.exists():
            return 0
        try:
            return json.loads(p.read_text()).get("total_tokens", 0)
        except Exception:
            return 0

    def get_period_total(self, start: date, end: date) -> int:
        total = 0
        current = start
        while current <= end:
            p = self.ledger_path(current)
            if p.exists():
                try:
                    total += json.loads(p.read_text()).get("total_tokens", 0)
                except Exception:
                    pass
            current += timedelta(days=1)
        return total

    # ── Ledger read/write ─────────────────────────────────────────────────────

    def load_ledger(self) -> dict:
        p = self.ledger_path()
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return {"date": date.today().isoformat(), "total_tokens": 0, "sessions": []}

    def save_ledger(self, ledger: dict):
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path().write_text(json.dumps(ledger, indent=2))

    def cleanup_old_ledgers(self):
        cutoff = date.today() - timedelta(days=self.retain_days)
        for f in self.ledger_dir.glob("????-??-??.json"):
            try:
                if date.fromisoformat(f.stem) < cutoff:
                    f.unlink()
            except ValueError:
                pass

    # ── Snooze ────────────────────────────────────────────────────────────────

    def get_snooze(self) -> int:
        """Return extra tokens from an active snooze, or 0 if none is active."""
        p = self.ledger_dir / "snooze.json"
        if not p.exists():
            return 0
        try:
            data = json.loads(p.read_text())
            if data.get("expires") == date.today().isoformat():
                return int(data.get("extra_tokens", 0))
        except Exception:
            pass
        return 0

    def write_snooze(self, extra_tokens: int):
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        snooze_file = self.ledger_dir / "snooze.json"
        snooze_file.write_text(
            json.dumps(
                {
                    "extra_tokens": extra_tokens,
                    "expires": date.today().isoformat(),
                },
                indent=2,
            )
        )
