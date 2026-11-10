import pytest


def _record(kind, domain, fields):
    return f'new {kind}("{domain}",' + ",".join(f'"{f}"' for f in fields) + ")"


def ppp(domain, name, **opt):
    """Fake WanPPP record. Options: status, ip, uptime, enable."""
    status = opt.get("status", "Connected")
    fields = ["0", "0", "AlwaysOn", "00:00:5E:00:53:01", status, "ERROR_NONE", "", name,
              opt.get("enable", "1"), "", "", status, "IP_Routed", opt.get("ip", "203.0.113.5"),
              "203.0.113.1", "1", "0", "198.51.100.1,198.51.100.2", "user", "pass", "AlwaysOn",
              "DetectBidirectionally", opt.get("uptime", "3600"), "0"]  # fmt: skip
    return _record("WanPPP", domain, fields)


def ipwan(domain, name, **opt):
    """Fake WanIP record. Options: status, mode, ip."""
    status = opt.get("status", "Disconnected")
    fields = ["0", "0", "AlwaysOn", "", status, "ERROR_NONE", "", name, "0", "", "", status,
              opt.get("mode", "IP_Bridged"), "DHCP", opt.get("ip", ""), "", "", "0", "0"]  # fmt: skip
    return _record("WanIP", domain, fields)


DOM = "InternetGatewayDevice.WANDevice.{}.WANConnectionDevice.1.WAN{}Connection.1"


@pytest.fixture
def one_active():
    return (
        "var WanList = new Array("
        + ",".join(
            [
                ppp(
                    DOM.format(1, "PPP"),
                    "1_TR069_INTERNET_R_VID_",
                    status="Disconnected",
                    ip="0.0.0.0",
                    uptime="0",
                    enable="0",
                ),
                ipwan(DOM.format(2, "IP"), "2_INTERNET_B_VID_"),
                ppp(DOM.format(3, "PPP"), "3_TR069_INTERNET_R_VID_"),
            ]
        )
        + ",null);"
    )


@pytest.fixture
def two_active(one_active):
    return one_active + ppp(DOM.format(4, "PPP"), "4_INTERNET_R_VID_10", ip="203.0.113.9")
