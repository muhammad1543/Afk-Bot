import asyncio, json, os
from pathlib import Path
import websockets
from dotenv import load_dotenv

load_dotenv()
URL=os.getenv('AGENT_SERVER_URL','ws://127.0.0.1:8765/ws/worker')
SECRET=os.getenv('WORKER_SECRET','')
ROOT=Path(os.getenv('AGENT_WORKSPACE','./workspace')).resolve()
ROOT.mkdir(parents=True,exist_ok=True)

async def main():
    while True:
        try:
            async with websockets.connect(URL) as ws:
                await ws.send(json.dumps({'type':'hello','secret':SECRET,'platform':os.name}))
                async for raw in ws:
                    job=json.loads(raw)
                    # Safe starter worker: only filesystem listing/read operations.
                    if job.get('action')=='list_workspace':
                        files=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()]
                        await ws.send(json.dumps({'type':'result','id':job.get('id'),'ok':True,'result':files}))
                    else:
                        await ws.send(json.dumps({'type':'result','id':job.get('id'),'ok':False,'error':'Action not enabled in safe starter worker.'}))
        except Exception:
            await asyncio.sleep(5)

if __name__=='__main__': asyncio.run(main())
