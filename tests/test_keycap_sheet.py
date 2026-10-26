"""keycap_sheet.py keeps its own copy of the keymap for the printed
inserts; it must match code.py's LAYERS key for key."""
import ast
import pathlib

from fake_macropad import load_code

SHEET = pathlib.Path(__file__).resolve().parent.parent / "keycap_sheet.py"
SHORT = {"COMPACT": "COMPCT"}  # printed in full; the OLED label is at most 6
COLORS = ("RED", "AMBER", "YELLOW", "GREEN", "CYAN", "BLUE", "PURPLE", "MAGENTA", "WHITE")


def sheet_tables():
    """keycap_sheet's DRIVE and FLEET tables, read without importing it
    (it needs reportlab and the DejaVu fonts at import)."""
    tables = {}
    for node in ast.parse(SHEET.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], "id", None)
            if name in ("DRIVE", "FLEET", "ENCODER"):
                tables[name] = ast.literal_eval(node.value)
    return tables


def test_sheet_matches_code_layers(monkeypatch):
    code = load_code(monkeypatch)
    names = {getattr(code, c): c for c in COLORS}
    tables = sheet_tables()
    assert [layer["name"] for layer in code.LAYERS] == ["DRIVE", "FLEET"]
    for layer in code.LAYERS:
        want = [(label, names[color]) for label, color, _ in layer["keys"]]
        got = [(SHORT.get(label, label), role) for label, role, _, _ in tables[layer["name"]]]
        assert got == want, layer["name"]
    assert sorted(tables["ENCODER"]) == ["DRIVE", "FLEET"]
