import pytest


def ppp(domain, name, status, ip, uptime="3600", enable="1"):
    fields = [
        "0",
        "0",
        "AlwaysOn",
        "00:00:5E:00:53:01",
        status,
        "ERROR_NONE",
        "",
        name,
        enable,
        "",
        "",
        status,
        "IP_Routed",
        ip,
        "203.0.113.1",
        "1",
        "0",
        "198.51.100.1,198.51.100.2",
        "user",
        "pass",
        "AlwaysOn",
        "DetectBidirectionally",
        uptime,
        "0",
    ]
    return f'new WanPPP("{domain}",' + ",".join(f'"{f}"' for f in fields) + ")"


def ipwan(domain, name, status="Disconnected", mode="IP_Bridged", ip=""):
    fields = [
        "0",
        "0",
        "AlwaysOn",
        "",
        status,
        "ERROR_NONE",
        "",
        name,
        "0",
        "",
        "",
        status,
        mode,
        "DHCP",
        ip,
        "",
        "",
        "0",
        "0",
    ]
    return f'new WanIP("{domain}",' + ",".join(f'"{f}"' for f in fields) + ")"


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
                    "Disconnected",
                    "0.0.0.0",
                    "0",
                    "0",
                ),
                ipwan(DOM.format(2, "IP"), "2_INTERNET_B_VID_"),
                ppp(DOM.format(3, "PPP"), "3_TR069_INTERNET_R_VID_", "Connected", "203.0.113.5"),
            ]
        )
        + ",null);"
    )


@pytest.fixture
def two_active(one_active):
    return one_active + ppp(DOM.format(4, "PPP"), "4_INTERNET_R_VID_10", "Connected", "203.0.113.9")
