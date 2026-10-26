"""MacroPad Layout Studio's generate() template must stay identical to
firmware/code.py wherever the template has no substitutions, or the next
export from the studio silently undoes a hand edit to code.py."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
STUDIO = ROOT / "MacroPad Layout Studio.html"
CODE = ROOT / "firmware" / "code.py"

MARK = "# " + "-" * 64 + " "


def template():
    html = STUDIO.read_text()
    body = html[html.index("function generate()"):]
    start = body.index("return `") + len("return `")
    end = body.index("\n`;", start) + 1
    return body[start:end]


def section(text, name, until=None):
    """From the named section marker to the next named one, or the end."""
    start = text.index(MARK + name + "\n")
    end = text.index(MARK + until + "\n", start) if until else len(text)
    return text[start:end]


def literal(text):
    """A JS template literal's text with no substitutions or escapes is its value."""
    assert "${" not in text and "\\" not in text and "`" not in text
    return text


def test_primitives_match_the_template():
    assert literal(section(template(), "primitives", "layers")) == section(CODE.read_text(), "primitives", "layers")


def test_display_and_main_loop_match_the_template():
    assert literal(section(template(), "display")) == section(CODE.read_text(), "display")


def test_template_header_matches_up_to_its_substitutions():
    """Everything above the layers, with each ${...} as a wildcard."""
    head = template()[:template().index(MARK + "layers\n")]
    parts = re.split(r"\$\{[^`]*?\}(?=\n|   )", head)
    pattern = "".join(re.escape(p) for p in parts[:1]) + "".join(".*?" + re.escape(p) for p in parts[1:])
    code = CODE.read_text()
    assert re.fullmatch(pattern, code[:code.index(MARK + "layers\n")], re.S)
