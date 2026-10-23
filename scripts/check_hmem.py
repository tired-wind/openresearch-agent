"""Prove the H-MEM feature: a later session starts from what an earlier one proved.

Runs entirely offline against a temporary store, so it is evidence for the BUILD
rule ("your agent remembers information from an earlier session and uses it on a
later task") without needing a model call.

Usage:
    python scripts/check_hmem.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import hmem  # noqa: E402


def rule(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def main() -> int:
    folder = Path(tempfile.mkdtemp(prefix="hmem-demo-"))
    print(f"H-MEM offline mechanics check (illustrative metrics and placeholder PMID; not a scientific/live-model run). Store: {folder}")

    # --- Session 1: a finished investigation is mined into long-term memory ---
    rule("第一会话：完成一次研究调查，把可复用事实写入记忆")
    store = hmem.MemoryStore(folder)
    report = {
        "question": "这些特征与心脏病是否相关？",
        "computed_metrics": {"balanced_accuracy": 0.6423},
        "selected_computed_factors": [{"feature": "thalach"}, {"feature": "cp"}],
        "references": [{"pmid": "12345678"}],
    }
    memory = hmem.mine_report(store, report, domain="research", run_id="run-heart-001")
    print(f"  写入: {memory.content[:90]}...")
    print(f"  layer={memory.layer} type={memory.type} confidence={memory.confidence}")
    print(f"  provenance={memory.provenance}")

    # A verified-artifact memory must never lack a source.
    try:
        store.add("没有出处的说法", source="")
        print("  [FAIL] 无来源记忆未被拒绝")
        return 1
    except ValueError as exc:
        print(f"  [PASS] 无来源记忆被拒绝: {exc}")

    # --- Session 2: a new, separately loaded store recalls it ---
    rule("第二会话：重新从磁盘加载记忆库，检索并注入上下文")
    reloaded = hmem.MemoryStore(folder)
    print(f"  重新加载到 {len(reloaded.all())} 条记忆（证明跨会话持久化）")
    result = hmem.retrieve(reloaded, "这些特征与心脏病是否相关？")
    print(f"  strategy={result['strategy']} threshold={result['threshold']} 命中={len(result['memories'])}")
    for row in result["memories"]:
        print(f"    - score={row['score']} reason={row['retrievalReason']}")
    if not result["context"]:
        print("  [FAIL] 第二会话没有召回任何上下文")
        return 1
    print("  [PASS] 注入给模型的上下文：")
    for line in result["context"].splitlines():
        print(f"    | {line}")

    # --- Feedback closes the loop ---
    rule("信任反馈：用户标记后，置信度与未来排序一起变化")
    target = result["memories"][0]["id"]
    before = reloaded.get(target).confidence
    reloaded.feedback(target, "wrong")
    after = reloaded.get(target).confidence
    print(f"  置信度 {before} -> {after}，标签 {reloaded.get(target).tags}")
    if not after < before:
        print("  [FAIL] 反馈没有降低置信度")
        return 1
    print(f"  [PASS] 账本动作统计: {reloaded.ledger.stats()}")

    # --- An unrelated question must stay empty ---
    rule("负向对照：无关问题不应召回")
    empty = hmem.retrieve(reloaded, "量子色动力学中的格点间距")
    print(f"  命中={len(empty['memories'])} context={'空' if not empty['context'] else '非空'}")
    if empty["memories"]:
        print("  [FAIL] 无关问题召回了记忆")
        return 1
    print("  [PASS] 无关问题零命中")

    print("\nH-MEM feature is ready: cross-session recall, provenance, and audit all work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
