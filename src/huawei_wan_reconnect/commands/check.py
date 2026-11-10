import argparse
import json
import sys

from huawei_wan_reconnect.core.redirect import check

EXIT_REDIRECTED = 3


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wan-reconnect check",
        description="Probe plain-HTTP sites and report whether the ISP quota redirect is active. "
        f"Exit 0 = clear, {EXIT_REDIRECTED} = redirected, 1 = no network.",
        epilog="Example: wan-reconnect check --json",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    state, results = check()
    if args.json:
        json.dump({"state": state, "probes": results}, sys.stdout)
        sys.stdout.write("\n")
    else:
        for r in results:
            print(f"{r['url']:28} {r['status'] or 'no reply'} {r['location']}".rstrip())
        print(state)
    return {"clear": 0, "redirected": EXIT_REDIRECTED}.get(state, 1)


if __name__ == "__main__":
    raise SystemExit(main())
