import sys
sys.stdout.reconfigure(encoding="utf-8")

from app.utils.token_count import count_tokens


def test_count_tokens_positive():
    """英文文本应返回正整数 token 数。"""
    n = count_tokens("hello world")
    assert isinstance(n, int)
    assert n > 0


def test_count_tokens_chinese():
    """中文文本应返回正整数 token 数。"""
    n = count_tokens("你好，世界")
    assert n > 0


def test_count_tokens_empty():
    """空文本返回 0。"""
    assert count_tokens("") == 0
