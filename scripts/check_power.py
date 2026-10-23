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

    # Pin one discovered model. Both this script and the app refuse meterless/auto,
    # because auto routing has been observed to land on different models per call.
    pinned = next((m for m in hosted if 'lightning' in m), hosted[0] if hosted else '')
    if not pinned:
        print("  [FAIL]  no hosted Nemotron model to pin; cannot produce award evidence")
        return 1

    prompt = "Reply with exactly one word: ready"
    if "--prompt" in sys.argv:
        idx = sys.argv.index("--prompt")
        if idx + 1 < len(sys.argv):
            prompt = sys.argv[idx + 1]

    # Nightshift has been observed to substitute a different, still-Nemotron model
    # (pinning nemotron-3-nano returned 3.5-lightning). The app's runner treats that
    # as a hard error; this check reports it as a warning, because the NVIDIA award
    # requires Nemotron to be serving, not one specific Nemotron id.
    result = llm.chat([{"role": "user", "content": prompt}], model=pinned, temperature=0)
    served = result.get("model") or ""
    nemotron_served = "nemotron" in served.lower()
    ok = result["status"] == "ok" or (nemotron_served and "instead of" in result["message"])

    if result["status"] == "ok":
        print(f"  [PASS]  real completion: {result['message']}")
        print(f"        served by : {served}")
        print(f"        answer    : {result['content'][:160]}")
        print(f"        usage     : {result['usage']}")
    elif nemotron_served:
        print(f"  [WARN]  real completion: {result['message']}")
        print(f"        Nightshift substituted another Nemotron; rerun for a clean match,")
        print(f"        or accept it and cite the model that actually served.")
    else:
        print(f"  [FAIL]  real completion: {result['message']}")

    print(f"  [{'PASS' if nemotron_served else 'FAIL'}]  the answering model is a Nemotron: {served or '(none)'}")

    print()
    if ok and hosted:
        print("Power layer is ready.")
        return 0
    print("Power layer is not ready; see the FAIL lines above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
