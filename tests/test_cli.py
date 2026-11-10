import importlib
import json

import pytest

from huawei_wan_reconnect import cli
from huawei_wan_reconnect.commands import check as check_cmd
from huawei_wan_reconnect.core.router import Router, RouterError


@pytest.mark.parametrize("name", cli.COMMANDS)
def test_every_command_resolves(name):
    module_name, _, func_name = cli.COMMANDS[name][0].partition(":")
    assert callable(getattr(importlib.import_module(module_name), func_name))


def test_no_args_prints_help_to_stderr(capsys):
    assert cli.main([]) == 2
    out, err = capsys.readouterr()
    assert out == "" and "usage" in err


def test_unknown_flag_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["status", "--bogus"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == "" and "--bogus" in err


@pytest.fixture
def fake_router(monkeypatch, one_active):
    calls = []
    monkeypatch.setenv("ROUTER_PASS", "x")
    monkeypatch.setattr(Router, "login", lambda self, u, p: setattr(self, "wan_page", "w.asp"))
    monkeypatch.setattr(Router, "wan_list", lambda self: one_active)
    monkeypatch.setattr(Router, "set_enable", lambda self, d, e: calls.append((d, e)))
    return calls


def test_status_json(fake_router, capsys):
    assert cli.main(["status", "--json"]) == 0
    out, err = capsys.readouterr()
    data = json.loads(out)
    assert [c["name"] for c in data if c["active"]] == ["3_TR069_INTERNET_R_VID_"]
    assert err == "" and "pass" not in out


def test_status_text_marks_active(fake_router, capsys):
    assert cli.main(["status"]) == 0
    out, _ = capsys.readouterr()
    assert "* 3_TR069_INTERNET_R_VID_" in out


def test_reconnect_dry_run_changes_nothing(fake_router, capsys):
    assert cli.main(["reconnect", "--dry-run", "--json"]) == 0
    out, _ = capsys.readouterr()
    assert json.loads(out)["connection"]["name"] == "3_TR069_INTERNET_R_VID_"
    assert fake_router == []


def test_reconnect_without_tty_needs_yes(fake_router, capsys, monkeypatch):
    monkeypatch.setattr("huawei_wan_reconnect.core.auth.interactive", lambda: False)
    monkeypatch.setattr("huawei_wan_reconnect.commands.reconnect.interactive", lambda: False)
    assert cli.main(["reconnect"]) == 1
    out, err = capsys.readouterr()
    assert out == "" and "--yes" in err and fake_router == []


def test_missing_password_without_tty(monkeypatch, capsys):
    monkeypatch.delenv("ROUTER_PASS", raising=False)
    monkeypatch.setattr("huawei_wan_reconnect.core.auth.interactive", lambda: False)
    monkeypatch.setattr("huawei_wan_reconnect.commands.reconnect.interactive", lambda: False)
    assert cli.main(["status"]) == 1
    _, err = capsys.readouterr()
    assert "ROUTER_PASS" in err and "Traceback" not in err


@pytest.mark.parametrize("state,code", [("clear", 0), ("redirected", 3), ("unknown", 1)])
def test_check_exit_codes(monkeypatch, capsys, state, code):
    monkeypatch.setattr(check_cmd, "check", lambda: (state, []))
    assert cli.main(["check", "--json"]) == code
    assert json.loads(capsys.readouterr().out)["state"] == state


class FlakyRouter:
    """Fake router whose WAN list fails once right after the disable."""

    def __init__(self, page_connected, page_down):
        self.pages = {True: page_connected, False: page_down}
        self.enabled = True
        self.calls = []
        self.fail_next_poll = False

    def install(self, monkeypatch):
        monkeypatch.setenv("ROUTER_PASS", "x")
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr(Router, "login", lambda r, u, p: setattr(r, "wan_page", "w.asp"))
        monkeypatch.setattr(Router, "relogin", lambda r: None)
        monkeypatch.setattr(Router, "wan_list", lambda r: self.wan_list())
        monkeypatch.setattr(Router, "set_enable", lambda r, d, e: self.set_enable(d, e))

    def set_enable(self, domain, enabled):
        self.calls.append((domain, enabled))
        self.enabled = enabled
        self.fail_next_poll = not enabled

    def wan_list(self):
        if self.fail_next_poll:
            self.fail_next_poll = False
            raise RouterError("router hiccup")
        return self.pages[self.enabled]


def test_reconnect_reenables_even_after_error(monkeypatch, capsys, one_active):
    down = one_active.replace('"Connected","ERROR_NONE"', '"Disconnected","ERROR_NONE"')
    fake = FlakyRouter(one_active, down)
    fake.install(monkeypatch)
    assert cli.main(["reconnect", "--yes"]) == 1  # the drop was never confirmed
    _, err = capsys.readouterr()
    assert fake.calls[0][1] is False and fake.calls[-1][1] is True
    assert "router hiccup" in err


def test_reconnect_happy_path(monkeypatch, capsys, one_active):
    down = one_active.replace('"Connected","ERROR_NONE"', '"Disconnected","ERROR_NONE"')
    fake = FlakyRouter(one_active, down)
    fake.install(monkeypatch)
    fake.set_enable = lambda d, e: (fake.calls.append((d, e)), setattr(fake, "enabled", e))
    assert cli.main(["reconnect", "--yes", "--json"]) == 0
    out, _ = capsys.readouterr()
    assert json.loads(out)["after"]["status"] == "Connected"
    assert [e for _, e in fake.calls] == [False, True]
