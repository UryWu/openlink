"""Load and list skills — mirrors internal/tool/skill.go."""

import os
from pathlib import Path

from app.skills.loader import load_infos, get_skill, find_skill
from app.tools.base import BaseTool, ToolContext, ToolResult


class SkillTool(BaseTool):
    def __init__(self, config):
        self._config = config

    @property
    def name(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        infos = load_infos(self._config.root_dir)
        if not infos:
            return "Load a specialized skill from skills directories"
        parts = ["Load a specialized skill from skills directories\n<available_skills>"]
        for s in infos:
            parts.append(f'\n  <skill><name>{s["name"]}</name><description>{s.get("description", "")}</description><location>file://{s.get("location", "")}</location></skill>')
        parts.append("\n</available_skills>")
        return "".join(parts)

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "skill": "string (optional) - skill name to load; omit to list available skills",
        }

    def validate(self, args: dict) -> str | None:
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        skill_name: str | None = ctx.args.get("skill")
        root = ctx.config.root_dir

        if not skill_name:
            infos = load_infos(root)
            if not infos:
                return ToolResult(output="没有找到可用的 skills")
            names = [s["name"] for s in infos]
            return ToolResult(output="可用 skills: " + ", ".join(names))

        info = get_skill(root, skill_name)
        if info is None:
            return ToolResult(status="error", error=f'skill "{skill_name}" not found')

        try:
            data = Path(info["location"]).read_text(encoding="utf-8")
        except OSError as e:
            return ToolResult(status="error", error=str(e))

        # List sibling files (up to 10, excluding SKILL.md)
        siblings: list[str] = []
        skill_dir = Path(info["dir"])
        if skill_dir.is_dir():
            for entry in sorted(skill_dir.iterdir()):
                if entry.is_file() and entry.name.lower() != "skill.md":
                    siblings.append(str(entry.resolve()))
                    if len(siblings) == 10:
                        break

        parts = [
            f'<skill_content name="{skill_name}">\n',
            f"IMPORTANT: All file paths referenced in this skill must use absolute paths. The skill directory is: {info['dir']}\n",
        ]
        if siblings:
            parts.append("Available files in skill directory (use these absolute paths directly):\n")
            for p in siblings:
                parts.append(f"  - {p}\n")
        parts.append("\n")
        parts.append(data)
        parts.append("\n</skill_content>")

        return ToolResult(output="".join(parts))
