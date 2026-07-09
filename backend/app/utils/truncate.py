"""Output truncation."""

import os
from datetime import datetime
from pathlib import Path

MAX_LINES = 2000
MAX_BYTES = 50 * 1024  # 50 KB
TOOL_OUTPUT_DIR = Path.home() / ".openlink" / "tool-output"


def truncate(output: str) -> tuple[str, bool]:
    """Truncate output to MAX_LINES / MAX_BYTES.

    Returns (truncated_text, was_truncated).
    If truncated, the full output is saved to ~/.openlink/tool-output/<timestamp>
    and a note about the spill file is appended.
    """
    lines = output.splitlines(keepends=True)
    if len(lines) <= MAX_LINES and len(output.encode("utf-8")) <= MAX_BYTES:
        return output, False

    # Build truncated version: limit lines first, then bytes
    truncated_lines = lines[:MAX_LINES]
    truncated = "".join(truncated_lines)

    # Enforce byte limit on the line-truncated result
    encoded = truncated.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        truncated = encoded[:MAX_BYTES].decode("utf-8", errors="replace")

    # Spill full output to file
    TOOL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    spill_path = TOOL_OUTPUT_DIR / f"tool_output_{ts}.txt"
    spill_path.write_text(output, encoding="utf-8")

    next_offset = len(truncated_lines) + 1
    hint = (
        f"\n[输出已截断，仅显示前 {MAX_LINES} 行/{MAX_BYTES // 1024}KB]\n"
        f"[完整输出已保存至: {spill_path}]\n"
        f"[可使用 read_file 工具从偏移量 {next_offset} 继续读取]"
    )
    return truncated + hint, True
