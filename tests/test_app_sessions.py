"""The Claude app's sessions on A1..A6, and key messages to Tally."""
import io

import oled
import render
import tally_link
from render import AMBER, BLUE, GREEN, LIVE, OFF, WHITE, scale

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
DRIVE = {"name": "DRIVE", "keys": [(label, GREY, None) for label in
         ["ESC", "MODE", "REWIND", "YES", "ALWAYS", "NO",
          "TAB", "LOG", "COMPCT", "ENTER", "TALK", "BG"]]}


def frame(**kw):
    f = {"t": "state", "v": 2, "slots": ["N", "W", None, None, None, None], "focus": 2,
         "fstate": "W", "overflow": {}, "herdr": True, "app": "claude", "asess": 3, "afocus": 2}
    f.update(kw)
    return f


def test_slot_keys_show_the_apps_sessions():
    out = render.render(FLEET, frame(), LIVE, set(), 100)
    assert out[0] == scale(WHITE, render.APP_SESSION)
    assert out[1] == scale(WHITE, render.APP_SHOWING)  # the session the app shows
    assert out[2] == scale(WHITE, render.APP_SESSION)
    assert out[3:6] == [OFF, OFF, OFF]                 # no fourth session


def test_slot_keys_without_session_fields():
    for f in (frame(asess=None, afocus=None), frame(asess="3"), frame(asess=0)):
        assert render.render(FLEET, f, LIVE, set(), 100)[:6] == [OFF] * 6
    out = render.render(FLEET, frame(afocus=None), LIVE, set(), 100)
    assert out[:3] == [scale(WHITE, render.APP_SESSION)] * 3


def test_attn_and_new_stay_quiet_and_unmapped_keys_go_dark():
    out = render.render(FLEET, frame(), LIVE, set(), 100)
    assert out[6] == scale(AMBER, render.QUIET)
    assert out[7] == scale(BLUE, render.QUIET)
    assert out[8:11] == [OFF, OFF, OFF]
    assert out[11] == scale(GREEN, render.QUIET)


def test_app_keys_that_ask_tally_are_not_unmapped():
    for label in render.SLOT_LABELS + ("ATTN",):
        assert label not in render.APP_UNMAPPED
    assert set(render.APP_UNMAPPED) == {"RESUME", "ZOOM", "LAST", "REWIND", "BG"}


def test_oled_counts_the_apps_sessions():
    assert oled.lines(DRIVE, frame(), LIVE)[1] == "SESSION 2 OF 3"
    assert oled.lines(DRIVE, frame(afocus=None), LIVE)[1] == "3 SESSIONS"
    assert oled.lines(DRIVE, frame(asess=1, afocus=None), LIVE)[1] == "1 SESSION"
    assert oled.lines(DRIVE, frame(asess=None), LIVE)[1] == "NO SESSIONS"
    assert oled.lines(DRIVE, frame(afocus=7), LIVE)[1] == "3 SESSIONS"


def test_oled_marks_herdrs_waiting_list():
    text = oled.lines(DRIVE, frame(), LIVE)
    assert text[0] == "DRIVE CLAUDE APP    *"
    assert text[2] == "HERDR A1 WAITING"
    assert text[3] == "1N 2W 3- 4- 5- 6-"
    assert oled.lines(DRIVE, frame(slots=["R"] * 6), LIVE)[2] == ""
    assert all(len(line) <= oled.WIDTH for line in text)


class Stream(io.BytesIO):
    in_waiting = 0


class ClosedStream(Stream):
    def write(self, data):
        raise OSError("host not reading")


def test_send_key_writes_one_message():
    stream = Stream()
    link = tally_link.Link(stream)
    stream.seek(0)
    stream.truncate()
    link.send_key("A3")
    assert stream.getvalue() == b'{"t":"key","k":"A3"}\n'


def test_send_key_never_raises():
    tally_link.Link(ClosedStream()).send_key("ATTN")
