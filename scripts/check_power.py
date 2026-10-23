"""Verify the Power layer: Meterless Nightshift runtime serving Nemotron.

Usage:
    python scripts/check_power.py            # discovery + one real completion
    python scripts/check_power.py --prompt "你的问题"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    from backend import llm

    print("Nightshift / Nemotron check")
    print("===========================")
    print(f"  Base URL : {os.environ.get('METERLESS_BASE_URL', '(default)')}")
    print()

    discovery = llm.list_models()
    print(f"  [{'PASS' if discovery['status'] == 'ok' else 'FAIL'}]  model discovery: {discovery['message']}")
    if discovery["status"] != "ok":
        print()
        print("Runtime is unreachable. Start Nightshift and retry.")
        return 1

    nemo = [m for m in discovery["models"] if "nemotron" in m.lower()]
    hosted = [m for m in nemo if not m.startswith("local")]
    print(f"  [{'PASS' if hosted else 'FAIL'}]  Nemotron reachable: {len(nemo)} total, {len(hosted)} hosted (evidence for the NVIDIA award)")
    if hosted:
        for m in hosted[:4]:
            print(f"        - {m}")

    prompt = "Reply with exactly one word: ready"
    if "--prompt" in sys.argv:
        idx = sys.argv.index("--prompt")
        if idx + 1 < len(sys.argv):
            prompt = sys.argv[idx + 1]

    result = llm.chat([{"role": "user", "content": prompt}], temperature=0)
    ok = result["status"] == "ok"
    print(f"  [{'PASS' if ok else 'FAIL'}]  real completion: {result['message']}")
    if ok:
        print(f"        served by : {result['model']}")
        print(f"        answer    : {result['content'][:160]}")
        print(f"        usage     : {result['usage']}")

    nemotron_served = "nemotron" in result.get("model", "").lower()
    print(f"  [{'PASS' if nemotron_served else 'WARN'}]  the answering model is a Nemotron: {result.get('model')}")

    print()
    if ok and hosted:
        print("Power layer is ready.")
        return 0
    print("Power layer is not ready; see the FAIL lines above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
