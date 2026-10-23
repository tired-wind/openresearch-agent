"""Verify the local Zetaris instance over its direct REST API.

Read-only: sends SELECT / SHOW statements only. Credentials come from .env.

Usage:
    python scripts/check_zetaris.py            # run the standard checks
    python scripts/check_zetaris.py --raw      # also dump the raw response body
    python scripts/check_zetaris.py "SELECT 1 AS one"
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader so this script needs no third-party dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        # Real environment variables win over the file.
        os.environ.setdefault(key, value)


def settings() -> tuple[str, str, str]:
    rest = os.environ.get("ZETARIS_REST_URL", "").rstrip("/")
    org = os.environ.get("ZETARIS_ORG_ID", "")
    key = os.environ.get("ZETARIS_API_KEY", "")
    missing = [n for n, v in (("ZETARIS_REST_URL", rest), ("ZETARIS_ORG_ID", org), ("ZETARIS_API_KEY", key)) if not v]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    return rest, org, key


def run_sql(sql: str, limit: int = 100, timeout: float = 120.0) -> dict[str, Any]:
    """Send one statement to POST /sql-editor/sqls/run and return the parsed body."""
    rest, org, key = settings()
    payload = json.dumps(
        {"queryId": str(uuid4()), "sql": sql, "source": "SqlEditor", "limit": limit}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{rest}/sql-editor/sqls/run",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "X-Org-ID": org,
            "X-Request-ID": str(uuid4()),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def rows_of(body: dict[str, Any]) -> list[list[Any]]:
    data = body.get("data")
    return data if isinstance(data, list) else []


def check(name: str, sql: str, expect: str | None = None, raw: bool = False) -> bool:
    try:
        body = run_sql(sql)
    except urllib.error.HTTPError as exc:  # pragma: no cover - diagnostics only
        detail = exc.read().decode("utf-8", "replace")[:300]
        print(f"  FAIL  {name}\n        HTTP {exc.code}: {detail}")
        return False
    except Exception as exc:  # pragma: no cover
        print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}")
        return False

    rows = rows_of(body)
    first = rows[0][0] if rows and rows[0] else None
    if expect is not None and str(first) != expect:
        print(f"  FAIL  {name} -> got {first!r}, expected {expect!r}")
        return False

    preview = f"rows={len(rows)}"
    if rows:
        preview += f" first_row={rows[0]!r}"
    print(f"  PASS  {name}  ({preview})")
    if raw:
        print(json.dumps(body, ensure_ascii=False, indent=2)[:1200])
    return True


def main() -> int:
    load_env()
    rest, org, _ = settings()
    print("Zetaris connection check")
    print("========================")
    print(f"  REST base : {rest}")
    print(f"  Org ID    : {org}")
    print()

    raw = "--raw" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        ok = check("custom statement", args[0], raw=raw)
        print()
        print("All checks passed." if ok else "The statement failed.")
        return 0 if ok else 1

    results = [
        check("SELECT 1", "SELECT 1 AS one", expect="1", raw=raw),
        check("SHOW LIGHTNING DATABASES", "SHOW LIGHTNING DATABASES", raw=raw),
        check("SHOW DATASOURCES", "SHOW DATASOURCES", raw=raw),
    ]

    print()
    if all(results):
        print(f"All {len(results)} checks passed.")
        return 0
    print(f"{results.count(False)} of {len(results)} checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
