"""Run a real local model/tool loop; never substitutes scripted model responses."""
import argparse
import json
from pathlib import Path
from uuid import UUID, uuid4
from backend.agent_runtime import OllamaProvider, ResearchSession
from backend import storage

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--example', choices=['heart', 'breast'], default='heart')
    parser.add_argument('--model', default='qwen3.5:4b')
    parser.add_argument('--run-id', type=UUID)
    args = parser.parse_args()
    folder = storage.ROOT / 'agent-runs' / str(args.run_id or uuid4())
    print(f'Real Agent trace: {folder}', flush=True)
    session = ResearchSession(args.example, folder, OllamaProvider(args.model))
    result = session.run()
    print(json.dumps({'status': result, 'trace': str(folder / 'trace.json')}, ensure_ascii=False))
    if result != 'completed_draft': raise SystemExit(1)

if __name__ == '__main__': main()
