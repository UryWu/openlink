"""Fetch web page content via HTTP."""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

from app.tools.base import BaseTool, ToolContext, ToolResult
from app.utils.truncate import truncate

_BODY_LIMIT = 1 * 1024 * 1024  # 1 MB
_TIMEOUT = 30  # seconds

_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_html_tag_re = re.compile(r"<[^>]+>")
_multi_space_re = re.compile(r"[ \t]{2,}")
_multi_newline_re = re.compile(r"\n{3,}")


def _strip_html(s: str) -> str:
    s = _html_tag_re.sub(" ", s)
    s = _multi_space_re.sub(" ", s)
    s = _multi_newline_re.sub("\n\n", s)
    return s.strip()


def _is_private(host: str) -> bool:
    """Check if host resolves to a private/internal IP address."""
    try:
        ips = socket.getaddrinfo(host, 80)
    except OSError:
        return False
    for family, _type, _proto, _cname, sockaddr in ips:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            for net in _PRIVATE_NETS:
                if ip in net:
                    return True
        except ValueError:
            continue
    return False


class WebFetchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch web page content via HTTP"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "url": "string (required) - http/https URL to fetch",
            "format": "string (optional) - 'text' (default, strips HTML) or 'html'",
        }

    def validate(self, args: dict) -> str | None:
        raw = args.get("url")
        if not isinstance(raw, str) or not raw.strip():
            return "url is required"
        if not raw.startswith(("http://", "https://")):
            return "only http/https URLs are supported"

        parsed = urlparse(raw)
        host = parsed.hostname or ""
        if _is_private(host):
            return "requests to private/internal addresses are not allowed"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        url: str = ctx.args["url"]
        fmt: str = ctx.args.get("format", "text")

        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                return ToolResult(status="error", error=str(e))

            content = resp.text[:_BODY_LIMIT]

        if fmt != "html":
            content = _strip_html(content)

        truncated, _ = truncate(content)
        return ToolResult(output=truncated)
