"""SKILL.md file scanner — mirrors internal/skill/loader.go."""

import os
from pathlib import Path
from typing import Any


def _skill_dirs(root_dir: str) -> list[Path]:
    """Return skill search directories in priority order (first found wins)."""
    home = Path.home()
    root = Path(root_dir)
    candidates = [
        root / ".skills",
        root / ".openlink" / "skills",
        root / ".agent" / "skills",
        root / ".claude" / "skills",
        home / ".openlink" / "skills",
        home / ".agent" / "skills",
        home / ".claude" / "skills",
    ]
    return [d for d in candidates if d.is_dir()]


def _parse_skill_md(path: Path) -> dict[str, Any]:
    """Parse YAML-like frontmatter from a SKILL.md file.

    Mirrors Go's parse() in skill/loader.go.
    """
    result: dict[str, Any] = {
        "name": path.parent.name,
        "description": "",
    }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return result

    if not text.startswith("---"):
        return result

    # Find closing ---
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return result

    frontmatter = text[3:end_idx].strip()
    for line in frontmatter.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key == "name":
                result["name"] = val
            elif key == "description":
                result["description"] = val

    return result


def load_infos(root_dir: str) -> list[dict[str, Any]]:
    """Scan all skill directories and return deduplicated info list.

    Mirrors Go's LoadInfos().
    """
    seen: set[str] = set()
    infos: list[dict[str, Any]] = []

    for skill_dir in _skill_dirs(root_dir):
        # Sort for deterministic ordering
        entries = sorted(skill_dir.iterdir())
        for entry in entries:
            if not entry.is_dir():
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                # Try lowercase
                for f in entry.iterdir():
                    if f.name.lower() == "skill.md":
                        skill_md = f
                        break
                else:
                    continue

            info = _parse_skill_md(skill_md)
            name = info.get("name", entry.name)
            if name in seen:
                continue
            seen.add(name)
            info["dir"] = str(entry.resolve())
            info["location"] = str(skill_md.resolve())
            infos.append(info)

    return infos


def get_skill(root_dir: str, name: str) -> dict[str, Any] | None:
    """Find a skill by name (case-insensitive). Returns None if not found.

    Mirrors Go's Get().
    """
    if "/" in name or "\\" in name or ".." in name:
        return None

    for info in load_infos(root_dir):
        if info.get("name", "").lower() == name.lower():
            return info
    return None


def find_skill(root_dir: str, name: str) -> dict[str, Any] | None:
    """Find a skill file by name, searching both flat files and subdirectories.

    Mirrors Go's FindSkill().
    Returns info dict with 'content', 'dir', 'location' keys, or None.
    """
    root = Path(root_dir)
    skill_dirs_list = _skill_dirs(root_dir)

    for d in skill_dirs_list:
        # Check flat file: dir/<name>.md
        flat = d / f"{name}.md"
        if flat.exists():
            return {
                "name": name,
                "dir": str(d.resolve()),
                "location": str(flat.resolve()),
                "content": flat.read_text(encoding="utf-8"),
            }
        # Check subdirectory: dir/<name>/SKILL.md (case-insensitive)
        subdir = d / name
        if subdir.is_dir():
            for f in subdir.iterdir():
                if f.name.lower() == "skill.md":
                    return {
                        "name": name,
                        "dir": str(subdir.resolve()),
                        "location": str(f.resolve()),
                        "content": f.read_text(encoding="utf-8"),
                    }
    return None
