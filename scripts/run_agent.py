"""Run a real local model/tool loop; never substitutes scripted model responses."""
import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path = ROOT / '.env') -> None:
    """scripts/start.sh exports .env; a CLI run must load it for itself."""
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

from backend.agent_runtime import NightshiftProvider, OllamaProvider, ResearchSession  # noqa: E402
from backend import hmem, storage  # noqa: E402

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--example', choices=['heart', 'breast'], default='heart')
    parser.add_argument('--provider', choices=['nightshift', 'ollama'],
                        help='default: nightshift when METERLESS_RUNTIME_TOKEN is set, else ollama')
    parser.add_argument('--model', help='model id; defaults per provider')
    parser.add_argument('--no-memory', action='store_true', help='disable H-MEM recall and mining')
    parser.add_argument('--memory-dir', default=str(storage.ROOT / 'hmem'))
    parser.add_argument('--run-id', type=UUID)
    args = parser.parse_args()

    provider_name = args.provider or ('nightshift' if os.environ.get('METERLESS_RUNTIME_TOKEN') else 'ollama')
    if provider_name == 'nightshift':
        provider = NightshiftProvider(args.model)
    else:
        provider = OllamaProvider(args.model or 'qwen3.5:4b')
    memory = None if args.no_memory else hmem.MemoryStore(Path(args.memory_dir))

    folder = storage.ROOT / 'agent-runs' / str(args.run_id or uuid4())
    print(f'Real Agent trace: {folder}', flush=True)
    print(f'provider={provider_name} model={provider.model} memory={"off" if memory is None else args.memory_dir}', flush=True)
    session = ResearchSession(args.example, folder, provider, memory=memory)
    result = session.run()
    print(json.dumps({'status': result, 'trace': str(folder / 'trace.json')}, ensure_ascii=False))
    if result != 'completed_draft': raise SystemExit(1)

if __name__ == '__main__': main()
