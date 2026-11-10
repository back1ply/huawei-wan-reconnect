import argparse
import json
import sys
import time

from huawei_wan_reconnect.core.auth import add_router_args, connect, interactive
from huawei_wan_reconnect.core.router import RouterError
from huawei_wan_reconnect.core.wan import SelectionError, pick


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wan-reconnect reconnect",
        description="Disable and re-enable the active WAN connection so the router dials a "
        "fresh session. Internet drops for roughly 20-30 seconds; Wi-Fi stays up.",
        epilog="Example: ROUTER_PASS=... wan-reconnect reconnect --yes",
    )
    add_router_args(parser)
    parser.add_argument(
        "--wan", metavar="NAME", help="connection name from 'status' (default: auto)"
    )
    parser.add_argument("--dry-run", action="store_true", help="show what would be reconnected")
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    parser.add_argument("--off-seconds", type=int, default=10, help="pause while off (default: 10)")
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    return parser


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def current(router, domain):
    for c in router.connections():
        if c.domain == domain:
            return c
    raise RouterError(f"connection {domain} disappeared from the WAN list")


def wait_for(router, domain, done, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(3)
        c = current(router, domain)
        log(f"  {time.strftime('%X')} {c.status} {c.ipv4 or '-'}")
        if done(c):
            return c
    return None


def confirm(name, args):
    if args.yes:
        return True
    if not interactive():
        raise RouterError("refusing to reconnect without confirmation; pass --yes")
    return input(f"Reconnect {name}? Internet drops ~30s. [y/N] ").strip().lower() == "y"


def _maybe_relogin(router, relogins_left):
    """Log in again if budget remains; repeated failed logins can lock the account."""
    if relogins_left <= 0:
        return 0
    try:
        router.relogin()
    except RouterError as e:
        log(f"  relogin failed: {e}")
    return relogins_left - 1


def _enable_once(router, domain):
    router.set_enable(domain, True)
    return wait_for(router, domain, lambda c: c.status == "Connected" and c.ipv4, 90)


def reenable(router, domain, attempts=5, max_relogins=2):
    """Turn the WAN back on, reusing the session and logging in again only when needed."""
    relogins_left = max_relogins
    for attempt in range(1, attempts + 1):
        try:
            c = _enable_once(router, domain)
            if c:
                return c
        except RouterError as e:
            log(f"  attempt {attempt}: {e}")
            relogins_left = _maybe_relogin(router, relogins_left)
        time.sleep(5)
    return None


def _wait_dropped(router, domain, off_seconds):
    try:
        dropped = wait_for(router, domain, lambda c: c.status != "Connected", 30)
    except RouterError as e:
        log(f"  {e}")
        return False
    if dropped:
        time.sleep(off_seconds)
    return bool(dropped)


def cycle(router, target, off_seconds):
    """Turn the connection off and back on. The re-enable always runs, even on Ctrl+C."""
    log(f"disabling {target.name} ...")
    router.set_enable(target.domain, False)
    dropped = False
    try:
        dropped = _wait_dropped(router, target.domain, off_seconds)
    finally:
        log(f"enabling {target.name} ...")
        after = reenable(router, target.domain)
    if not after:
        raise RouterError(f"{target.name} did not come back; re-enable it in the router's WAN page")
    if not dropped:
        raise RouterError("router did not drop the connection; it is still on")
    return after


def run(args):
    router = connect(args)
    target = pick(router.connections(), args.wan)
    before = target.to_dict()
    if args.dry_run:
        return {"dry_run": True, "connection": before}, 0
    if not confirm(target.name, args):
        log("cancelled")
        return {"cancelled": True, "connection": before}, 1
    after = cycle(router, target, args.off_seconds)
    return {"before": before, "after": after.to_dict()}, 0


def _describe(result):
    if "after" in result:
        b, a = result["before"], result["after"]
        return f"reconnected {a['name']}: {b['ipv4']} -> {a['ipv4']}"
    if result.get("dry_run"):
        c = result["connection"]
        return f"would reconnect {c['name']} ({c['kind']}, {c['ipv4']})"
    return ""


def _emit(doc, text, stream, as_json):
    if as_json:
        json.dump(doc, stream)
        stream.write("\n")
    elif text:
        print(text, file=stream)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except (RouterError, SelectionError) as e:
        _emit({"error": str(e)}, f"error: {e}", sys.stderr, args.json)
        return 1
    _emit(result, _describe(result), sys.stdout, args.json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
