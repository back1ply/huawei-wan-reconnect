"""Detect an ISP quota redirect by probing plain-HTTP sites without following redirects."""

import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROBE_URLS = ("http://example.com/", "http://detectportal.firefox.com/success.txt")
REDIRECT_HINT = "redirection"  # e.g. megaplusredirection.tedata.net


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe(url, timeout=8):
    """Return {"url", "status", "location", "redirected"}; status is None on network error."""
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(url, timeout=timeout) as resp:
            return {"url": url, "status": resp.status, "location": "", "redirected": False}
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "") or ""
        return {
            "url": url,
            "status": e.code,
            "location": loc,
            "redirected": 300 <= e.code < 400 and REDIRECT_HINT in loc.lower(),
        }
    except OSError:
        return {"url": url, "status": None, "location": "", "redirected": False}


def check(urls=PROBE_URLS):
    """Return (state, results). state is 'redirected', 'clear', or 'unknown'."""
    with ThreadPoolExecutor(len(urls)) as pool:
        results = list(pool.map(probe, urls))
    if any(r["redirected"] for r in results):
        return "redirected", results
    if any(r["status"] is not None for r in results):
        return "clear", results
    return "unknown", results
