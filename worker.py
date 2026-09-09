import asyncio
import json
import os
from pathlib import Path

import websockets
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("AGENT_SERVER_URL", "ws://127.0.0.1:8765")
SECRET = os.getenv("WORKER_SECRET", "change-this-secret")
ROOT = (Path(__file__).resolve().parent / os.getenv("AGENT_WORKSPACE", "workspace")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)


def safe_path(value: str) -> Path:
    candidate = (ROOT / value).resolve()
    if candidate != ROOT and ROOT not in candidate.parents:
        raise ValueError("Path must stay inside the agent workspace")
    return candidate


async def handle(ws, job: dict):
    rid = job.get("request_id")
    action = job.get("action")
    args = job.get("args") or {}
    try:
        if action == "ping":
            result = "pong"
        elif action == "list_files":
            result = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()]
        elif action == "read_file":
            path = safe_path(str(args.get("path", "")))
            if not path.is_file():
                raise FileNotFoundError(str(path.relative_to(ROOT)))
            if path.stat().st_size > 2_000_000:
                raise ValueError("File is larger than 2 MB")
            result = path.read_text(encoding="utf-8")
        elif action == "write_file":
            path = safe_path(str(args.get("path", "")))
            content = str(args.get("content", ""))
            if len(content.encode("utf-8")) > 2_000_000:
                raise ValueError("File is larger than 2 MB")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result = f"Wrote {path.relative_to(ROOT)}"
        else:
            raise ValueError("Action not enabled in the safe worker")
        await ws.send(json.dumps({"type": "result", "request_id": rid, "ok": True, "result": result}))
    except Exception as exc:
        await ws.send(json.dumps({"type": "result", "request_id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"}))


async def main():
    while True:
        try:
            async with websockets.connect(URL, ping_interval=20, ping_timeout=20) as ws:
                await ws.send(json.dumps({"type": "hello", "secret": SECRET, "platform": os.name, "workspace": str(ROOT)}))
                async for raw in ws:
                    job = json.loads(raw)
                    if job.get("type") == "task":
                        await handle(ws, job)
        except Exception as exc:
            print(f"Worker disconnected: {type(exc).__name__}: {exc}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
