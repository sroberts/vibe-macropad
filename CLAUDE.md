# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A keypad for driving Claude Code from an Adafruit MacroPad RP2040 (CircuitPython), plus tooling around it. The pad acts only as a USB HID keyboard. It sends keystrokes to Claude Code directly (DRIVE layer) and to the herdr terminal multiplexer through its prefix key (FLEET layer). Pressing the encoder cycles layers.

Work follows GitHub Flow: branch, PR, merge commit on GitHub. Local hooks block commits and pushes on `main`.

## Files and how they relate

- `MacroPad Layout Studio.html`: a self-contained, single-file web app and the **source of truth for the keymap**. You edit layouts in the browser; it saves them to `localStorage`. Its `generate()` function emits `code.py`, and `herdrConfig()` emits the matching herdr `config.toml` snippet.
- `firmware/code.py`: generated firmware. Line 22 holds a `# tally-layout: {...}` JSON comment with the full layout, and the studio's Import button reads it back in. If you hand-edit `LAYERS` in `code.py`, update that JSON line to match. Otherwise the next import/export from the studio loses your edits. If the change belongs in the generator itself (new action types, loop behavior), change the template in `generate()` in the HTML too.
- `firmware/boot.py`: enables the second USB CDC (`data`) serial port for Tally. It runs only after a hard reset or replug, not on a `code.py` auto-reload.
- `keycap_sheet.py`: renders `macropad-keycap-sheet.pdf` (a reference card plus physical keycap inserts) with reportlab. Its `DRIVE`/`FLEET`/`ENCODER` tables are a **separate hand-maintained copy** of the keymap. Keep them in sync with `code.py` when bindings change.
- tally, the host daemon that lights the keys with each herdr agent's state, lives in its own repo (`~/Developer/tally`, github.com/sroberts/tally). Its `docs/design/tally-macropad.md` is the design: the serial protocol (v2 newline-delimited JSON, 512-byte cap), the slot ordering rules and the per-layer lighting tables. Read it before firmware link or lighting work; a protocol change lands in both repos together, and lighting changes go in every client (tally's browser pad, `internal/web/static/lighting.js` in the tally repo, ports `render.py`).

## The pad's side of tally

- `firmware/tally_link.py` reads frames from the USB CDC data port without blocking, answers `ping` with `hello`, and reports link status (`none` before any frame, `live`, `stale` after 15 s).
- `firmware/render.py` is a pure function from (layer, frame, status, held keys, time) to 12 colors, with no hardware imports so it runs under CPython tests. It matches keys **by OLED label** (`A1`–`A6`, `ATTN`, `ENTER`, ...), not position, so rearranging a layout keeps the lighting right. Without a frame it returns the layout's static colors. On DRIVE it lights keys by the focused agent's `fstate` only while live, else static. Held TALK shows full purple. `render.Alert` is the cross-agent alert: it flashes when the count of blocked agents rises, not counting the focused one, and never while TALK is held.
- `firmware/oled.py`: `lines()` is pure (4 status lines, or `None` to keep the label grid before Tally's first frame): space name, state, who is waiting and for how long (`Waits`, timed on the pad), and a slot strip. No key hints: the keycaps carry the labels. `StatusScreen` imports displayio only when built.
- The frame's optional `space` field is the focused agent's herdr workspace `label`.
- `code.py` (and the studio's `generate()` template, which must stay identical in the `primitives` section and from the `display` section down; `tests/test_generator.py` checks) polls the link and repaints about every 33 ms after handling keys.
- Times are integer milliseconds from `time.monotonic_ns()`: CircuitPython floats lose precision as uptime grows.

## Commands

```bash
uv run pytest                        # firmware tests under CPython (tests/)
uv run pytest tests/test_render.py::test_blocked_blinks_at_1hz
go install github.com/sroberts/tally@latest   # tally itself is developed in its own repo
tally status --json | tally frame -  # light the pad from live herdr state, once
tally frame '{"t":"state","v":2,"slots":["N","G","W","R","U",null],"focus":2,"fstate":"G","herdr":true}'

# Regenerate the keycap PDF (args: insert size in mm, output path)
uv run --with reportlab python keycap_sheet.py 12 macropad-keycap-sheet.pdf
```

`tests/conftest.py` appends `firmware/` to `sys.path` rather than prepending it, because `firmware/code.py` would shadow the standard library's `code` module.

In this sandbox git can't read `~/.gitconfig`; prefix git with `GIT_CONFIG_GLOBAL=/dev/null`.

`keycap_sheet.py` needs the DejaVu fonts. It searches the Linux path and then `~/Library/Fonts` and `/Library/Fonts`; on macOS, install them with `brew install --cask font-dejavu`.

Deploy firmware by copying `firmware/*.py` to the root of the `CIRCUITPY` drive; `code.py` imports `render`, `oled` and `tally_link`, so all four (`code.py`, `render.py`, `oled.py`, `tally_link.py`) must be there, along with `boot.py`, which turns on the data port tally talks over (hard reset or replug after copying it). The pad reloads on save. Install the libraries with `circup install -r firmware/requirements.txt` from the repo root, which uses the bundle release pinned under `[tool.circup]` in `pyproject.toml`; a new bundle import goes in `firmware/requirements.txt` (a test checks).

## Firmware constraints

- Key numbers run 0–11, row-major from the top-left (the OLED is at the top). FLEET keys A1–A6 map to herdr `focus_agent` 1–6, which follows herdr's sidebar order.
- OLED labels are at most 6 characters. `build_screen` lays out three labels per row in 21 columns.
- `HERDR_PREFIX` must match `keys.prefix` in `~/.config/herdr/config.toml`. The FLEET bindings also need the herdr config block shown in the comment header of `code.py`.
- `Hold` actions press on key-down and release on key-up. Switching layers calls `kbd.release_all()` so a held key never sticks.
- Per the Tally design, HID responsiveness comes first: the main loop must never block on serial or rendering.
