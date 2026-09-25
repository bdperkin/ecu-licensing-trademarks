#!/usr/bin/env python3
"""Unit tests for tools/color_svg.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from tools.color_svg import (
        extract_colors_from_svg,
        get_color_comment,
        get_color_shade,
        parse_color,
        replace_colors_in_svg,
    )
except ImportError:
    from color_svg import (
        extract_colors_from_svg,
        get_color_comment,
        get_color_shade,
        parse_color,
        replace_colors_in_svg,
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
COLOR_SCRIPT = REPO_ROOT / "tools" / "color_svg.py"
SAMPLE_ECU_SVG = REPO_ROOT / "fmt" / "svg" / "ecu-vintage-peedee-fullbody.svg"
SAMPLE_LEGACY_SVG = REPO_ROOT / "src" / "alt-logos" / "ecu-legacy-pirate-head.svg"


class TestColorParsingAndNaming(unittest.TestCase):
    """Tests for color parsing, shade classification, and naming."""

    def test_parse_color_hex(self) -> None:
        """Verify hex parsing with various digit counts and cases."""
        self.assertEqual(parse_color("#582c83"), "#582C83")
        self.assertEqual(parse_color("#582C83"), "#582C83")
        self.assertEqual(parse_color("582c83"), "#582C83")
        self.assertEqual(parse_color("#fff"), "#FFFFFF")
        self.assertEqual(parse_color("#000"), "#000000")
        self.assertEqual(parse_color("#123"), "#112233")
        self.assertEqual(parse_color("#abcd"), "#AABBCC")
        self.assertEqual(parse_color("#582c83ff"), "#582C83")

    def test_parse_color_rgb_rgba(self) -> None:
        """Verify rgb() and rgba() parsing with integers and percentages."""
        self.assertEqual(parse_color("rgb(88, 44, 131)"), "#582C83")
        self.assertEqual(parse_color("rgb(0, 0, 0)"), "#000000")
        self.assertEqual(parse_color("rgb(255, 255, 255)"), "#FFFFFF")
        self.assertEqual(parse_color("rgba(88, 44, 131, 0.8)"), "#582C83")
        self.assertEqual(parse_color("rgb(100%, 0%, 0%)"), "#FF0000")
        self.assertEqual(parse_color("rgb(0%, 100%, 0%)"), "#00FF00")
        self.assertEqual(parse_color("rgb(0%, 0%, 100%)"), "#0000FF")

    def test_parse_color_hsl(self) -> None:
        """Verify hsl() parsing."""
        self.assertEqual(parse_color("hsl(0, 100%, 50%)"), "#FF0000")
        self.assertEqual(parse_color("hsl(120, 100%, 50%)"), "#00FF00")
        self.assertEqual(parse_color("hsl(240, 100%, 50%)"), "#0000FF")

    def test_parse_color_named(self) -> None:
        """Verify CSS named color conversion."""
        self.assertEqual(parse_color("black"), "#000000")
        self.assertEqual(parse_color("white"), "#FFFFFF")
        self.assertEqual(parse_color("gold"), "#FFD700")
        self.assertEqual(parse_color("purple"), "#800080")
        self.assertEqual(parse_color("midnightblue"), "#191970")

    def test_parse_color_non_colors(self) -> None:
        """Verify non-colors return None."""
        self.assertIsNone(parse_color("none"))
        self.assertIsNone(parse_color("None"))
        self.assertIsNone(parse_color("transparent"))
        self.assertIsNone(parse_color("currentColor"))
        self.assertIsNone(parse_color("inherit"))
        self.assertIsNone(parse_color("url(#linearGradient1)"))
        self.assertIsNone(parse_color(""))
        self.assertIsNone(parse_color(None))
        self.assertIsNone(parse_color("not-a-color"))

    def test_get_color_shade(self) -> None:
        """Verify shade classification across grayscales and hues."""
        self.assertEqual(get_color_shade("#000000"), "Black")
        self.assertEqual(get_color_shade("#FFFFFF"), "White")
        self.assertEqual(get_color_shade("#808080"), "Gray")
        self.assertEqual(get_color_shade("#231F20"), "Near Black")
        self.assertEqual(get_color_shade("#FF0000"), "Vivid Red")
        self.assertEqual(get_color_shade("#00FF00"), "Vivid Green")
        self.assertEqual(get_color_shade("#0000FF"), "Vivid Blue")

    def test_get_color_comment(self) -> None:
        """Verify comment generation matches official brand names when available."""
        self.assertEqual(get_color_comment("#582C83"), "ECU Purple (PMS 268 C/U)")
        self.assertEqual(get_color_comment("#FFC700"), "ECU Gold - Uncoated (PMS 109 U)")
        self.assertEqual(get_color_comment("#FFC72C"), "ECU Gold - Coated (PMS 123 C)")
        self.assertEqual(get_color_comment("#000000"), "Black (Process Black C)")
        self.assertEqual(get_color_comment("#FFFFFF"), "White")
        self.assertEqual(get_color_comment("#D3A985"), "Beige / Skin Tone (PMS 728 C/U)")
        self.assertEqual(get_color_comment("#9D2235"), "Red / Crimson (PMS 201 C)")
        # Non-official color comments
        self.assertIn("Gold", get_color_comment("#FDD50E"))
        self.assertIn("Tan / Beige", get_color_comment("#E6B671"))


class TestColorExtractionAndSubstitution(unittest.TestCase):
    """Tests for SVG scanning, color counting, and text substitution."""

    def test_extract_colors_from_svg(self) -> None:
        """Verify extraction across attributes, styles, and <style> tags."""
        svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <defs>
    <linearGradient id="g1">
      <stop offset="0%" stop-color="#FFC700"/>
      <stop offset="100%" stop-color="#FFC72C"/>
    </linearGradient>
  </defs>
  <path id="p1" fill="#582C83" stroke="#000000" inkscape:label="Path 1"/>
  <rect id="r1" style="fill:#582C83; stroke:none; fill-opacity:1;"/>
  <style type="text/css">
    .text-cls { fill: #FFFFFF; stroke: #582C83; }
  </style>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg_content)
            temp_path = Path(f.name)

        try:
            counts, occurrences = extract_colors_from_svg(temp_path)
            # #582C83: p1 fill, r1 style:fill, style .text-cls stroke = 3
            self.assertEqual(counts["#582C83"], 3)
            # #FFC700: stop-color = 1
            self.assertEqual(counts["#FFC700"], 1)
            # #FFC72C: stop-color = 1
            self.assertEqual(counts["#FFC72C"], 1)
            # #000000: p1 stroke = 1
            self.assertEqual(counts["#000000"], 1)
            # #FFFFFF: style .text-cls fill = 1
            self.assertEqual(counts["#FFFFFF"], 1)
            self.assertEqual(len(occurrences), 7)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_replace_colors_in_svg(self) -> None:
        """Verify accurate substitution while preserving whitespace and tags."""
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg">
  <path id="p1" fill="#2f2976" stroke="#fdd50e"/>
  <rect id="r1" style="fill:#2F2976; stroke:none;"/>
  <style>.c1 { fill: #2f2976; }</style>
</svg>"""
        replacements = {"#2F2976": "#582C83", "#FDD50E": "#FFC700"}
        result, count = replace_colors_in_svg(svg_content, replacements)

        self.assertEqual(count, 4)
        self.assertIn('fill="#582C83"', result)
        self.assertIn('stroke="#FFC700"', result)
        self.assertIn("fill:#582C83;", result)
        self.assertIn("fill: #582C83;", result)
        self.assertNotIn("#2f2976", result)
        self.assertNotIn("#2F2976", result)
        self.assertNotIn("#fdd50e", result)


class TestColorSvgCLI(unittest.TestCase):
    """End-to-end tests executing tools/color_svg.py via CLI."""

    def run_tool(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(COLOR_SCRIPT), *args]
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def test_display_mode(self) -> None:
        """Verify default table display and counts."""
        res = self.run_tool([str(SAMPLE_ECU_SVG)])
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("HEX COLOR", res.stdout)
        self.assertIn("COUNT", res.stdout)
        self.assertIn("#000000", res.stdout)
        self.assertIn("#582C83", res.stdout)
        self.assertIn("#FFC72C", res.stdout)
        self.assertIn("#D3A985", res.stdout)
        self.assertIn("#FFFFFF", res.stdout)
        self.assertIn("ECU Purple", res.stdout)

    def test_sort_options(self) -> None:
        """Verify sorting by hex, count, and name."""
        res_hex = self.run_tool([str(SAMPLE_ECU_SVG), "--sort", "hex", "--no-header"])
        self.assertEqual(res_hex.returncode, 0)
        lines = [line.split()[0] for line in res_hex.stdout.strip().splitlines() if line]
        self.assertEqual(lines, sorted(lines))

    def test_json_output(self) -> None:
        """Verify --json output structure."""
        res = self.run_tool([str(SAMPLE_ECU_SVG), "--json"])
        self.assertEqual(res.returncode, 0)
        self.assertTrue(res.stdout.strip().startswith("["))
        self.assertIn('"hex": "#582C83"', res.stdout)
        self.assertIn('"count":', res.stdout)

    def test_validation_success(self) -> None:
        """Verify validation passes when all colors match official palette."""
        res = self.run_tool([str(SAMPLE_ECU_SVG), "--validate", "--palette", "official"])
        self.assertEqual(res.returncode, 0, f"Expected validation success: {res.stderr}")
        self.assertIn("Validation PASSED", res.stdout)

    def test_validation_failure(self) -> None:
        """Verify validation errors out with code 1 and reports violating colors."""
        res = self.run_tool([str(SAMPLE_LEGACY_SVG), "--validate", "--palette", "official"])
        self.assertEqual(res.returncode, 1)
        self.assertIn("Validation FAILED", res.stderr)
        self.assertIn("#2F2976", res.stderr)
        self.assertIn("#FDD50E", res.stderr)
        self.assertIn("#E6B671", res.stderr)
        self.assertIn("#231F20", res.stderr)

    def test_validation_custom_palette(self) -> None:
        """Verify validation with custom comma-separated palette list."""
        palette = "#FDD50E,#E6B671,#231F20,#FFFFFF,#2F2976"
        res = self.run_tool([str(SAMPLE_LEGACY_SVG), "--validate", "--palette", palette])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Validation PASSED", res.stdout)

    def test_dry_run_replacement(self) -> None:
        """Verify dry-run reports planned replacements without touching files."""
        res = self.run_tool(
            [
                str(SAMPLE_LEGACY_SVG),
                "--replace",
                "#2F2976",
                "#582C83",
                "--replace",
                "#FDD50E",
                "#FFC700",
                "--dry-run",
            ]
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("[Dry Run] Color replacement plan", res.stdout)
        self.assertIn("#2F2976", res.stdout)
        self.assertIn("#582C83", res.stdout)
        self.assertIn("Total planned replacements: 7", res.stdout)
        self.assertIn("Dry run complete. No files were modified.", res.stdout)

    def test_implicit_dry_run(self) -> None:
        """Verify that omitting -o and -i safely triggers dry-run preview mode."""
        res = self.run_tool([str(SAMPLE_LEGACY_SVG), "-r", "#2F2976", "#582C83"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("[Dry Run] Color replacement plan", res.stdout)
        self.assertIn("Notice: Executed in dry-run preview mode.", res.stdout)

    def test_file_output_replacement(self) -> None:
        """Verify -o writes substituted SVG to target path."""
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            temp_out = Path(f.name)

        try:
            res = self.run_tool(
                [
                    str(SAMPLE_LEGACY_SVG),
                    "-r",
                    "#2F2976",
                    "#582C83",
                    "-o",
                    str(temp_out),
                ]
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("Successfully replaced 1 color occurrence(s)", res.stdout)

            # Check that temp_out has new color and not old color
            counts, _ = extract_colors_from_svg(temp_out)
            self.assertIn("#582C83", counts)
            self.assertNotIn("#2F2976", counts)
        finally:
            if temp_out.exists():
                temp_out.unlink()

    def test_in_place_replacement(self) -> None:
        """Verify -i replaces color in-place directly on disk."""
        sample_svg = """<svg xmlns="http://www.w3.org/2000/svg">
  <path id="p1" fill="#2f2976"/>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(sample_svg)
            temp_file = Path(f.name)

        try:
            res = self.run_tool(
                [
                    str(temp_file),
                    "-r",
                    "#2F2976",
                    "#582C83",
                    "-i",
                ]
            )
            self.assertEqual(res.returncode, 0)
            content = temp_file.read_text(encoding="utf-8")
            self.assertIn('fill="#582C83"', content)
            self.assertNotIn("#2f2976", content)
        finally:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    unittest.main()
