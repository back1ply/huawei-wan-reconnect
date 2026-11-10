"""Router connection options shared by the commands that log in."""

import getpass
import os
import sys

from huawei_wan_reconnect.core.router import Router, RouterError


def interactive():
    """True only when a person can answer a prompt. Windows reports NUL as a TTY,
    so stderr must be a terminal too."""
    return sys.stdin.isatty() and sys.stderr.isatty()


def add_router_args(parser):
    parser.add_argument(
        "--router",
        default=os.environ.get("ROUTER_IP", "192.168.1.1"),
        help="router address (env ROUTER_IP, default: %(default)s)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("ROUTER_USER", "admin"),
        help="web UI user (env ROUTER_USER, default: %(default)s)",
    )
    parser.add_argument(
        "--password-file",
        metavar="PATH",
        help="file holding the web UI password (else env ROUTER_PASS, else a prompt)",
    )


def get_password(password_file):
    if password_file:
        try:
            with open(password_file, encoding="utf-8") as f:
                return f.read().strip()
        except OSError as e:
            raise RouterError(
                f"cannot read --password-file {password_file}: {e.strerror}"
            ) from None
    if pw := os.environ.get("ROUTER_PASS"):
        return pw
    if not interactive():
        raise RouterError("no password: set ROUTER_PASS or pass --password-file PATH")
    return getpass.getpass("Router password: ")


def connect(args):
    router = Router(args.router)
    router.login(args.user, get_password(args.password_file))
    return router
