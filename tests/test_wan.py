import pytest

from huawei_wan_reconnect.core.router import unescape_js
from huawei_wan_reconnect.core.wan import SelectionError, parse_connections, pick


def test_parse_reads_status_ip_and_uptime(one_active):
    conns = parse_connections(one_active)
    assert [c.name for c in conns] == [
        "1_TR069_INTERNET_R_VID_",
        "2_INTERNET_B_VID_",
        "3_TR069_INTERNET_R_VID_",
    ]
    active = conns[2]
    assert (active.kind, active.status, active.ipv4, active.uptime) == (
        "PPPoE",
        "Connected",
        "203.0.113.5",
        3600,
    )
    assert conns[0].ipv4 == "" and not conns[0].enabled
    assert conns[1].kind == "IP" and conns[1].ipv4 == ""


def test_ip_record_does_not_mistake_dhcp_for_address():
    from conftest import DOM, ipwan

    c = parse_connections(
        ipwan(DOM.format(5, "IP"), "x", status="Connected", mode="IP_Routed", ip="203.0.113.7")
    )
    assert c[0].ipv4 == "203.0.113.7" and c[0].is_active


def test_pick_auto_selects_single_active(one_active):
    assert pick(parse_connections(one_active)).name == "3_TR069_INTERNET_R_VID_"


def test_pick_refuses_to_guess_between_two(two_active):
    with pytest.raises(SelectionError, match="--wan NAME"):
        pick(parse_connections(two_active))


def test_pick_by_name_and_unknown_name(two_active):
    conns = parse_connections(two_active)
    assert pick(conns, "4_INTERNET_R_VID_10").ipv4 == "203.0.113.9"
    with pytest.raises(SelectionError, match="available"):
        pick(conns, "nope")


def test_unescape_js():
    assert unescape_js(r"1\x5fTR069\x2e") == "1_TR069."
