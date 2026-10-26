"""Stand-ins for the CircuitPython modules firmware/code.py imports, so
CPython can run it. load_code() runs code.py against them and stops its
main loop when the scripted input runs out."""
import importlib.util
import pathlib
import sys
import types

CODE = pathlib.Path(__file__).resolve().parent.parent / "firmware" / "code.py"


class Done(Exception):
    """The script has no more input: leave code.py's main loop."""


class Keycode:
    def __getattr__(self, name):
        return name


class Keyboard:
    def __init__(self, log):
        self.log = log

    def press(self, *keys):
        self.log.append(("press",) + keys)

    def release(self, *keys):
        self.log.append(("release",) + keys)

    def release_all(self):
        self.log.append(("release_all",))


class Layout:
    def __init__(self, log):
        self.log = log

    def write(self, text):
        self.log.append(("write", text))


class Line:
    text = ""


class Screen(list):
    def __init__(self, log, title):
        super().__init__(Line() for _ in range(4))
        self.log, self.title = log, title

    def show(self):
        self.log.append(("screen", self.title))


class Pixels(list):
    def __init__(self, log):
        super().__init__([None] * 12)
        self.log = log

    def show(self):
        self.log.append(("pixels", tuple(self)))


class Event:
    def __init__(self, key_number, pressed):
        self.key_number, self.pressed = key_number, pressed


class Events:
    def __init__(self, pad):
        self.pad = pad

    def get(self):
        if not self.pad.script:
            raise Done
        step = self.pad.script.pop(0)
        return step(self.pad) if callable(step) else step


class Switch:
    def __init__(self):
        self.pressed = False
        self.next = False

    def update(self):
        self.pressed, self.next = self.next, False


class MacroPad:
    """The adafruit_macropad.MacroPad surface code.py uses. script is a list
    of what keys.events.get() returns in turn: an Event, None, or a function
    of the pad (to turn the encoder or press it) returning one of those."""

    script = []

    def __init__(self):
        self.log = []
        self.script = list(MacroPad.script)
        self.Keycode = Keycode()
        self.keyboard = Keyboard(self.log)
        self.keyboard_layout = Layout(self.log)
        self.pixels = Pixels(self.log)
        self.keys = types.SimpleNamespace(events=Events(self))
        self.encoder = 0
        self.encoder_switch_debounced = Switch()
        self.display = types.SimpleNamespace(root_group=None)

    def display_text(self, title):
        return Screen(self.log, title)


def press(n):
    return Event(n, True)


def release(n):
    return Event(n, False)


def turn(by):
    def step(pad):
        pad.encoder += by
    return step


def push(pad):
    pad.encoder_switch_debounced.next = True


def _modules(data):
    label = types.SimpleNamespace(Label=lambda font, **kw: types.SimpleNamespace(**kw))
    group = type("Group", (list,), {})
    return {
        "adafruit_macropad": types.SimpleNamespace(MacroPad=MacroPad),
        "usb_cdc": types.SimpleNamespace(data=data),
        "displayio": types.SimpleNamespace(Group=group),
        "terminalio": types.SimpleNamespace(FONT=None),
        "adafruit_display_text": types.SimpleNamespace(label=label),
        "adafruit_display_text.label": label,
    }


def load_code(monkeypatch, script=(), data=None):
    """Run firmware/code.py until script is used up; return its module."""
    for name, module in _modules(data).items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(MacroPad, "script", list(script))
    spec = importlib.util.spec_from_file_location("firmware_code", CODE)
    code = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(code)
    except Done:
        pass
    return code
