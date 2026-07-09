"""String replacement in files.

Implements 10 replacer strategies in cascade for robust AI-generated string matching.
"""

import math
import os
import re
from pathlib import Path

from app.core.security.sandbox import safe_path, safe_abs_path
from app.tools.base import BaseTool, ToolContext, ToolResult

# Confidence thresholds for the multi-candidate replacer chain
SINGLE_CANDIDATE_THRESHOLD = 0.0
MULTIPLE_CANDIDATES_THRESHOLD = 0.3


# ── Helpers ───────────────────────────────────────────────────────────────

def normalize_line_endings(s: str) -> str:
    return s.replace("\r\n", "\n")


def levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein distance."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    curr = [0] * (len(b) + 1)
    for i, ca in enumerate(a, 1):
        curr[0] = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[-1]


# ── Replacer strategies ───────────────────────────────────────────────────

Replacer = callable  # type: ignore[arg-type]


def simple_replacer(content: str, find: str) -> list[str]:
    """Strategy 1: Exact substring match."""
    return [find]


def line_trimmed_replacer(content: str, find: str) -> list[str]:
    """Strategy 2: Match lines with whitespace trimmed."""
    original_lines = content.split("\n")
    search_lines = find.split("\n")

    # Pop trailing empty line from find (if find ends with \n)
    if search_lines and search_lines[-1] == "":
        search_lines = search_lines[:-1]
    if not search_lines:
        return []

    results: list[str] = []
    for i in range(len(original_lines) - len(search_lines) + 1):
        match = True
        for j in range(len(search_lines)):
            if original_lines[i + j].strip() != search_lines[j].strip():
                match = False
                break
        if not match:
            continue
        # Compute byte offset of the matched block
        match_start = sum(len(original_lines[k]) + 1 for k in range(i))
        match_end = match_start + sum(
            len(original_lines[i + k]) + (1 if k < len(search_lines) - 1 else 0)
            for k in range(len(search_lines))
        )
        results.append(content[match_start:match_end])
    return results


def block_anchor_replacer(content: str, find: str) -> list[str]:
    """Strategy 3: Match by first/last line anchors with Levenshtein similarity."""
    original_lines = content.split("\n")
    search_lines = find.split("\n")

    if len(search_lines) < 3:
        return []
    if search_lines[-1] == "":
        search_lines = search_lines[:-1]
    if len(search_lines) < 3:
        return []

    first_line_search = search_lines[0].strip()
    last_line_search = search_lines[-1].strip()
    search_block_size = len(search_lines)

    # Collect all anchor candidates
    candidates: list[tuple[int, int]] = []
    for i in range(len(original_lines)):
        if original_lines[i].strip() != first_line_search:
            continue
        for j in range(i + 2, len(original_lines)):
            if original_lines[j].strip() == last_line_search:
                candidates.append((i, j))
                break
    if not candidates:
        return []

    def _block_to_substring(start_line: int, end_line: int) -> str:
        start = sum(len(original_lines[k]) + 1 for k in range(start_line))
        end = start + sum(
            len(original_lines[k]) + (1 if k < end_line else 0)
            for k in range(start_line, end_line + 1)
        )
        return content[start:end]

    def _calc_similarity(c: tuple[int, int]) -> float:
        start, end = c
        actual_block_size = end - start + 1
        lines_to_check = min(search_block_size - 2, actual_block_size - 2)
        if lines_to_check <= 0:
            return 1.0

        sim = 0.0
        for j in range(1, min(search_block_size - 1, actual_block_size - 1)):
            orig_line = original_lines[start + j].strip()
            srch_line = search_lines[j].strip()
            max_len = max(len(orig_line), len(srch_line))
            if max_len == 0:
                continue
            dist = levenshtein(orig_line, srch_line)
            sim += (1 - dist / max_len) / lines_to_check
        return sim

    if len(candidates) == 1:
        c = candidates[0]
        if _calc_similarity(c) >= SINGLE_CANDIDATE_THRESHOLD:
            return [_block_to_substring(*c)]
        return []

    # Multiple candidates: pick best
    best_idx, max_sim = -1, -1.0
    for i, c in enumerate(candidates):
        sim = _calc_similarity(c)
        if sim > max_sim:
            max_sim = sim
            best_idx = i

    if max_sim >= MULTIPLE_CANDIDATES_THRESHOLD and best_idx >= 0:
        return [_block_to_substring(*candidates[best_idx])]
    return []


_ws_re = re.compile(r"\s+")


def _normalize_whitespace(s: str) -> str:
    return _ws_re.sub(" ", s.strip())


def whitespace_normalized_replacer(content: str, find: str) -> list[str]:
    """Strategy 4: Collapse all whitespace to single spaces before matching."""
    normalized_find = _normalize_whitespace(find)
    lines = content.split("\n")
    results: list[str] = []

    # Phase 1: single-line matching
    for line in lines:
        norm_line = _normalize_whitespace(line)
        if norm_line == normalized_find:
            results.append(line)
        elif normalized_find in norm_line:
            words = _ws_re.split(find.strip())
            if words:
                pattern = r"\s+".join(re.escape(w) for w in words)
                m = re.search(pattern, line)
                if m:
                    results.append(m.group())

    # Phase 2: multi-line matching (only if find contains newlines)
    find_lines = find.split("\n")
    if len(find_lines) > 1:
        for i in range(len(lines) - len(find_lines) + 1):
            block = "\n".join(lines[i:i + len(find_lines)])
            if _normalize_whitespace(block) == normalized_find:
                results.append(block)

    return results


def _remove_indentation(text: str) -> str:
    """Strip common leading whitespace from all non-empty lines."""
    lines = text.split("\n")
    min_indent = -1
    for line in lines:
        if not line.strip():
            continue
        n = len(line) - len(line.lstrip(" \t"))
        if min_indent < 0 or n < min_indent:
            min_indent = n
    if min_indent <= 0:
        return text
    out: list[str] = []
    for line in lines:
        if not line.strip():
            out.append(line)
        else:
            out.append(line[min_indent:])
    return "\n".join(out)


def indentation_flexible_replacer(content: str, find: str) -> list[str]:
    """Strategy 5: Strip common leading whitespace before matching."""
    normalized_find = _remove_indentation(find)
    content_lines = content.split("\n")
    find_lines = find.split("\n")

    results: list[str] = []
    for i in range(len(content_lines) - len(find_lines) + 1):
        block = "\n".join(content_lines[i:i + len(find_lines)])
        if _remove_indentation(block) == normalized_find:
            results.append(block)
    return results


_escape_re = re.compile(r"\\(n|t|r|'|\"|`|\\|\n|\$)")


def _unescape_string(s: str) -> str:
    """Unescape common escape sequences (\\n, \\t, \\\", etc.)."""
    def _replace(m: re.Match) -> str:
        ch = m.group(1)
        return {
            "n": "\n", "t": "\t", "r": "\r",
            "'": "'", '"': '"', "`": "`",
            "\\": "\\", "\n": "\n", "$": "$",
        }.get(ch, m.group(0))
    return _escape_re.sub(_replace, s)


def escape_normalized_replacer(content: str, find: str) -> list[str]:
    """Strategy 6: Unescape \\n, \\t etc. before matching."""
    unescaped = _unescape_string(find)
    results: list[str] = []

    # Step 1: direct containment
    if unescaped in content:
        results.append(unescaped)

    # Step 2: sliding window
    lines = content.split("\n")
    find_lines = unescaped.split("\n")
    for i in range(len(lines) - len(find_lines) + 1):
        block = "\n".join(lines[i:i + len(find_lines)])
        if _unescape_string(block) == unescaped:
            results.append(block)
    return results


def trimmed_boundary_replacer(content: str, find: str) -> list[str]:
    """Strategy 7: Trim whitespace from both ends before matching."""
    trimmed = find.strip()
    if trimmed == find:
        return []  # no change, skip

    results: list[str] = []
    if trimmed in content:
        results.append(trimmed)

    lines = content.split("\n")
    find_lines = find.split("\n")
    for i in range(len(lines) - len(find_lines) + 1):
        block = "\n".join(lines[i:i + len(find_lines)])
        if block.strip() == trimmed:
            results.append(block)
    return results


def tab_newline_replacer(content: str, find: str) -> list[str]:
    """Strategy 8: Replace \\t with \\n\\t (fix AI model errors)."""
    if "\n" in find:
        return []
    if "\t" not in find:
        return []
    return [find.replace("\t", "\n\t")]


def context_aware_replacer(content: str, find: str) -> list[str]:
    """Strategy 9: Match blocks with >=50% middle-line similarity."""
    find_lines = find.split("\n")
    if len(find_lines) < 3:
        return []
    if find_lines[-1] == "":
        find_lines = find_lines[:-1]
    if len(find_lines) < 3:
        return []

    first_line = find_lines[0].strip()
    last_line = find_lines[-1].strip()
    content_lines = content.split("\n")

    for i in range(len(content_lines)):
        if content_lines[i].strip() != first_line:
            continue
        for j in range(i + 2, len(content_lines)):
            if content_lines[j].strip() != last_line:
                continue
            block_lines = content_lines[i:j + 1]
            if len(block_lines) != len(find_lines):
                break

            matching = 0
            total_non_empty = 0
            for k in range(1, len(block_lines) - 1):
                bl = block_lines[k].strip()
                fl = find_lines[k].strip()
                if bl or fl:
                    total_non_empty += 1
                    if bl == fl:
                        matching += 1

            if total_non_empty == 0 or matching / total_non_empty >= 0.5:
                return ["\n".join(block_lines)]
            break
    return []


def multi_occurrence_replacer(content: str, find: str) -> list[str]:
    """Strategy 10: Find all occurrences via strings.Index loop."""
    results: list[str] = []
    start = 0
    while True:
        idx = content.find(find, start)
        if idx == -1:
            break
        results.append(find)
        start = idx + len(find)
    return results


# ── Main replace dispatcher ──────────────────────────────────────────────

def _replace(content: str, old_string: str, new_string: str, replace_all: bool) -> tuple[str, str | None]:
    """Core replacement logic.

    Returns (new_content, error_string). On success error_string is None.
    """
    if old_string == new_string:
        return "", "No changes to apply: oldString and newString are identical."

    not_found = True

    replacers: list[Replacer] = [
        simple_replacer,
        line_trimmed_replacer,
        block_anchor_replacer,
        whitespace_normalized_replacer,
        indentation_flexible_replacer,
        escape_normalized_replacer,
        trimmed_boundary_replacer,
        tab_newline_replacer,
        context_aware_replacer,
        multi_occurrence_replacer,
    ]

    for replacer_fn in replacers:
        for search in replacer_fn(content, old_string):
            idx = content.find(search)
            if idx == -1:
                continue
            not_found = False
            if replace_all:
                return content.replace(search, new_string), None
            # Single replacement: verify uniqueness
            last_idx = content.rfind(search)
            if idx != last_idx:
                continue  # multiple occurrences, skip this candidate
            return content[:idx] + new_string + content[idx + len(search):], None

    if not_found:
        return "", ("Could not find old_string in the file. It must match exactly, "
                     "including whitespace, indentation, and line endings.")
    return "", "Found multiple matches for old_string. Provide more surrounding context to make the match unique."


# ── Tool class ────────────────────────────────────────────────────────────

class EditTool(BaseTool):
    def __init__(self, config):
        self._config = config

    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return "Replace a string in a file (exact match)"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "path": "string (required) - file path",
            "old_string": "string (required) - text to replace",
            "new_string": "string (required) - replacement text",
            "replace_all": "bool (optional) - replace all occurrences (default false)",
        }

    def validate(self, args: dict) -> str | None:
        p = args.get("path")
        if not isinstance(p, str) or not p.strip():
            return "path is required"
        if not isinstance(args.get("old_string"), str):
            return "old_string is required"
        if not isinstance(args.get("new_string"), str):
            return "new_string is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        raw_path: str = ctx.args["path"]
        old_str: str = ctx.args["old_string"]
        new_str: str = ctx.args["new_string"]
        replace_all: bool = bool(ctx.args.get("replace_all", False))
        root = ctx.config.root_dir

        # Resolve path through sandbox
        try:
            if os.path.isabs(raw_path) or raw_path.startswith("~"):
                abs_path = safe_abs_path(
                    raw_path,
                    allowed_roots=[root, str(Path.home() / ".claude"),
                                   str(Path.home() / ".openlink"),
                                   str(Path.home() / ".agent")],
                )
            else:
                abs_path = safe_path(root, raw_path)
        except ValueError as e:
            return ToolResult(status="error", error=str(e))

        try:
            raw_content = Path(abs_path).read_bytes()
        except OSError as e:
            return ToolResult(status="error", error=str(e))

        content = normalize_line_endings(raw_content.decode("utf-8", errors="replace"))

        replaced, err = _replace(content, old_str, new_str, replace_all)
        if err:
            return ToolResult(status="error", error=err)

        try:
            Path(abs_path).write_text(replaced, encoding="utf-8")
        except OSError as e:
            return ToolResult(status="error", error=str(e))

        return ToolResult(output=f"已替换 '{old_str}' → '{new_str}'")
