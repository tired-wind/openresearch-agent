"""Run a real local model/tool loop; never substitutes scripted model responses."""
import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path = ROOT / '.env') -> None:
    """scripts/start.sh exports .env; a CLI run must load it for itself."""
    if os.environ.get('OPENRESEARCH_NO_DOTENV') == '1':
        return
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--example', choices=['heart', 'breast'], default='heart')
    parser.add_argument('--provider', choices=['nightshift', 'ollama'], default='ollama',
                        help='default: ollama; nightshift requires explicit selection')
    parser.add_argument('--model', help='model id; defaults per provider')
    parser.add_argument('--no-memory', action='store_true', help='disable H-MEM recall and mining')
    parser.add_argument('--memory-dir', help='H-MEM directory; enables memory explicitly')
    parser.add_argument('--env-file', type=Path, help='explicitly load this local env file (never allowed for web workers)')
    parser.add_argument('--run-id', type=UUID)
    args = parser.parse_args()
    if args.env_file:
        if os.environ.get('OPENRESEARCH_NO_DOTENV') == '1':
            parser.error('Environment-file loading is disabled for this worker.')
        load_env(args.env_file)

    from backend.agent_runtime import NightshiftProvider, OllamaProvider, ResearchSession
    from backend import hmem, storage

    provider_name = args.provider
    if provider_name == 'nightshift':
        provider = NightshiftProvider(args.model)
    else:
        provider = OllamaProvider(args.model or 'qwen3.5:4b')
    memory = hmem.MemoryStore(Path(args.memory_dir)) if args.memory_dir and not args.no_memory else None

    folder = storage.ROOT / 'agent-runs' / str(args.run_id or uuid4())
    print(f'Real Agent trace: {folder}', flush=True)
    print(f'provider={provider_name} model={provider.model} memory={"off" if memory is None else args.memory_dir}', flush=True)
    session = ResearchSession(args.example, folder, provider, memory=memory)
    result = session.run()
    print(json.dumps({'status': result, 'trace': str(folder / 'trace.json')}, ensure_ascii=False))
    if result != 'completed_draft': raise SystemExit(1)

if __name__ == '__main__': main()
