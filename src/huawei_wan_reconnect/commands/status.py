import argparse
import json
import sys

from huawei_wan_reconnect.core.auth import add_router_args, connect
from huawei_wan_reconnect.core.router import RouterError


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wan-reconnect status",
        description="List the router's WAN connections and mark the active one.",
        epilog="Example: ROUTER_PASS=... wan-reconnect status --json",
    )
    add_router_args(parser)
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    return parser


def format_uptime(seconds):
    if seconds is None:
        return "-"
    h, rem = divmod(seconds, 3600)
    return f"{h}h{rem // 60:02d}m"


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        conns = connect(args).connections()
    except RouterError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        json.dump([c.to_dict() for c in conns], sys.stdout)
        sys.stdout.write("\n")
        return 0
    print(f"{'':2}{'NAME':32} {'TYPE':6} {'ENABLED':8} {'STATUS':13} {'IPV4':16} UPTIME")
    for c in conns:
        mark = "* " if c.is_active else "  "
        print(
            f"{mark}{c.name:32} {c.kind:6} {'yes' if c.enabled else 'no':8} {c.status:13} "
            f"{c.ipv4 or '-':16} {format_uptime(c.uptime)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
