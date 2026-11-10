"""Parse the router's WAN list and pick the connection that carries internet traffic."""

import ipaddress
import re
from dataclasses import asdict, dataclass

RECORD_RE = re.compile(r'new (WanPPP|WanIP)\("(InternetGatewayDevice\.WANDevice\.[^"]+)"(.*?)\)')
FIELD_RE = re.compile(r'"([^"]*)"')

# Field positions after the domain; the same in WanPPP and WanIP records.
STATUS, NAME, ENABLE, MODE = 4, 7, 8, 12


@dataclass
class Connection:
    name: str
    domain: str
    kind: str  # "PPPoE" or "IP"
    enabled: bool
    status: str
    mode: str
    ipv4: str
    uptime: int | None

    @property
    def is_active(self):
        return self.status == "Connected" and self.mode == "IP_Routed" and bool(self.ipv4)

    def to_dict(self):
        return asdict(self) | {"active": self.is_active}


def _first_ipv4(fields):
    """The connection's own IPv4: the first address-shaped field (gateway and DNS come later).
    0.0.0.0 means no address."""
    for f in fields:
        try:
            ip = ipaddress.IPv4Address(f)
        except ValueError:
            continue
        return "" if ip.is_unspecified else f
    return ""


def _uptime(fields):
    if "DetectBidirectionally" in fields:
        i = fields.index("DetectBidirectionally") + 1
        if i < len(fields) and fields[i].isdigit():
            return int(fields[i])
    return None


def parse_connections(text):
    conns = []
    for kind, domain, rest in RECORD_RE.findall(text):
        f = FIELD_RE.findall(rest)
        if len(f) <= MODE:
            continue
        conns.append(
            Connection(
                name=f[NAME] or domain,
                domain=domain,
                kind="PPPoE" if kind == "WanPPP" else "IP",
                enabled=f[ENABLE] == "1",
                status=f[STATUS],
                mode=f[MODE],
                ipv4=_first_ipv4(f[MODE + 1 :]),
                uptime=_uptime(f),
            )
        )
    return conns


class SelectionError(Exception):
    pass


def _names(conns):
    return ", ".join(c.name for c in conns) or "none found"


def _pick_by_name(conns, name):
    for c in conns:
        if c.name == name:
            return c
    raise SelectionError(f"no WAN connection named {name!r}; available: {_names(conns)}")


def _pick_active(conns):
    active = [c for c in conns if c.is_active]
    if len(active) == 1:
        return active[0]
    if not active:
        raise SelectionError(
            "no connected internet WAN found; run 'wan-reconnect status' and pass --wan NAME"
        )
    raise SelectionError(f"several connected WANs ({_names(active)}); choose one with --wan NAME")


def pick(conns, name=None):
    """Return the one connection to reconnect, or raise SelectionError explaining why not."""
    return _pick_by_name(conns, name) if name else _pick_active(conns)
