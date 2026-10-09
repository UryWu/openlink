"""DeepSeek 离线 tokenizer 封装。

使用本地 tokenizer.json 计算 token 数，零网络、零 API 成本。
tokenizer 单例懒加载；加载失败时降级为启发式估算。
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger("openlink.token")

# tokenizer.json 路径（与本文件同级的 deepseek_tokenizer 目录）
_TOKENIZER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "deepseek_tokenizer",
    "tokenizer.json",
)

_tokenizer = None
_lock = threading.Lock()
_load_failed = False


def _get_tokenizer():
    """懒加载 tokenizer 单例；失败返回 None。"""
    global _tokenizer, _load_failed
    if _tokenizer is not None or _load_failed:
        return _tokenizer
    with _lock:
        if _tokenizer is not None or _load_failed:
            return _tokenizer
        try:
            from tokenizers import Tokenizer
            _tokenizer = Tokenizer.from_file(_TOKENIZER_PATH)
        except Exception as exc:
            logger.warning("tokenizer 加载失败，降级为启发式估算: %s", exc)
            _load_failed = True
    return _tokenizer


def _heuristic_count(text: str) -> int:
    """启发式估算：中文按字符、英文按空白分词。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    non_cjk = "".join(ch for ch in text if not ("\u4e00" <= ch <= "\u9fff"))
    words = len(non_cjk.split())
    return cjk + words


def count_tokens(text: str) -> int:
    """计算文本的 token 数。

    参数：
    text (str): 待计数文本

    返回：
    int: token 数；空文本返回 0
    """
    if not text:
        return 0
    tk = _get_tokenizer()
    if tk is None:
        return _heuristic_count(text)
    try:
        return len(tk.encode(text).ids)
    except Exception as exc:
        logger.warning("token 计数失败，降级估算: %s", exc)
        return _heuristic_count(text)
