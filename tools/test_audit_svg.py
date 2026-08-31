#!/usr/bin/env python3
"""Unit tests for tools/audit_svg.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = REPO_ROOT / "tools" / "audit_svg.py"
ART_SHEET_SVG = REPO_ROOT / "src" / "art-sheet-5-8-23" / "2023-05-08-art-sheet-01.svg"


class TestAuditSvgTool(unittest.TestCase):
    """Test suite for SVG audit checks."""

    def run_audit(
        self, svg_path: str | Path, args: list[str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(AUDIT_SCRIPT), str(svg_path)]
        if args:
            cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def test_repo_art_sheet_audit_strict(self) -> None:
        """Verify that the production art sheet SVG passes in strict mode."""
        self.assertTrue(ART_SHEET_SVG.is_file(), f"Art sheet not found at {ART_SHEET_SVG}")
        res = self.run_audit(ART_SHEET_SVG, ["--strict", "-s"])
        self.assertEqual(
            res.returncode,
            0,
            f"Audit failed with code {res.returncode}:\n{res.stdout}\n{res.stderr}",
        )
        self.assertIn("Total <g> elements: 1045", res.stdout)
        self.assertIn("Groups missing labels: 0", res.stdout)
        self.assertIn("Duplicate label names: 0", res.stdout)

    def test_missing_label_check(self) -> None:
        """Check 1: Verify missing label detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="unlabeled"><path id="p1"/><path id="p2"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "missing"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Total groups missing label: 1", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_duplicate_label_check(self) -> None:
        """Check 2: Verify duplicate label detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="g1" inkscape:label="DupLabel"><path id="p1"/><path id="p2"/></g>
  <g id="g2" inkscape:label="DupLabel"><path id="p3"/><path id="p4"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "duplicates"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Label 'DupLabel' (2 occurrences) is duplicated", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_spelling_check(self) -> None:
        """Check 3: Verify typo detection in labels."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="g1" inkscape:label="Verbiag Typoo"><path id="p1"/><path id="p2"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "spelling"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("contains potential typos", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_empty_groups_check(self) -> None:
        """Check 4: Verify empty groups detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="empty_g" inkscape:label="Empty Container" />
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "empty"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Total empty groups: 1", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_single_object_groups_check(self) -> None:
        """Check 5: Verify single-child wrapper groups detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="single_g" inkscape:label="Single Wrapper"><path id="p1"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "single"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Total single-object groups: 1", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_formatting_check(self) -> None:
        """Check 6: Verify label formatting and whitespace detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="g1" inkscape:label="  Leading"><path id="p1"/><path id="p2"/></g>
  <g id="g2" inkscape:label="Double  Space"><path id="p3"/><path id="p4"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "formatting"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("leading/trailing whitespace", res.stdout)
            self.assertIn("consecutive spaces", res.stdout)
            self.assertIn("Total groups with formatting issues: 2", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_numbered_marks_check(self) -> None:
        """Check 7: Verify numbered mark sequence and indicator child check."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="m1" inkscape:label="Mark 1"><g id="c1" inkscape:label="1"><path id="p1"/><path id="p2"/></g></g>
  <g id="m3" inkscape:label="Mark 3"><g id="bad" inkscape:label="wrong"><path id="p3"/><path id="p4"/></g></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "marks"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Missing Mark 2 in sequence Mark 1..Mark 3", res.stdout)
            self.assertIn("Mark 3 is missing child indicator group labeled '3'", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()

    def test_ungrouped_canvas_root_check(self) -> None:
        """Check 8: Verify stranded canvas root element detection."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <path id="stranded_path" d="M0,0" />
  <g id="sec1" inkscape:label="Section 1"><path id="p1"/><path id="p2"/></g>
</svg>"""
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
            f.write(svg)
            fname = Path(f.name)
        try:
            res = self.run_audit(fname, ["-c", "ungrouped"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Stranded <path id='stranded_path'> element at canvas root", res.stdout)
        finally:
            if fname.exists():
                fname.unlink()


if __name__ == "__main__":
    unittest.main()
