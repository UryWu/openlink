"""Sandbox path validation and dangerous-command filtering.

  - SafePath:        relative path resolved against rootDir, must stay inside
  - SafeAbsPath:     absolute (or ~) path must be inside one of allowedRoots
  - IsDangerousCommand: blocks rm -rf / mkfs / sudo etc.
"""

import os
import re
from pathlib import Path
from typing import Sequence

# Multi-word patterns matched as substrings (case-insensitive)
_DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -fr",
    "> /dev/",
    "chmod 777",
    "kill -9",
]

# Single-word commands matched at word boundaries (case-insensitive)
_DANGEROUS_WORDS = [
    "mkfs",
    "format",
    "nc",
    "netcat",
    "sudo",
    "reboot",
    "shutdown",
]


def _resolve(path_str: str) -> str:
    """Resolve symlinks; fall back to absolute path if file doesn't exist yet."""
    try:
        return os.path.realpath(path_str)
    except OSError:
        return os.path.abspath(path_str)


def safe_path(root_dir: str, target_path: str) -> str:
    """Validate target_path (relative) stays inside root_dir.

    Raises ValueError if the resolved path is outside the sandbox.
    Returns the resolved absolute path on success.
    """
    abs_root = _resolve(root_dir)
    joined = os.path.join(abs_root, target_path)
    abs_target = _resolve(joined)

    sep = os.sep
    if not (abs_target.startswith(abs_root + sep) or abs_target == abs_root):
        msg = f"path outside sandbox: {abs_target} not under {abs_root}"
        raise ValueError(msg)
    return abs_target


def safe_abs_path(target_path: str, allowed_roots: Sequence[str]) -> str:
    """Validate an absolute (or ~-prefixed) path against one or more allowed roots.

    Raises ValueError if the path doesn't fall under any allowed root.
    Returns the resolved absolute path on success.
    """
    expanded = os.path.expanduser(target_path)
    if not os.path.isabs(expanded):
        raise ValueError(f"not an absolute path: {target_path}")

    abs_target = _resolve(expanded)

    for root in allowed_roots:
        abs_root = _resolve(root)
        sep = os.sep
        if abs_target.startswith(abs_root + sep) or abs_target == abs_root:
            return abs_target

    raise ValueError(f"path outside sandbox: {abs_target}")


def is_dangerous_command(cmd: str) -> bool:
    """Check whether a shell command is dangerous to execute.

    Uses word-boundary matching so patterns like 'rm' don't trigger on
    substrings (e.g. 'gorm', 'farm').
    """
    lower = cmd.lower()

    # Multi-word patterns: direct substring match
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in lower:
            return True

    # Single-word commands: require word boundaries
    def is_separator(ch: str) -> bool:
        return ch in ' \t\n;|&()\'"`<>'

    for word in _DANGEROUS_WORDS:
        idx = 0
        while True:
            pos = lower.find(word, idx)
            if pos < 0:
                break
            before_sep = pos == 0 or is_separator(lower[pos - 1])
            after_sep = (pos + len(word) >= len(lower)) or is_separator(lower[pos + len(word)])
            if before_sep and after_sep:
                return True
            idx = pos + 1

    return False
