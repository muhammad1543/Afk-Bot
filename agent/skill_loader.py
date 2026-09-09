from pathlib import Path


class SkillLoader:
    """Loads human-readable SKILL.md definitions. It never executes downloaded code."""

    def __init__(self, root: Path):
        self.root = root

    def list_definitions(self) -> list[dict[str, str]]:
        result = []
        if not self.root.exists():
            return result
        for path in sorted(self.root.glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            title = path.parent.name
            if lines and lines[0].startswith("#"):
                title = lines[0].lstrip("# ").strip()
            result.append({"name": path.parent.name, "title": title, "definition": text[:4000]})
        return result

    def catalog(self) -> str:
        items = self.list_definitions()
        if not items:
            return "(no SKILL.md definitions found)"
        return "\n\n".join(f"[{x['name']}] {x['definition']}" for x in items)
