#!/usr/bin/env python3
"""color_svg.py.

Inspects, validates, and substitutes colors in SVG vector graphics.

Features:
  1. Display Colors:
     Extracts all unique colors used in an SVG file, normalizes them to RGB
     hex format (#RRGGBB), counts their occurrences across presentation
     attributes, inline styles, and <style> blocks, and provides a comment
     identifying the color name or general shade.

  2. Palette Validation:
     Validates all colors in the SVG against an allowed palette (provided
     as a file, comma-separated list, or official ECU palette preset).
     Fails with exit code 1 if any non-palette color is detected.

  3. Color Replacement / Substitution:
     Finds specified RGB hex colors and substitutes them with target values
     across all attributes, inline styles, and embedded stylesheets while
     preserving original XML formatting, indentation, and namespaces.
     Supports dry-run mode (--dry-run) to preview planned changes.

Usage Examples:
  # Display colors in an SVG with counts and shade comments:
  python3 tools/color_svg.py logo.svg

  # Output as JSON:
  python3 tools/color_svg.py logo.svg --json

  # Validate against official ECU brand colors:
  python3 tools/color_svg.py logo.svg --validate --palette official

  # Validate against a custom palette file or list:
  python3 tools/color_svg.py logo.svg --validate --palette tools/palette.txt
  python3 tools/color_svg.py logo.svg --validate --palette "#582C83,#FFC700,#000000,#FFFFFF"

  # Preview color substitution (dry-run):
  python3 tools/color_svg.py logo.svg --replace "#2F2976" "#582C83" --dry-run

  # Replace colors and save to a new file:
  python3 tools/color_svg.py logo.svg -r "#2F2976" "#582C83" -o logo-fixed.svg

  # Replace colors in-place:
  python3 tools/color_svg.py logo.svg -r "#2F2976" "#582C83" -r "#FDD50E" "#FFC700" -i
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple

from lxml import etree

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"

# Standard SVG presentation attributes that define paint / color
COLOR_ATTRIBUTES = frozenset(
    {"fill", "stroke", "stop-color", "flood-color", "lighting-color", "color"}
)

# Authoritative ECU Trademark Licensing Palette (reference: OFFICIAL_COLORS.md)
OFFICIAL_ECU_COLORS: dict[str, str] = {
    "#582C83": "ECU Purple (PMS 268 C/U)",
    "#FFC700": "ECU Gold - Uncoated (PMS 109 U)",
    "#FFC72C": "ECU Gold - Coated (PMS 123 C)",
    "#000000": "Black (Process Black C)",
    "#FFFFFF": "White",
    "#D3A985": "Beige / Skin Tone (PMS 728 C/U)",
    "#9D2235": "Red / Crimson (PMS 201 C)",
}

# Standard CSS3 / SVG 1.1 Named Colors (148 colors)
CSS_NAMED_COLORS: dict[str, str] = {
    "aliceblue": "#F0F8FF",
    "antiquewhite": "#FAEBD7",
    "aqua": "#00FFFF",
    "aquamarine": "#7FFFD4",
    "azure": "#F0FFFF",
    "beige": "#F5F5DC",
    "bisque": "#FFE4C4",
    "black": "#000000",
    "blanchedalmond": "#FFEBCD",
    "blue": "#0000FF",
    "blueviolet": "#8A2BE2",
    "brown": "#A52A2A",
    "burlywood": "#DEB887",
    "cadetblue": "#5F9EA0",
    "chartreuse": "#7FFF00",
    "chocolate": "#D2691E",
    "coral": "#FF7F50",
    "cornflowerblue": "#6495ED",
    "cornsilk": "#FFF8DC",
    "crimson": "#DC143C",
    "cyan": "#00FFFF",
    "darkblue": "#00008B",
    "darkcyan": "#008B8B",
    "darkgoldenrod": "#B8860B",
    "darkgray": "#A9A9A9",
    "darkgreen": "#006400",
    "darkgrey": "#A9A9A9",
    "darkkhaki": "#BDB76B",
    "darkmagenta": "#8B008B",
    "darkolivegreen": "#556B2F",
    "darkorange": "#FF8C00",
    "darkorchid": "#9932CC",
    "darkred": "#8B0000",
    "darksalmon": "#E9967A",
    "darkseagreen": "#8FBC8F",
    "darkslateblue": "#483D8B",
    "darkslategray": "#2F4F4F",
    "darkslategrey": "#2F4F4F",
    "darkturquoise": "#00CED1",
    "darkviolet": "#9400D3",
    "deeppink": "#FF1493",
    "deepskyblue": "#00BFFF",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1E90FF",
    "firebrick": "#B22222",
    "floralwhite": "#FFFAF0",
    "forestgreen": "#228B22",
    "fuchsia": "#FF00FF",
    "gainsboro": "#DCDCDC",
    "ghostwhite": "#F8F8FF",
    "gold": "#FFD700",
    "goldenrod": "#DAA520",
    "gray": "#808080",
    "green": "#008000",
    "greenyellow": "#ADFF2F",
    "grey": "#808080",
    "honeydew": "#F0FFF0",
    "hotpink": "#FF69B4",
    "indianred": "#CD5C5C",
    "indigo": "#4B0082",
    "ivory": "#FFFFF0",
    "khaki": "#F0E68C",
    "lavender": "#E6E6FA",
    "lavenderblush": "#FFF0F5",
    "lawngreen": "#7CFC00",
    "lemonchiffon": "#FFFACD",
    "lightblue": "#ADD8E6",
    "lightcoral": "#F08080",
    "lightcyan": "#E0FFFF",
    "lightgoldenrodyellow": "#FAFAD2",
    "lightgray": "#D3D3D3",
    "lightgreen": "#90EE90",
    "lightgrey": "#D3D3D3",
    "lightpink": "#FFB6C1",
    "lightsalmon": "#FFA07A",
    "lightseagreen": "#20B2AA",
    "lightskyblue": "#87CEFA",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#B0C4DE",
    "lightyellow": "#FFFFE0",
    "lime": "#00FF00",
    "limegreen": "#32CD32",
    "linen": "#FAF0E6",
    "magenta": "#FF00FF",
    "maroon": "#800000",
    "mediumaquamarine": "#66CDAA",
    "mediumblue": "#0000CD",
    "mediumorchid": "#BA55D3",
    "mediumpurple": "#9370DB",
    "mediumseagreen": "#3CB371",
    "mediumslateblue": "#7B68EE",
    "mediumspringgreen": "#00FA9A",
    "mediumturquoise": "#48D1CC",
    "mediumvioletred": "#C71585",
    "midnightblue": "#191970",
    "mintcream": "#F5FFFA",
    "mistyrose": "#FFE4E1",
    "moccasin": "#FFE4B5",
    "navajowhite": "#FFDEAD",
    "navy": "#000080",
    "oldlace": "#FDF5E6",
    "olive": "#808000",
    "olivedrab": "#6B8E23",
    "orange": "#FFA500",
    "orangered": "#FF4500",
    "orchid": "#DA70D6",
    "palegoldenrod": "#EEE8AA",
    "palegreen": "#98FB98",
    "paleturquoise": "#AFEEEE",
    "palevioletred": "#DB7093",
    "papayawhip": "#FFEFD5",
    "peachpuff": "#FFDAB9",
    "peru": "#CD853F",
    "pink": "#FFC0CB",
    "plum": "#DDA0DD",
    "powderblue": "#B0E0E6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#FF0000",
    "rosybrown": "#BC8F8F",
    "royalblue": "#4169E1",
    "saddlebrown": "#8B4513",
    "salmon": "#FA8072",
    "sandybrown": "#F4A460",
    "seagreen": "#2E8B57",
    "seashell": "#FFF5EE",
    "sienna": "#A0522D",
    "silver": "#C0C0C0",
    "skyblue": "#87CEEB",
    "slateblue": "#6A5ACD",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#FFFAFA",
    "springgreen": "#00FF7F",
    "steelblue": "#4682B4",
    "tan": "#D2B48C",
    "teal": "#008080",
    "thistle": "#D8BFD8",
    "tomato": "#FF6347",
    "turquoise": "#40E0D0",
    "violet": "#EE82EE",
    "wheat": "#F5DEB3",
    "white": "#FFFFFF",
    "whitesmoke": "#F5F5F5",
    "yellow": "#FFFF00",
    "yellowgreen": "#9ACD32",
}

CSS_HEX_TO_NAME: dict[str, str] = {
    hex_val.upper(): name.capitalize() for name, hex_val in CSS_NAMED_COLORS.items()
}


class ColorOccurrence(NamedTuple):
    """Detailed location record for a color usage in an SVG document."""

    color_hex: str
    raw_value: str
    property_name: str
    element_tag: str
    element_id: str
    element_label: str
    line_number: int


def parse_color(val: str | None) -> str | None:
    """Parses any SVG/CSS color representation into normalized uppercase #RRGGBB.

    Supported inputs:
      - 3, 4, 6, 8 digit hex codes (#RGB, #RGBA, #RRGGBB, #RRGGBBAA, or without #)
      - rgb(r, g, b) or rgba(r, g, b, a) with integers or percentages
      - hsl(h, s, l) or hsla(h, s, l, a)
      - CSS named colors (e.g. 'black', 'white', 'purple', 'gold')

    Returns None for non-color values like 'none', 'transparent', 'currentColor',
    'inherit', 'url(...)', or invalid syntax.
    """
    if not val:
        return None

    cleaned = val.strip().strip("\"'").strip()
    if not cleaned:
        return None

    lower = cleaned.lower()
    if lower in ("none", "transparent", "currentcolor", "inherit") or lower.startswith("url("):
        return None

    # 1. Named CSS colors
    if lower in CSS_NAMED_COLORS:
        return CSS_NAMED_COLORS[lower].upper()

    # 2. Hex values (#RGB, #RGBA, #RRGGBB, #RRGGBBAA, or bare hex)
    hex_match = re.match(r"^#?([0-9a-fA-F]{3,8})$", cleaned)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            return f"#{digits[0] * 2}{digits[1] * 2}{digits[2] * 2}".upper()
        if len(digits) in (6, 8):
            return f"#{digits[:6]}".upper()

    # 3. rgb(...) / rgba(...)
    rgb_match = re.match(r"^rgba?\s*\(\s*([^)]+)\s*\)$", cleaned, re.I)
    if rgb_match:
        parts = [p.strip() for p in rgb_match.group(1).split(",") if p.strip()]
        if len(parts) >= 3:
            rgb_vals = []
            for p in parts[:3]:
                num = float(p[:-1]) * 2.55 if p.endswith("%") else float(p)
                rgb_vals.append(max(0, min(255, round(num))))
            return f"#{rgb_vals[0]:02X}{rgb_vals[1]:02X}{rgb_vals[2]:02X}"

    # 4. hsl(...) / hsla(...)
    hsl_match = re.match(r"^hsla?\s*\(\s*([^)]+)\s*\)$", cleaned, re.I)
    if hsl_match:
        parts = [p.strip() for p in hsl_match.group(1).split(",") if p.strip()]
        if len(parts) >= 3:
            hue = float(parts[0].replace("deg", "")) % 360.0 / 360.0
            sat = float(parts[1].rstrip("%")) / 100.0
            light = float(parts[2].rstrip("%")) / 100.0
            r_flt, g_flt, b_flt = colorsys.hls_to_rgb(hue, light, sat)
            r_int = max(0, min(255, round(r_flt * 255)))
            g_int = max(0, min(255, round(g_flt * 255)))
            b_int = max(0, min(255, round(b_flt * 255)))
            return f"#{r_int:02X}{g_int:02X}{b_int:02X}"

    return None


def get_nearest_css_name(hex_code: str) -> tuple[str, float]:
    """Finds the nearest named CSS color using human-perception weighted RGB distance."""
    r1 = int(hex_code[1:3], 16)
    g1 = int(hex_code[3:5], 16)
    b1 = int(hex_code[5:7], 16)

    best_name = "Black"
    best_dist = float("inf")

    for name, hex_val in CSS_NAMED_COLORS.items():
        r2 = int(hex_val[1:3], 16)
        g2 = int(hex_val[3:5], 16)
        b2 = int(hex_val[5:7], 16)
        dr = r1 - r2
        dg = g1 - g2
        db = b1 - b2
        # Weighted Euclidean distance approximating human eye sensitivity
        dist = 2 * (dr**2) + 4 * (dg**2) + 3 * (db**2)
        if dist < best_dist:
            best_dist = dist
            best_name = name.capitalize()

    return best_name, best_dist


def get_color_shade(hex_code: str) -> str:
    """Classifies an RGB hex color into a human-readable general color shade or family."""
    r = int(hex_code[1:3], 16)
    g = int(hex_code[3:5], 16)
    b = int(hex_code[5:7], 16)

    h, light, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    hue_deg = h * 360.0

    # Grayscale / Achromatic
    if sat < 0.10 or light <= 0.05 or light >= 0.95:
        if light <= 0.05:
            return "Black"
        if light <= 0.15:
            return "Near Black"
        if light <= 0.30:
            return "Very Dark Gray"
        if light <= 0.45:
            return "Dark Gray"
        if light <= 0.60:
            return "Gray"
        if light <= 0.75:
            return "Light Gray"
        if light <= 0.92:
            return "Very Light Gray"
        return "White"

    # Earth tones
    if 15 <= hue_deg <= 45 and 0.12 <= light <= 0.45 and sat >= 0.15:
        return "Dark Brown" if light < 0.25 else "Brown"
    if 25 <= hue_deg <= 50 and 0.55 <= light <= 0.85 and 0.15 <= sat <= 0.75:
        return "Warm Tan / Beige"
    if 60 <= hue_deg <= 90 and 0.15 <= light <= 0.45 and sat >= 0.15:
        return "Olive"

    # Hue classification
    if hue_deg < 15 or hue_deg >= 345:
        base = "Pink" if light > 0.7 else "Red"
    elif hue_deg < 25:
        base = "Red-Orange"
    elif hue_deg < 42:
        base = "Orange"
    elif hue_deg < 55:
        base = "Gold / Amber"
    elif hue_deg < 70:
        base = "Yellow"
    elif hue_deg < 85:
        base = "Lime / Yellow-Green"
    elif hue_deg < 155:
        base = "Green"
    elif hue_deg < 175:
        base = "Teal"
    elif hue_deg < 195:
        base = "Cyan / Aqua"
    elif hue_deg < 220:
        base = "Sky Blue"
    elif hue_deg < 255:
        base = "Blue"
    elif hue_deg < 268:
        base = "Indigo / Blue-Violet"
    elif hue_deg < 315:
        base = "Purple / Violet"
    elif hue_deg < 335:
        base = "Magenta / Fuchsia"
    else:
        base = "Rose / Pink"

    # Tone modifiers
    prefix = ""
    if light < 0.28:
        prefix = "Dark "
    elif light > 0.75:
        prefix = "Light "
    elif sat < 0.35:
        prefix = "Muted "
    elif sat > 0.80 and 0.35 <= light <= 0.65:
        prefix = "Vivid "

    return f"{prefix}{base}".strip()


def get_color_comment(hex_code: str) -> str:
    """Generates an informative comment describing the color name, brand label, or shade."""
    hex_code = hex_code.upper()
    shade = get_color_shade(hex_code)
    official = OFFICIAL_ECU_COLORS.get(hex_code)
    exact_css = CSS_HEX_TO_NAME.get(hex_code)

    if official:
        shade_words = [w for w in re.split(r"[\s/]+", shade.lower()) if len(w) > 3]
        if any(w in official.lower() for w in shade_words) or shade.lower() in official.lower():
            return official
        return f"{official} ({shade})"

    if exact_css:
        if exact_css.lower() == shade.lower():
            return exact_css
        return f"{exact_css} ({shade})"

    nearest_css, distance = get_nearest_css_name(hex_code)
    # If nearest CSS color is relatively close (distance < 5000), mention it
    if distance < 5000 and nearest_css.lower() != shade.lower():
        return f"{shade} (nearest: {nearest_css})"

    return shade


def extract_colors_from_svg(
    svg_path: Path | str,
) -> tuple[Counter[str], list[ColorOccurrence]]:
    """Scans an SVG file to extract all color occurrences and their occurrence counts.

    Returns:
      A tuple of (color_counts, occurrence_list).
    """
    path_obj = Path(svg_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"SVG file not found: '{svg_path}'")

    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    tree = etree.parse(str(path_obj), parser)

    counts: Counter[str] = Counter()
    occurrences: list[ColorOccurrence] = []

    for elem in tree.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else str(elem.tag)
        elem_id = elem.get("id") or ""
        elem_label = (
            elem.get(f"{{{INKSCAPE_NS}}}label")
            or elem.get("label")
            or elem.get(f"{{{SODIPODI_NS}}}label")
            or ""
        )
        line_num = elem.sourceline or 0

        # 1. Presentation attributes
        for attr in COLOR_ATTRIBUTES:
            val = elem.get(attr)
            if val:
                norm = parse_color(val)
                if norm:
                    counts[norm] += 1
                    occurrences.append(
                        ColorOccurrence(
                            color_hex=norm,
                            raw_value=val,
                            property_name=attr,
                            element_tag=tag,
                            element_id=elem_id,
                            element_label=elem_label,
                            line_number=line_num,
                        )
                    )

        # 2. Inline style attribute
        style_val = elem.get("style")
        if style_val:
            for decl in style_val.split(";"):
                if ":" in decl:
                    prop, prop_val = decl.split(":", 1)
                    prop_name = prop.strip().lower()
                    if prop_name in COLOR_ATTRIBUTES:
                        norm = parse_color(prop_val)
                        if norm:
                            counts[norm] += 1
                            occurrences.append(
                                ColorOccurrence(
                                    color_hex=norm,
                                    raw_value=prop_val.strip(),
                                    property_name=f"style:{prop_name}",
                                    element_tag=tag,
                                    element_id=elem_id,
                                    element_label=elem_label,
                                    line_number=line_num,
                                )
                            )

        # 3. Embedded <style> element CSS rules
        if tag == "style" and elem.text:
            css_text = elem.text
            css_decl_re = re.compile(
                r"\b(fill|stroke|stop-color|flood-color|lighting-color|color)\s*:\s*([^;}\s]+)",
                re.I,
            )
            for m in css_decl_re.finditer(css_text):
                prop_name = m.group(1).lower()
                raw_val = m.group(2).strip()
                norm = parse_color(raw_val)
                if norm:
                    counts[norm] += 1
                    occurrences.append(
                        ColorOccurrence(
                            color_hex=norm,
                            raw_value=raw_val,
                            property_name=f"css:{prop_name}",
                            element_tag="style",
                            element_id=elem_id,
                            element_label=elem_label,
                            line_number=line_num,
                        )
                    )

    return counts, occurrences


def load_palette(palette_arg: str | None = None) -> set[str]:
    """Loads a set of allowed color hex values from a file, comma-separated list, or preset.

    If palette_arg is None:
      Looks for tools/palette.txt relative to this script; if absent, defaults
      to the official ECU trademark licensing palette.
    """
    script_dir = Path(__file__).resolve().parent

    # Special presets
    if palette_arg in (None, "", "official", "ecu"):
        if palette_arg in ("official", "ecu"):
            return set(OFFICIAL_ECU_COLORS.keys())

        # Check default palette file
        default_file = script_dir / "palette.txt"
        if default_file.is_file():
            return parse_palette_file(default_file)

        return set(OFFICIAL_ECU_COLORS.keys())

    # Check if palette_arg is an existing file
    potential_path = Path(palette_arg)
    if potential_path.is_file():
        return parse_palette_file(potential_path)

    # Otherwise treat as comma or whitespace separated list of colors
    colors: set[str] = set()
    tokens = re.split(r"[,;\s]+", palette_arg.strip())
    for token in tokens:
        if token:
            norm = parse_color(token)
            if norm:
                colors.add(norm)
            else:
                raise ValueError(f"Invalid color specification in palette: '{token}'")

    if not colors:
        raise ValueError(f"No valid colors found in palette specification: '{palette_arg}'")

    return colors


def parse_palette_file(file_path: Path) -> set[str]:
    """Reads a palette file, parsing hex colors while ignoring comments and empty lines."""
    colors: set[str] = set()
    text = file_path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue
        # Extract potential hex color token from line
        # e.g. '#582C83 # ECU Purple' or '#582C83'
        tokens = line.split()
        if tokens:
            first = tokens[0]
            norm = parse_color(first)
            if norm:
                colors.add(norm)

    if not colors:
        raise ValueError(f"No valid colors parsed from palette file: '{file_path}'")

    return colors


def validate_colors(
    identified_colors: Counter[str] | dict[str, int] | set[str],
    allowed_palette: set[str],
) -> list[str]:
    """Compares identified colors against the allowed palette and returns violating hex codes."""
    violating: list[str] = []
    for color in identified_colors:
        norm = parse_color(color)
        if norm and norm not in allowed_palette:
            violating.append(norm)
    return sorted(violating)


def replace_colors_in_svg(
    svg_content: str,
    replacements: dict[str, str],
) -> tuple[str, int]:
    """Substitutes colors in an SVG document while preserving formatting and namespaces.

    Single-pass substitution maps any occurrence matching an old normalized
    color to its replacement value.
    """
    normalized_map = {}
    for old_c, new_c in replacements.items():
        old_norm = parse_color(old_c)
        new_norm = parse_color(new_c)
        if not old_norm:
            raise ValueError(f"Invalid search color: '{old_c}'")
        if not new_norm:
            raise ValueError(f"Invalid replacement color: '{new_c}'")
        normalized_map[old_norm] = new_norm

    total_replacements = 0

    def repl_attr(m: re.Match[str]) -> str:
        nonlocal total_replacements
        attr = m.group(1)
        q = m.group(2)
        val = m.group(3)
        norm = parse_color(val)
        if norm in normalized_map:
            total_replacements += 1
            return f"{attr}={q}{normalized_map[norm]}{q}"
        return m.group(0)

    def repl_style_decl(m: re.Match[str]) -> str:
        nonlocal total_replacements
        prop = m.group(1)
        colon = m.group(2)
        val = m.group(3)
        norm = parse_color(val)
        if norm in normalized_map:
            total_replacements += 1
            return f"{prop}{colon}{normalized_map[norm]}"
        return m.group(0)

    def repl_style_attr(m: re.Match[str]) -> str:
        prefix = m.group(1)
        q = m.group(2)
        val = m.group(3)
        new_val = re.sub(
            r"\b(fill|stroke|stop-color|flood-color|lighting-color|color)(\s*:\s*)([^;\"\'\s]+)",
            repl_style_decl,
            val,
            flags=re.I,
        )
        return f"{prefix}{q}{new_val}{q}"

    def repl_style_tag(m: re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        close_tag = m.group(3)
        new_content = re.sub(
            r"\b(fill|stroke|stop-color|flood-color|lighting-color|color)(\s*:\s*)([^;}\s]+)",
            repl_style_decl,
            content,
            flags=re.I,
        )
        return f"{open_tag}{new_content}{close_tag}"

    # 1. Replace presentation attributes
    attr_re = re.compile(
        r"\b(fill|stroke|stop-color|flood-color|lighting-color|color)\s*=\s*(['\"])(.*?)\2",
        re.I,
    )
    result = attr_re.sub(repl_attr, svg_content)

    # 2. Replace declarations in inline style attributes
    style_re = re.compile(r"(\bstyle\s*=\s*)(['\"])(.*?)\2", re.I)
    result = style_re.sub(repl_style_attr, result)

    # 3. Replace declarations inside <style> blocks
    style_tag_re = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.I | re.S)
    result = style_tag_re.sub(repl_style_tag, result)

    return result, total_replacements


def plan_replacements(
    occurrences: list[ColorOccurrence],
    replacements: dict[str, str],
) -> dict[str, list[ColorOccurrence]]:
    """Groups occurrences that match any planned color replacement."""
    normalized_map: dict[str, str] = {}
    for old_c, new_c in replacements.items():
        old_norm = parse_color(old_c)
        new_norm = parse_color(new_c)
        if old_norm and new_norm:
            normalized_map[old_norm] = new_norm

    planned: dict[str, list[ColorOccurrence]] = defaultdict(list)
    for occ in occurrences:
        if occ.color_hex in normalized_map:
            planned[occ.color_hex].append(occ)

    return planned


def format_table(
    counts: Counter[str],
    sort_by: str = "count",
    reverse: bool = False,
    no_header: bool = False,
) -> str:
    """Formats the extracted colors as a clean, human-readable table with comments."""
    items = list(counts.items())

    if sort_by == "hex":
        items.sort(key=lambda x: x[0], reverse=reverse)
    elif sort_by == "name":
        items.sort(key=lambda x: get_color_comment(x[0]), reverse=reverse)
    else:  # default: count descending, then hex ascending
        items.sort(key=lambda x: (-x[1] if not reverse else x[1], x[0]))

    lines = []
    if not no_header:
        lines.append(f"{'HEX COLOR':<10} {'COUNT':>6}  {'SHADE / NAME'}")
        lines.append("-" * 65)

    for hex_val, count in items:
        comment = get_color_comment(hex_val)
        lines.append(f"{hex_val:<10} {count:>6}  # {comment}")

    return "\n".join(lines)


def format_json_output(
    counts: Counter[str],
    occurrences: list[ColorOccurrence] | None = None,
    include_details: bool = False,
) -> str:
    """Formats color extraction results as structured JSON."""
    data = []
    occ_by_color = defaultdict(list)
    if occurrences and include_details:
        for occ in occurrences:
            occ_by_color[occ.color_hex].append(
                {
                    "raw_value": occ.raw_value,
                    "property": occ.property_name,
                    "element_tag": occ.element_tag,
                    "element_id": occ.element_id,
                    "element_label": occ.element_label,
                    "line_number": occ.line_number,
                }
            )

    for hex_val, count in counts.most_common():
        item = {
            "hex": hex_val,
            "count": count,
            "shade": get_color_shade(hex_val),
            "comment": get_color_comment(hex_val),
            "official_match": OFFICIAL_ECU_COLORS.get(hex_val),
            "exact_css_match": CSS_HEX_TO_NAME.get(hex_val),
        }
        if include_details:
            item["occurrences"] = occ_by_color.get(hex_val, [])
        data.append(item)

    return json.dumps(data, indent=2)


def build_parser() -> argparse.ArgumentParser:
    """Builds and returns the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Display, validate, and substitute colors in SVG vector graphics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s logo.svg
  %(prog)s logo.svg --validate --palette official
  %(prog)s logo.svg --replace "#2F2976" "#582C83" --dry-run
  %(prog)s logo.svg -r "#2F2976" "#582C83" -r "#FDD50E" "#FFC700" -i
""",
    )

    parser.add_argument(
        "svg_files",
        nargs="+",
        help="One or more SVG file paths to inspect or modify.",
    )

    display_group = parser.add_argument_group("Display Options")
    display_group.add_argument(
        "--sort",
        choices=["count", "hex", "name"],
        default="count",
        help="Sort colors by occurrence count (default), hex code, or shade name.",
    )
    display_group.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse the sort order.",
    )
    display_group.add_argument(
        "--no-header",
        action="store_true",
        help="Omit table header and borders (plain output for scripting).",
    )
    display_group.add_argument(
        "--details",
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed element tags, IDs, labels, and line numbers for each color.",
    )
    display_group.add_argument(
        "--json",
        action="store_true",
        help="Output color analysis as structured JSON.",
    )

    val_group = parser.add_argument_group("Validation Options")
    val_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate that all identified colors are members of an approved palette list.",
    )
    val_group.add_argument(
        "-p",
        "--palette",
        "--palette-file",
        dest="palette",
        default=None,
        help="Approved palette list: path to palette file, comma-separated hex values, or 'official'.",
    )

    rep_group = parser.add_argument_group("Color Replacement / Substitution Options")
    rep_group.add_argument(
        "-r",
        "--replace",
        nargs=2,
        action="append",
        metavar=("FIND", "REPLACE"),
        help="Substitute FIND color with REPLACE color. Can be specified multiple times.",
    )
    rep_group.add_argument(
        "--find",
        dest="find_color",
        help="Color to find (paired with --replace-with).",
    )
    rep_group.add_argument(
        "--replace-with",
        dest="replace_with_color",
        help="Color to substitute in place of --find.",
    )
    rep_group.add_argument(
        "-o",
        "--output",
        help="Output SVG file path for modified document. Requires single input SVG file.",
    )
    rep_group.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Modify SVG file(s) in-place directly on disk.",
    )
    rep_group.add_argument(
        "-d",
        "-n",
        "--dry-run",
        action="store_true",
        help="Preview planned substitutions and occurrences without modifying files on disk.",
    )

    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    # Collect replacements
    replacements: dict[str, str] = {}
    if args.replace:
        for find_val, rep_val in args.replace:
            replacements[find_val] = rep_val
    if args.find_color and args.replace_with_color:
        replacements[args.find_color] = args.replace_with_color
    elif (args.find_color and not args.replace_with_color) or (
        args.replace_with_color and not args.find_color
    ):
        parser.error("Both --find and --replace-with must be specified together.")

    # Validate output options
    if args.output and len(args.svg_files) > 1:
        parser.error("-o/--output can only be specified when a single SVG file is provided.")
    if args.output and args.in_place:
        parser.error("Cannot combine -o/--output with -i/--in-place.")

    # Auto-activate validation if --palette is passed without replacement
    is_validation = args.validate or (args.palette is not None and not replacements)

    # Determine if replacement is requested
    is_replacement = bool(replacements)

    # If replacement requested without -o, -i, or --dry-run, default to dry-run safely
    implicit_dry_run = False
    if is_replacement and not args.output and not args.in_place and not args.dry_run:
        args.dry_run = True
        implicit_dry_run = True

    overall_exit_code = 0

    for svg_file_path in args.svg_files:
        path_obj = Path(svg_file_path)
        if not path_obj.is_file():
            print(f"Error: File '{svg_file_path}' not found.", file=sys.stderr)
            overall_exit_code = 1
            continue

        try:
            counts, occurrences = extract_colors_from_svg(path_obj)
        except Exception as e:
            print(f"Error parsing '{svg_file_path}': {e}", file=sys.stderr)
            overall_exit_code = 1
            continue

        # Header banner if processing multiple files
        if len(args.svg_files) > 1 and not args.json:
            print(f"\n=== {svg_file_path} ===")

        # -------------------------------------------------------------
        # Mode 1: Validation Mode
        # -------------------------------------------------------------
        if is_validation:
            try:
                allowed_palette = load_palette(args.palette)
            except Exception as e:
                print(f"Error loading palette: {e}", file=sys.stderr)
                return 1

            violating = validate_colors(counts, allowed_palette)
            if violating:
                print(
                    f"Validation FAILED for '{svg_file_path}': "
                    f"{len(violating)} violating color(s) not in palette:",
                    file=sys.stderr,
                )
                for v_hex in violating:
                    comment = get_color_comment(v_hex)
                    print(
                        f"  - {v_hex} (count: {counts[v_hex]})  # {comment}",
                        file=sys.stderr,
                    )
                    if args.details:
                        matching_occs = [o for o in occurrences if o.color_hex == v_hex]
                        for occ in matching_occs:
                            id_str = f' id="{occ.element_id}"' if occ.element_id else ""
                            lbl_str = f' label="{occ.element_label}"' if occ.element_label else ""
                            print(
                                f"      Line {occ.line_number}: <{occ.element_tag}{id_str}{lbl_str}> "
                                f"property '{occ.property_name}' (raw: {occ.raw_value})",
                                file=sys.stderr,
                            )
                overall_exit_code = 1
            else:
                total_color_uses = sum(counts.values())
                print(
                    f"Validation PASSED: All {len(counts)} color(s) ({total_color_uses} total occurrences) "
                    f"in '{svg_file_path}' match the approved palette."
                )

        # -------------------------------------------------------------
        # Mode 2: Replacement Mode (with Dry-Run support)
        # -------------------------------------------------------------
        elif is_replacement:
            try:
                planned = plan_replacements(occurrences, replacements)
            except Exception as e:
                print(f"Error planning color replacement: {e}", file=sys.stderr)
                overall_exit_code = 1
                continue

            normalized_replacements: dict[str, str] = {}
            for old_c, new_c in replacements.items():
                old_norm = parse_color(old_c)
                new_norm = parse_color(new_c)
                if old_norm and new_norm:
                    normalized_replacements[old_norm] = new_norm

            total_planned_occurrences = sum(len(occs) for occs in planned.values())

            if args.dry_run:
                print(f"[Dry Run] Color replacement plan for '{svg_file_path}':")
                if not planned:
                    print("  No occurrences of the specified search colors were found.")
                else:
                    for old_hex, new_hex in normalized_replacements.items():
                        occs = planned.get(old_hex, [])
                        old_desc = get_color_comment(old_hex)
                        new_desc = get_color_comment(new_hex)
                        print(
                            f"  {old_hex} ({old_desc}) -> {new_hex} ({new_desc}): {len(occs)} occurrence(s)"
                        )
                        for occ in occs:
                            id_str = f' id="{occ.element_id}"' if occ.element_id else ""
                            lbl_str = f' label="{occ.element_label}"' if occ.element_label else ""
                            print(
                                f"    - Line {occ.line_number}: <{occ.element_tag}{id_str}{lbl_str}> "
                                f"property '{occ.property_name}' ({occ.raw_value} -> {new_hex})"
                            )

                    print(
                        f"\nTotal planned replacements: {total_planned_occurrences} "
                        f"across {len(planned)} color rule(s)."
                    )

                if implicit_dry_run:
                    print(
                        "\nNotice: Executed in dry-run preview mode. To write changes to disk, specify:\n"
                        "  -i / --in-place (overwrite input file) or -o / --output <file> (write to new file)."
                    )
                else:
                    print("Dry run complete. No files were modified.")

            else:
                # Real execution
                try:
                    orig_content = path_obj.read_text(encoding="utf-8")
                    new_content, count = replace_colors_in_svg(orig_content, replacements)

                    # Validate XML syntax of output
                    etree.fromstring(new_content.encode("utf-8"))

                    target_out = Path(args.output) if args.output else path_obj
                    target_out.write_text(new_content, encoding="utf-8")

                    print(f"Successfully replaced {count} color occurrence(s) in '{target_out}'.")
                except Exception as e:
                    print(
                        f"Error applying color replacement to '{svg_file_path}': {e}",
                        file=sys.stderr,
                    )
                    overall_exit_code = 1

        # -------------------------------------------------------------
        # Mode 3: Display Mode (Default)
        # -------------------------------------------------------------
        elif args.json:
            print(format_json_output(counts, occurrences, include_details=args.details))
        elif not counts:
            print(f"No colors identified in '{svg_file_path}'.")
        else:
            print(
                format_table(
                    counts,
                    sort_by=args.sort,
                    reverse=args.reverse,
                    no_header=args.no_header,
                )
            )

            if args.details:
                print("\nElement Occurrence Breakdown:")
                print("-" * 65)
                for hex_val, count in counts.most_common():
                    comment = get_color_comment(hex_val)
                    print(f"\n{hex_val} ({count} occurrences) # {comment}:")
                    matching_occs = [o for o in occurrences if o.color_hex == hex_val]
                    for occ in matching_occs:
                        id_str = f' id="{occ.element_id}"' if occ.element_id else ""
                        lbl_str = f' label="{occ.element_label}"' if occ.element_label else ""
                        print(
                            f"  Line {occ.line_number:>4}: <{occ.element_tag}{id_str}{lbl_str}> "
                            f"property '{occ.property_name}' (raw: {occ.raw_value})"
                        )

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
