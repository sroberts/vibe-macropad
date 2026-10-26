"""firmware/requirements.txt lists every bundle library the firmware imports."""
import ast
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ROOT / "firmware"
CORE = {"displayio", "json", "math", "terminalio", "time", "usb_cdc"}  # built into CircuitPython


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_requirements_cover_the_firmware_imports():
    local = {p.stem for p in FIRMWARE.glob("*.py")}
    needed = {m for p in FIRMWARE.glob("*.py") for m in imports(p)} - local - CORE
    lines = (FIRMWARE / "requirements.txt").read_text().splitlines()
    listed = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
    assert needed == listed


def test_bundle_release_is_pinned():
    pinned = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["circup"]["bundle-versions"]
    tag = pinned["adafruit/Adafruit_CircuitPython_Bundle"]  # circup's key for the bundle
    assert tag.isdigit() and len(tag) == 8  # a release tag, YYYYMMDD
