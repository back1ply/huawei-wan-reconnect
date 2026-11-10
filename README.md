# huawei-wan-reconnect

Find the internet connection your **Huawei DN8245V** router is actually using and
reconnect it (turn it off and back on) without rebooting the router.

Built for **WE / Telecom Egypt (TE Data)** home VDSL lines. After you renew a
used-up package, the line can stay stuck on the
`megaplusredirection.tedata.net/VDSL-Redirection_100.html` "you have consumed
100% of your quota" page, even after clicking **Continue Browsing**. The block
is attached to the router's current connection, so it lasts until the router
dials a new one. This tool does that in about 20 seconds; Wi-Fi stays up.

Changing DNS (to TE's or anyone else's) does not fix it: the redirect also
happens when you open a site by its bare IP address.

## Install

Needs Python 3.10+ and no other packages.

```bash
uv tool install git+https://github.com/back1ply/huawei-wan-reconnect
# or
pipx install git+https://github.com/back1ply/huawei-wan-reconnect
# or, from a clone
pip install .
```

This installs the `wan-reconnect` command.

## Use

Run these from a device connected to the router. The password is the router's
web page password (the `admin` user).

```bash
export ROUTER_PASS='your-router-password'   # PowerShell: $env:ROUTER_PASS='...'

wan-reconnect check                # is the quota redirect active?
wan-reconnect status               # list connections; * marks the active one
wan-reconnect reconnect --dry-run  # show which connection it would reconnect
wan-reconnect reconnect            # do it (asks first; --yes skips the question)
```

Example:

```
$ wan-reconnect status
  NAME                     TYPE   ENABLED  STATUS        IPV4          UPTIME
  1_TR069_INTERNET_R_VID_  PPPoE  no       Disconnected  -             0h00m
* 7_TR069_INTERNET_R_VID_  PPPoE  yes      Connected     203.0.113.5   44h21m

$ wan-reconnect reconnect --yes
disabling 7_TR069_INTERNET_R_VID_ ...
enabling 7_TR069_INTERNET_R_VID_ ...
reconnected 7_TR069_INTERNET_R_VID_: 203.0.113.5 -> 198.51.100.20
```

### How it picks the connection

Routers list several connections (ADSL, VDSL, Ethernet, 4G backup), and the one
in use differs between homes: `1_...`, `3_...`, `7_...` and so on. The tool
reads the router's live WAN list and picks the connection that is
**Connected**, **routed**, and has a public IPv4 address. If none or several
match, it stops and asks you to choose with `--wan NAME` (names come from
`status`).

### Options

| Option | Commands | Meaning |
|---|---|---|
| `--router ADDR` | status, reconnect | router address (env `ROUTER_IP`, default `192.168.1.1`) |
| `--user NAME` | status, reconnect | web user (env `ROUTER_USER`, default `admin`) |
| `--password-file PATH` | status, reconnect | read the password from a file instead of `ROUTER_PASS` |
| `--wan NAME` | reconnect | reconnect this connection instead of auto-picking |
| `--dry-run` | reconnect | show the choice, change nothing |
| `--yes` | reconnect | no confirmation (required when not run from a terminal) |
| `--off-seconds N` | reconnect | how long to stay off (default 10) |
| `--json` | all | print one JSON document on stdout |

If no password is given and the tool runs in a terminal, it asks for one.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | success (`check`: no redirect) |
| 1 | failure (login, network, no single active connection, did not reconnect) |
| 2 | bad command-line usage |
| 3 | `check` only: the quota redirect is active |

## What it changes

Only the **Enable** flag of the one connection: off, wait, on. It sends the same
`set.cgi` request the router's own WAN page uses. Nothing else in your settings
is touched. You can confirm this in the router log (System Tools → Log), which
shows only `Enable:0` and then `Enable:1`.

If the connection doesn't come back after five tries, the tool says so. Turn it
on yourself in the router's WAN page by ticking **Enable** on that connection.

## Notes

- The router allows one web session at a time. Running the tool may log out a
  router page open in your browser, and an open browser session can make the
  tool's login fail. Close the page and try again.
- The password is never printed or written anywhere. Prefer `ROUTER_PASS` or
  `--password-file` over typing it in shared shell history.
- The router uses a self-signed certificate on your local network, so the tool
  doesn't verify it.
- `check` probes `http://example.com/` and `http://detectportal.firefox.com/success.txt` (in parallel) without
  following redirects and looks for a redirect to a `...redirection...` host.

## Tested on

Huawei EchoLife **DN8245V-56**, firmware `V500R022C10SPC205 WE`, as supplied by
WE / TE Data Egypt. Other Huawei models with the same web UI (`set.cgi`,
`wan_list_cache_wan.asp`) may work; run `status` and `reconnect --dry-run`
first. Reports from other models are welcome.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

## نبذة بالعربي

لو جددت باقة وي (WE) وفضلت صفحة "تم استهلاك ١٠٠٪ من باقتك" تظهر، المشكلة إن
الراوتر لسه شغال على نفس الاتصال القديم. الأداة دي بتلاقي الاتصال المستخدم فعلاً
في راوتر Huawei DN8245V وتقفله وتفتحه تاني من غير ما تعمل ريستارت للراوتر.
تغيير الـ DNS مش هيحل المشكلة.

```bash
export ROUTER_PASS='باسورد الراوتر'
wan-reconnect reconnect
```

## License

MIT
