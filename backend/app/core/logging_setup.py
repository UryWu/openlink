"""File logging for the openlink server.

Tees process stdout/stderr into <root_dir>/logs/openlink_<timestamp>.log so
every console line (print, uvicorn, subprocess output) is persisted, and
prunes old log files once the logs directory exceeds a size budget.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]")

LOG_DIR_NAME = "logs"
LOG_PREFIX = "openlink_"
LOG_SUFFIX = ".log"
MAX_TOTAL_BYTES = 50 * 1024 * 1024


class _Tee:
    def __init__(self, terminal, file):
        self._terminal = terminal
        self._file = file

    def write(self, data):
        try:
            self._terminal.write(data)
        except Exception:
            pass
        try:
            self._file.write(_ANSI_RE.sub("", data))
        except Exception:
            pass

    def flush(self):
        for s in (self._terminal, self._file):
            try:
                s.flush()
            except Exception:
                pass

    def isatty(self):
        return getattr(self._terminal, "isatty", lambda: False)()

    def fileno(self):
        return self._terminal.fileno()


def _prune_old_logs(log_dir: Path) -> None:
    files = sorted(
        (p for p in log_dir.glob(f"{LOG_PREFIX}*{LOG_SUFFIX}") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    total = sum(p.stat().st_size for p in files)
    for p in files:
        if total <= MAX_TOTAL_BYTES:
            break
        try:
            size = p.stat().st_size
            p.unlink()
            total -= size
        except OSError:
            pass


def setup_file_logging(root_dir: str) -> str | None:
    """Mirror stdout/stderr into a timestamped log file under root_dir/logs.

    Returns the log file path on success, or None if the directory can't be
    created. Safe to call multiple times — only the first call attaches.
    """
    if getattr(setup_file_logging, "_done", False):
        return getattr(setup_file_logging, "_path", None)

    log_dir = Path(root_dir) / LOG_DIR_NAME
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    _prune_old_logs(log_dir)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{LOG_PREFIX}{ts}{LOG_SUFFIX}"
    try:
        fh = open(log_path, "a", encoding="utf-8", buffering=1)
    except OSError:
        return None

    sys.stdout = _Tee(sys.__stdout__, fh)
    sys.stderr = _Tee(sys.__stderr__, fh)
    setup_file_logging._file = fh

    setup_file_logging._done = True
    setup_file_logging._path = str(log_path)
    return str(log_path)
