from __future__ import annotations
import json
from pathlib import Path
from .config import WORKSPACE

class Memory:
    def __init__(self, filename="memory.json"):
        self.path = Path(WORKSPACE) / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def add(self, role: str, content: str):
        data = self.load()
        data.append({"role": role, "content": content})
        self.path.write_text(json.dumps(data[-100:], ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
