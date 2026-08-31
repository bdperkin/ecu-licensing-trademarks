#!/usr/bin/env python3
"""Unit tests for tools/export_svg_groups.py."""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.export_svg_groups import (
    filter_groups,
    get_supported_formats,
    main,
    normalize_slug,
    parse_svg_groups,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_SVG = REPO_ROOT / "src" / "art-sheet-5-8-23" / "2023-05-08-art-sheet-01.svg"


class TestExportSvgGroups(unittest.TestCase):
    """Test suite for SVG group exporter and hierarchy inspector."""

    def setUp(self) -> None:
        self.assertTrue(SAMPLE_SVG.exists(), f"Sample SVG not found at {SAMPLE_SVG}")

    def test_normalize_slug(self) -> None:
        """Test label normalization into clean directory/file slugs."""
        self.assertEqual(normalize_slug("Primary Mark"), "primary-mark")
        self.assertEqual(normalize_slug("Page 1 Title"), "page-1-title")
        self.assertEqual(normalize_slug("Mark 5"), "mark-5")
        self.assertEqual(
            normalize_slug("Gold & Black / Powder Blue!"), "gold-black-powder-blue"
        )
        self.assertEqual(normalize_slug(""), "unlabeled")
        self.assertEqual(normalize_slug("---"), "unlabeled")

    def test_no_args_prints_help(self) -> None:
        """Requirement 6: If no arguments or flags given, default to printing help."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("usage: export_svg_groups.py", output)
        self.assertIn("Scan, list, filter, and export SVG groups", output)

    def test_file_only_defaults_to_list_tree(self) -> None:
        """Requirements 7 & 8: If file provided with no flags, list groups as a tree."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([str(SAMPLE_SVG)])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Page 1 Title [g0011000]", output)
        self.assertIn("Primary Mark [g0015000]", output)
        self.assertIn("├── Mark 1 [g0100000]", output)
        self.assertIn("└── ", output)

    def test_list_flag_explicit(self) -> None:
        """Requirement 2: -l / --list explicitly lists groups."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([str(SAMPLE_SVG), "--list"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Page 2 Title [g0021000]", output)
        self.assertIn("Page 3 Footer [g0037000]", output)

    def test_filter_exact_match(self) -> None:
        """Requirement 3: Match a single group by exact label."""
        groups = parse_svg_groups(SAMPLE_SVG)
        matched = filter_groups(groups, "Mark 5")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].id, "g0500000")
        self.assertEqual(matched[0].label, "Mark 5")
        self.assertEqual(matched[0].ancestor_labels, ["Primary Mark"])

    def test_filter_regex(self) -> None:
        """Requirement 3: Match groups via regular expression."""
        groups = parse_svg_groups(SAMPLE_SVG)
        matched = filter_groups(groups, r"^Mark [1-3]$")
        self.assertEqual(len(matched), 3)
        labels = sorted(m.label for m in matched)
        self.assertEqual(labels, ["Mark 1", "Mark 2", "Mark 3"])

    def test_filter_glob(self) -> None:
        """Requirement 3: Match groups via glob pattern."""
        groups = parse_svg_groups(SAMPLE_SVG)
        matched = filter_groups(groups, "Page * Title")
        self.assertEqual(len(matched), 3)
        labels = sorted(m.label for m in matched)
        self.assertEqual(labels, ["Page 1 Title", "Page 2 Title", "Page 3 Title"])

    def test_default_format_when_group_provided(self) -> None:
        """Requirement 9: If group provided, but no format provided, default to plain SVG."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(SAMPLE_SVG),
                    "--group",
                    "Mark 5",
                    "--dry-run",
                    "--verbose",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Exporting 1 group(s) as 'svg'", output)
        self.assertIn("fmt/svg/primary-mark/mark-5.svg", output)

    def test_default_top_level_when_format_provided(self) -> None:
        """Requirement 10: If format provided, but no group provided, export all top-level groups."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(SAMPLE_SVG),
                    "--format",
                    "png",
                    "--dry-run",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Exporting 25 group(s) as 'png'", output)
        self.assertIn("fmt/png/page-1-title.png", output)
        self.assertIn("fmt/png/primary-mark.png", output)

    def test_real_export_in_tempdir(self) -> None:
        """Requirements 11, 12, 13, 14, 15: Full export into nested fmt directory structure."""
        if not shutil.which("inkscape"):
            self.skipTest("Inkscape CLI not installed in environment")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        str(SAMPLE_SVG),
                        "--group",
                        "Mark 5",
                        "--format",
                        "svg",
                        "--output-dir",
                        str(out_path),
                    ]
                )
            self.assertEqual(exit_code, 0)

            # Check created file structure
            expected_file = out_path / "fmt" / "svg" / "primary-mark" / "mark-5.svg"
            self.assertTrue(
                expected_file.exists(),
                f"Expected file {expected_file} was not created.",
            )
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_full_document_export_dry_run(self) -> None:
        """Test exporting full document canvas in dry-run mode."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(SAMPLE_SVG),
                    "--full",
                    "--format",
                    "png",
                    "--dry-run",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("fmt/png/2023-05-08-art-sheet-01.png", output)

    def test_full_document_export_real(self) -> None:
        """Test actual full document export into temporary directory."""
        if not shutil.which("inkscape"):
            self.skipTest("Inkscape CLI not installed in environment")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        str(SAMPLE_SVG),
                        "--all",
                        "--format",
                        "svg",
                        "--output-dir",
                        str(out_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            expected_file = out_path / "fmt" / "svg" / f"{SAMPLE_SVG.stem}.svg"
            self.assertTrue(
                expected_file.exists(),
                f"Expected file {expected_file} was not created.",
            )
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_get_supported_formats(self) -> None:
        """Test dynamic discovery of supported Inkscape export formats."""
        formats = get_supported_formats()
        self.assertIsInstance(formats, list)
        self.assertIn("svg", formats)
        self.assertIn("png", formats)
        self.assertIn("pdf", formats)

    def test_list_formats_flag(self) -> None:
        """Test --list-formats flag outputs supported format catalog."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--list-formats"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Supported Inkscape export formats", output)
        self.assertIn(".png", output)
        self.assertIn(".svg", output)

    def test_invalid_format_rejected(self) -> None:
        """Test that unsupported formats are rejected with an error message."""
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main([str(SAMPLE_SVG), "--format", "nonexistent_fmt"])
        self.assertEqual(exit_code, 1)
        output = stderr.getvalue()
        self.assertIn("Unsupported export format", output)
        self.assertIn("Allowed formats", output)

    def test_verbose_export_logging(self) -> None:
        """Test that --verbose logs detailed subprocess execution commands."""
        if not shutil.which("inkscape"):
            self.skipTest("Inkscape CLI not installed in environment")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        str(SAMPLE_SVG),
                        "--group",
                        "Mark 5",
                        "--format",
                        "svg",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Running:", output)
            self.assertIn("inkscape", output)
            self.assertIn("g0500000", output)
            expected_file = out_path / "fmt" / "svg" / "primary-mark" / "mark-5.svg"
            self.assertTrue(expected_file.exists())


if __name__ == "__main__":
    unittest.main()
