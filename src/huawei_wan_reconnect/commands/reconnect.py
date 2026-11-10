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


def reenable(router, domain, attempts=5, max_relogins=2):
    """Turn the WAN back on. Reuses the session and logs in again at most
    max_relogins times, because repeated failed logins can lock the account."""
    relogins = 0
    for attempt in range(1, attempts + 1):
        try:
            router.set_enable(domain, True)
            c = wait_for(router, domain, lambda c: c.status == "Connected" and c.ipv4, 90)
            if c:
                return c
        except RouterError as e:
            log(f"  attempt {attempt}: {e}")
            if relogins < max_relogins:
                relogins += 1
                try:
                    router.relogin()
                except RouterError as e2:
                    log(f"  relogin failed: {e2}")
        time.sleep(5)
    return None


def run(args):
    router = connect(args)
    target = pick(router.connections(), args.wan)
    before = target.to_dict()
    if args.dry_run:
        return {"dry_run": True, "connection": before}, 0
    if not confirm(target.name, args):
        log("cancelled")
        return {"cancelled": True, "connection": before}, 1

    log(f"disabling {target.name} ...")
    router.set_enable(target.domain, False)
    dropped = False
    try:
        dropped = wait_for(router, target.domain, lambda c: c.status != "Connected", 30)
        if dropped:
            time.sleep(args.off_seconds)
    except RouterError as e:
        log(f"  {e}")
    finally:
        # Always turn it back on, including after an error or Ctrl+C.
        log(f"enabling {target.name} ...")
        after = reenable(router, target.domain)

    if not after:
        raise RouterError(f"{target.name} did not come back; re-enable it in the router's WAN page")
    if not dropped:
        raise RouterError("router did not drop the connection; it is still on")
    return {"before": before, "after": after.to_dict()}, 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except (RouterError, SelectionError) as e:
        if args.json:
            json.dump({"error": str(e)}, sys.stderr)
            sys.stderr.write("\n")
        else:
            print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    elif "after" in result:
        b, a = result["before"], result["after"]
        print(f"reconnected {a['name']}: {b['ipv4']} -> {a['ipv4']}")
    elif result.get("dry_run"):
        c = result["connection"]
        print(f"would reconnect {c['name']} ({c['kind']}, {c['ipv4']})")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
