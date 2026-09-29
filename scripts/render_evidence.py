"""Render real command output as a terminal-style PNG for submission/evidence.

    python -m pytest -q | python scripts/render_evidence.py --title "python -m pytest -q" --out submission/evidence/01-pytest.png

Reads the output from stdin (or --input), so the image shows exactly what the command printed.
JSON lines can be pretty-printed with --pretty-json to stay readable at screenshot size.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [r"C:\Windows\Fonts\CascadiaMono.ttf", r"C:\Windows\Fonts\consola.ttf", "DejaVuSansMono.ttf"]
BACKGROUND = (24, 24, 27)
FOREGROUND = (228, 228, 231)
PROMPT = (134, 239, 172)
MUTED = (161, 161, 170)
WRAP_AT = 150


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def expand(lines: list[str], pretty_json: bool) -> list[str]:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if pretty_json and stripped.startswith("{") and stripped.endswith("}"):
            try:
                out.extend(json.dumps(json.loads(stripped), indent=2, ensure_ascii=False).splitlines())
                continue
            except json.JSONDecodeError:
                pass
        out.extend(textwrap.wrap(line, WRAP_AT, drop_whitespace=False) or [""])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--title", required=True, help="The command that produced the output")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--pretty-json", action="store_true")
    args = parser.parse_args()

    raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.buffer.read().decode("utf-8", "replace")
    body = expand(raw.rstrip("\n").splitlines(), args.pretty_json)

    font = load_font(18)
    line_height = 24
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = [(f"$ {args.title}", PROMPT)]
    footer = [("", FOREGROUND), (f"# rendered from the command's own output at {stamp}", MUTED)]
    rows = header + [(line, FOREGROUND) for line in body] + footer

    width = max(900, int(max(font.getlength(text) for text, _ in rows)) + 48)
    image = Image.new("RGB", (width, line_height * len(rows) + 40), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for index, (text, color) in enumerate(rows):
        draw.text((24, 20 + index * line_height), text, font=font, fill=color)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"Wrote {args.out} ({len(body)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
