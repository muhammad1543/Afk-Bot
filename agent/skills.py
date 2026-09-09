from __future__ import annotations
from pathlib import Path
import re

class Skill:
    def __init__(self, name, description, permissions, path):
        self.name, self.description, self.permissions, self.path = name, description, permissions, path

class SkillRegistry:
    def __init__(self, root="skills"):
        self.root = Path(root)
        self.skills = {}
        self.reload()

    def reload(self):
        self.skills = {}
        if not self.root.exists(): return
        for md in self.root.glob("*/SKILL.md"):
            text = md.read_text(encoding="utf-8", errors="ignore")
            name = md.parent.name
            desc = ""
            m = re.search(r"(?im)^description:\s*(.+)$", text)
            if m: desc = m.group(1).strip()
            perms = []
            m = re.search(r"(?im)^permissions:\s*(.+)$", text)
            if m: perms = [x.strip() for x in m.group(1).split(",") if x.strip()]
            self.skills[name] = Skill(name, desc, perms, str(md))

    def list(self):
        return list(self.skills.values())

    def context(self):
        return "\n".join(f"- {s.name}: {s.description} (permissions: {', '.join(s.permissions) or 'none'})" for s in self.skills.values())
