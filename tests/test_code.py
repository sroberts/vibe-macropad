"""Smoke tests for firmware/code.py's main loop against fake hardware."""
import json

from fake_macropad import load_code, press, push, release, turn
from render import LIVE, NONE
from test_tally_link import FakeData

TALK, REWIND, ESC = 10, 2, 0


def keys(log):
    return [e for e in log if e[0] in ("press", "release", "release_all", "write")]


def test_hold_presses_until_release(monkeypatch):
    code = load_code(monkeypatch, [press(TALK), None, release(TALK)])
    assert keys(code.macropad.log) == [("press", "RIGHT_ALT"), ("release", "RIGHT_ALT")]


def test_layer_switch_releases_a_held_key(monkeypatch):
    code = load_code(monkeypatch, [press(TALK), push, release(TALK), push])
    # TALK's release lands on FLEET, where key 10 is LAST: nothing to release
    # there, and release_all already let go of Right Option.
    assert keys(code.macropad.log) == [("press", "RIGHT_ALT"), ("release_all",), ("release_all",)]
    assert code.held == set() and code.layer_index == 0


def test_encoder_steps_per_detent(monkeypatch):
    code = load_code(monkeypatch, [turn(2), turn(-1)])
    assert keys(code.macropad.log) == [("press", "DOWN_ARROW"), ("release_all",)] * 2 + \
        [("press", "UP_ARROW"), ("release_all",)]


def test_rewind_sends_two_escapes_without_blocking(monkeypatch):
    code = load_code(monkeypatch, [press(REWIND), release(REWIND), press(ESC)])
    log = code.macropad.log
    escapes = [i for i, e in enumerate(log) if e == ("press", "ESCAPE")]
    assert len(escapes) == 3  # ESC, ESC from REWIND, then the ESC key
    assert any(e[0] == "pixels" for e in log[escapes[0]:escapes[1]])  # lights ran in the gap
    assert code.rewind_due is None


def test_label_grid_until_tally_speaks(monkeypatch):
    code = load_code(monkeypatch, [None])
    assert code.oled_screen is code.SCREENS[0]
    assert [line.text for line in code.SCREENS[0]][0].split() == ["ESC", "MODE", "REWIND"]


def test_status_lines_rebuild_only_when_their_inputs_change(monkeypatch):
    data = FakeData()
    code = load_code(monkeypatch, data=data)
    frame = {"t": "state", "v": 2, "slots": ["W"], "focus": 1, "fstate": "W", "herdr": True}
    data.feed((json.dumps(frame) + "\n").encode())
    code.link.poll(0)
    updates = []
    real = code.status_screen.update
    monkeypatch.setattr(code.status_screen, "update", lambda text: (updates.append(text), real(text)))

    f = code.link.frame
    code.show_status(0, f, LIVE, 5000)
    code.show_status(0, f, LIVE, 5999)          # same second, same inputs
    assert len(updates) == 1 and code.oled_screen is code.status_screen
    code.show_status(0, f, LIVE, 6000)          # each second, for the timers
    code.show_status(1, f, LIVE, 6000)          # another layer
    assert len(updates) == 3 and updates[-1][0].startswith("FLEET")
    code.show_status(0, None, NONE, 6000)       # back to the label grid
    assert len(updates) == 3 and code.oled_screen is code.SCREENS[0]
    assert ("screen", "DRIVE") in code.macropad.log
