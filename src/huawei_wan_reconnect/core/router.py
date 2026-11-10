"""HTTP session with a Huawei DN8245V web UI (login, page tokens, set.cgi)."""

import base64
import http.cookiejar
import re
import ssl
import urllib.parse
import urllib.request

from huawei_wan_reconnect.core.wan import parse_connections

TOKEN_RE = re.compile(r'(?:id|name)="onttoken"[^>]*value="([0-9a-fA-F]{16,})"')
WAN_PAGE_RE = re.compile(r"html/bbsp/wan/wan\w*\.asp")
HEX_ESCAPE_RE = re.compile(r"\\x([0-9a-fA-F]{2})")
WAN_LIST_PAGE = "html/bbsp/common/wan_list_cache_wan.asp"
DEFAULT_WAN_PAGE = "html/bbsp/wan/wan.asp"


class RouterError(Exception):
    """An expected failure talking to the router, with a one-line message."""


def unescape_js(text):
    """Decode the \\xNN escapes the router uses inside its JavaScript strings."""
    return HEX_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


class Router:
    def __init__(self, host, timeout=20):
        self.host = host
        self.timeout = timeout
        self.wan_page = None
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # the router ships a self-signed LAN certificate
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

    def _url(self, path):
        return f"https://{self.host}/{path.lstrip('/')}"

    def _open(self, req):
        req.add_header("Referer", self._url("index.asp"))
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except OSError as e:
            raise RouterError(f"cannot reach router at {self.host}: {e}") from None

    def get(self, path):
        return self._open(urllib.request.Request(self._url(path)))

    def post(self, path, fields, headers=None):
        req = urllib.request.Request(self._url(path), data=urllib.parse.urlencode(fields).encode())
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        return self._open(req)

    def login(self, user, password):
        rand = self.get("asp/GetRandCount.asp").strip().lstrip("﻿")
        self.post(
            "login.cgi",
            {
                "UserName": user,
                "PassWord": base64.b64encode(password.encode()).decode(),
                "Language": "english",
                "x.X_HW_Token": rand,
            },
            headers={"Cookie": "Cookie=body:Language:english:id=-1"},
        )
        failed = RouterError(
            "login failed: check the password, and close any router page open in a browser "
            "(the router allows one web session)"
        )
        try:
            index = self.get("index.asp")  # a bad login gets 403 here
        except RouterError:
            raise failed from None
        if not TOKEN_RE.search(index):
            raise failed
        m = WAN_PAGE_RE.search(index)
        self.wan_page = m.group(0) if m else DEFAULT_WAN_PAGE
        self._credentials = (user, password)  # kept for relogin(); never printed

    def relogin(self):
        self.login(*self._credentials)

    def token(self):
        m = TOKEN_RE.search(self.get(self.wan_page))
        if not m:
            raise RouterError("session expired: no page token on the WAN page")
        return m.group(1)

    def wan_list(self):
        return unescape_js(self.get(WAN_LIST_PAGE))

    def connections(self):
        conns = parse_connections(self.wan_list())
        if not conns:
            raise RouterError(
                "router returned no WAN list (wrong password or unsupported firmware)"
            )
        return conns

    def set_enable(self, domain, enabled):
        self.post(
            f"set.cgi?x={domain}&RequestFile={self.wan_page}",
            {"x.Enable": "1" if enabled else "0", "x.X_HW_Token": self.token()},
        )
