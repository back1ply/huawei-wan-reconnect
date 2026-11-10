"""Root parser and lazy subcommand dispatch."""

import argparse
import importlib
import importlib.metadata
import sys

COMMANDS = {
    "status": ("huawei_wan_reconnect.commands.status:main", "list WAN connections"),
    "check": ("huawei_wan_reconnect.commands.check:main", "is the ISP quota redirect active?"),
    "reconnect": ("huawei_wan_reconnect.commands.reconnect:main", "disable + re-enable active WAN"),
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wan-reconnect",
        description="Find the active internet connection on a Huawei DN8245V router and "
        "reconnect it, e.g. to clear a stuck WE/TE Data quota redirect.",
        epilog="Run 'wan-reconnect COMMAND --help' for command options.",
    )
    parser.add_argument(
        "--version", action="version", version=importlib.metadata.version("huawei-wan-reconnect")
    )
    parser.add_argument(
        "command",
        choices=COMMANDS,
        metavar="COMMAND",
        help="; ".join(f"{k}: {v[1]}" for k, v in COMMANDS.items()),
    )
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        build_parser().print_help(sys.stderr)
        return 2
    if argv[0] not in COMMANDS:
        build_parser().parse_args(argv[:1])  # prints help/version or exits 2
    module_name, _, func_name = COMMANDS[argv[0]][0].partition(":")
    func = getattr(importlib.import_module(module_name), func_name)
    return func(argv[1:])
