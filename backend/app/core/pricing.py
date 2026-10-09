"""模型单价配置与费用计算。

配置存 ~/.openlink/pricing.json，结构：
{
  "currency": "CNY",
  "unit": 1000000,
  "platforms": {
    "chat.deepseek.com": { "input": 1.0, "output": 2.0 },
    "chat.qwen.ai": { "input": 0.4, "output": 1.2 }
  }
}
单价单位：货币 / unit tokens（默认每百万 token）。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("openlink.pricing")

_DEFAULT_PRICING: dict[str, Any] = {
    "currency": "CNY",
    "unit": 1_000_000,
    # 参考官方 API 单价（元/百万 token），网页版无峰谷/缓存分档，取固定估值。
    "platforms": {
        # DeepSeek：按 deepseek-flash 高峰价（输入 2 / 输出 8）
        "chat.deepseek.com": {"input": 2.0, "output": 8.0},
        # 通义千问：按 qwen-plus 原价（输入 2 / 输出 8）
        "chat.qwen.ai": {"input": 2.0, "output": 8.0},
    },
}


def _default_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".openlink", "pricing.json")


def load_pricing(path: str | None = None) -> dict[str, Any]:
    """读取单价配置；不存在则写默认并返回默认。"""
    p = path or _default_path()
    if not os.path.isfile(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_PRICING, f, ensure_ascii=False, indent=2)
        return dict(_DEFAULT_PRICING)
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 合并默认（缺字段兜底）
        merged = dict(_DEFAULT_PRICING)
        merged.update(data)
        return merged
    except Exception as exc:
        logger.warning("读取 pricing 失败，用默认: %s", exc)
        return dict(_DEFAULT_PRICING)


def calc_cost(platform: str, input_tokens: int, output_tokens: int, pricing: dict[str, Any] | None = None) -> float:
    """计算费用。

    参数：
    platform: 平台 hostname（如 chat.deepseek.com）
    input_tokens / output_tokens: token 数
    pricing: 单价配置；None 时自动加载

    返回：
    float: 费用（货币单位由配置决定）
    """
    pr = pricing or load_pricing()
    unit = pr.get("unit", 1_000_000) or 1_000_000
    platforms = pr.get("platforms", {})
    price = platforms.get(platform)
    if not price:
        return 0.0
    pi = float(price.get("input", 0) or 0)
    po = float(price.get("output", 0) or 0)
    return (input_tokens / unit) * pi + (output_tokens / unit) * po
