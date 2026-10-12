"""The Claude app in front: render and the OLED, from the frame's app field."""
import oled
import render
from render import AMBER, BLUE, GREEN, LIVE, NONE, OFF, STALE, WHITE, scale

GREY = (60, 60, 60)
FLEET = {
    "name": "FLEET",
    "keys": [
        ("A1", GREY, None), ("A2", GREY, None), ("A3", GREY, None),
        ("A4", GREY, None), ("A5", GREY, None), ("A6", GREY, None),
        ("ATTN", AMBER, None), ("NEW", BLUE, None), ("RESUME", BLUE, None),
        ("ZOOM", BLUE, None), ("LAST", BLUE, None), ("ENTER", GREEN, None),
    ],
}
DRIVE = {
    "name": "DRIVE",
    "keys": [(label, (i + 1, i + 1, i + 1), None) for i, label in enumerate(
        ["ESC", "MODE", "REWIND", "YES", "ALWAYS", "NO",
         "TAB", "LOG", "COMPCT", "ENTER", "TALK", "BG"])],
}
BLINK_ON = 100


def frame(**kw):
    f = {"t": "state", "v": 2, "slots": ["N", "W", "R", None, None, None], "focus": 2,
         "fstate": "W", "overflow": {}, "herdr": True, "space": "web", "app": "claude"}
    f.update(kw)
    return f


def test_app_mode_needs_a_live_frame_naming_the_claude_app():
    assert render.app_mode(frame(), LIVE)
    assert render.app_mode(frame(herdr=False), LIVE)  # app detection doesn't need herdr
    assert not render.app_mode(frame(), STALE)
    assert not render.app_mode(frame(), NONE)
    assert not render.app_mode(None, LIVE)
    assert not render.app_mode(frame(app=None), LIVE)
    assert not render.app_mode(frame(app="other"), LIVE)
    f = frame()
    del f["app"]
    assert not render.app_mode(f, LIVE)


def test_drive_shows_layout_colors_on_keys_that_work_in_the_app():
    out = render.render(DRIVE, frame(), LIVE, set(), BLINK_ON)
    for (label, color, _), got in zip(DRIVE["keys"], out):
        assert got == (OFF if label in ("REWIND", "BG") else color), label


def test_fleet_lights_the_sidebar_keys_and_darkens_unmapped_keys():
    out = render.render(FLEET, frame(), LIVE, set(), BLINK_ON)
    assert out[:6] == [scale(WHITE, render.QUIET)] * 6  # Cmd+1..6
    for n in (8, 9, 10):  # RESUME, ZOOM, LAST
        assert out[n] == OFF
    assert out[6] == scale(AMBER, render.QUIET)  # ATTN: asks Tally
    assert out[7] == scale(BLUE, render.QUIET)   # NEW: Cmd+N
    assert out[11] == scale(GREEN, render.QUIET)  # ENTER: not tied to herdr's focus


def test_fleet_in_the_app_with_herdr_offline():
    out = render.render(FLEET, frame(herdr=False, slots=[None] * 6), LIVE, set(), 0)
    assert out[:6] == [scale(WHITE, render.QUIET)] * 6  # Cmd+1..6 don't need herdr
    assert out[6] == scale(AMBER, render.QUIET) and out[8] == OFF


def test_stale_frame_falls_back_to_herdr_lighting():
    assert render.render(DRIVE, frame(), STALE, set(), 0) == [k[1] for k in DRIVE["keys"]]
    assert render.render(FLEET, frame(), STALE, set(), 0) == [scale(k[1], render.DIMMED) for k in FLEET["keys"]]


def test_held_keys_and_the_alert_still_show_in_the_app():
    out = render.render(DRIVE, frame(), LIVE, {0, 10}, 0)
    assert out[0] == render.PRESS and out[10] == render.PURPLE
    assert render.render(DRIVE, frame(), LIVE, set(), 0, flash=True) == [AMBER] * 12


def test_unmapped_labels():
    assert not set(render.SLOT_LABELS) & set(render.APP_UNMAPPED)
    for label in ("ESC", "MODE", "YES", "ALWAYS", "NO", "TAB", "LOG", "COMPCT", "ENTER", "TALK", "NEW", "ATTN"):
        assert label not in render.APP_UNMAPPED


def test_oled_names_the_app_and_keeps_herdrs_waiting_list():
    text = oled.lines(DRIVE, frame(), LIVE)
    assert text[0] == "DRIVE CLAUDE APP    *"
    assert text[1] == "A1-A6 = CMD+1-6"
    assert text[2] == "HERDR A1 WAITING"
    assert text[3] == "1N 2W 3R 4- 5- 6-"
    assert all(len(line) <= oled.WIDTH for line in text)


def test_oled_in_the_app_with_herdr_offline():
    text = oled.lines(FLEET, frame(herdr=False), LIVE)
    assert text[0] == "FLEET CLAUDE APP    h"
    assert text[1] == "HERDR OFFLINE"


def test_oled_leaves_app_mode_when_the_frame_goes_stale():
    assert oled.lines(DRIVE, frame(), STALE)[1] == "TALLY OFFLINE"
    assert not oled.lines(DRIVE, frame(), STALE)[0].startswith("DRIVE CLAUDE")
