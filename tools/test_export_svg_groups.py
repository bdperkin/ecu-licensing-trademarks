#!/usr/bin/env python3
"""Unit tests for tools/export_svg_groups.py."""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lxml import etree

from tools.export_svg_groups import (
    INKSCAPE_NS,
    filter_groups,
    get_supported_formats,
    main,
    normalize_slug,
    parse_svg_groups,
    remove_mark_number_indicators,
    verify_exported_file,
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
        self.assertEqual(normalize_slug("Gold & Black / Powder Blue!"), "gold-black-powder-blue")
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

    def test_extension_format_export_hpgl(self) -> None:
        """Test two-step isolation export for extension-based format (HPGL)."""
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
                        "Mark 63",
                        "--format",
                        "hpgl",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Isolating group SVG:", output)
            self.assertIn("[VERBOSE] Converting isolated SVG:", output)
            expected_file = out_path / "fmt" / "hpgl" / "brand-pattern-swatches" / "mark-63.hpgl"
            self.assertTrue(expected_file.exists())
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_export_timeout_expired(self) -> None:
        """Test that exceeding the timeout aborts cleanly and reports an error."""
        if not shutil.which("inkscape"):
            self.skipTest("Inkscape CLI not installed in environment")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        str(SAMPLE_SVG),
                        "--group",
                        "Mark 1",
                        "--format",
                        "png",
                        "--output-dir",
                        str(out_path),
                        "--timeout",
                        "0.0001",
                    ]
                )
            self.assertEqual(exit_code, 1)
            output = stderr.getvalue()
            self.assertIn("timed out", output)

    def test_verify_exported_file_missing(self) -> None:
        """Test that verify_exported_file raises when file does not exist."""
        non_existent = Path("/tmp/definitely_not_a_real_file_12345.png")
        with self.assertRaises(RuntimeError) as ctx:
            verify_exported_file(non_existent)
        self.assertIn("was not created", str(ctx.exception))

    def test_verify_exported_file_empty(self) -> None:
        """Test that verify_exported_file raises when file is 0 bytes."""
        with tempfile.NamedTemporaryFile(suffix=".png") as empty_file:
            empty_path = Path(empty_file.name)
            with self.assertRaises(RuntimeError) as ctx:
                verify_exported_file(empty_path)
            self.assertIn("is empty", str(ctx.exception))

    def test_raster_export_and_verification_jpg(self) -> None:
        """Test raster conversion and post-export verification for JPG."""
        if not shutil.which("inkscape") or not (shutil.which("magick") or shutil.which("convert")):
            self.skipTest("Inkscape or ImageMagick not installed in environment")

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
                        "jpg",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Rendering intermediate PNG:", output)
            self.assertIn("[VERBOSE] Converting raster image:", output)
            expected_file = out_path / "fmt" / "jpg" / "primary-mark" / "mark-5.jpg"
            self.assertTrue(expected_file.exists())
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_archive_export_tar(self) -> None:
        """Test archive export and verification for TAR."""
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
                        "tar",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Verified valid tar archive:", output)
            expected_file = out_path / "fmt" / "tar" / "primary-mark" / "mark-5.tar"
            self.assertTrue(expected_file.exists())
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_archive_export_zip(self) -> None:
        """Test archive export and verification for ZIP."""
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
                        "zip",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Verified valid zip archive:", output)
            expected_file = out_path / "fmt" / "zip" / "primary-mark" / "mark-5.zip"
            self.assertTrue(expected_file.exists())
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_export_xaml(self) -> None:
        """Test XAML export and ResourceDictionary verification."""
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
                        "xaml",
                        "--output-dir",
                        str(out_path),
                        "--verbose",
                    ]
                )
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("[VERBOSE] Verified valid XAML document", output)
            expected_file = out_path / "fmt" / "xaml" / "primary-mark" / "mark-5.xaml"
            self.assertTrue(expected_file.exists())
            self.assertGreater(expected_file.stat().st_size, 0)

    def test_remove_mark_number_indicators_function(self) -> None:
        """Test remove_mark_number_indicators directly on SVG DOM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cleaned_svg = Path(tmpdir) / "cleaned.svg"
            remove_mark_number_indicators(SAMPLE_SVG, output_path=cleaned_svg)
            self.assertTrue(cleaned_svg.exists())

            tree = etree.parse(str(cleaned_svg))
            root = tree.getroot()
            ink_label = f"{{{INKSCAPE_NS}}}label"

            # Verify that for Mark 45, the child labeled '45' is gone, but other children remain
            mark45 = root.xpath(
                '//svg:g[@inkscape:label="Mark 45"]',
                namespaces={"svg": "http://www.w3.org/2000/svg", "inkscape": INKSCAPE_NS},
            )
            self.assertEqual(len(mark45), 1)
            child_labels = [c.get(ink_label) for c in mark45[0]]
            self.assertNotIn("45", child_labels)
            self.assertIn("45 Background", child_labels)
            self.assertIn("45 Mark", child_labels)

            # Verify that for Mark 1, the child labeled '1' is gone
            mark1 = root.xpath(
                '//svg:g[@inkscape:label="Mark 1"]',
                namespaces={"svg": "http://www.w3.org/2000/svg", "inkscape": INKSCAPE_NS},
            )
            self.assertEqual(len(mark1), 1)
            child_labels_1 = [c.get(ink_label) for c in mark1[0]]
            self.assertNotIn("1", child_labels_1)
            self.assertIn("1 Background", child_labels_1)
            self.assertIn("1 Primary Mark", child_labels_1)

    def test_remove_mark_number_indicators_target_group_only(self) -> None:
        """Test remove_mark_number_indicators targeting a specific group ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cleaned_svg = Path(tmpdir) / "cleaned_single.svg"
            # Target Mark 45 (id: g4500000)
            remove_mark_number_indicators(
                SAMPLE_SVG, output_path=cleaned_svg, target_group_id="g4500000"
            )
            self.assertTrue(cleaned_svg.exists())

            tree = etree.parse(str(cleaned_svg))
            root = tree.getroot()
            ink_label = f"{{{INKSCAPE_NS}}}label"

            # Mark 45 should have child '45' removed
            mark45 = root.xpath(
                '//svg:g[@inkscape:label="Mark 45"]',
                namespaces={"svg": "http://www.w3.org/2000/svg", "inkscape": INKSCAPE_NS},
            )
            child_labels_45 = [c.get(ink_label) for c in mark45[0]]
            self.assertNotIn("45", child_labels_45)

            # Mark 1 should still retain child '1'
            mark1 = root.xpath(
                '//svg:g[@inkscape:label="Mark 1"]',
                namespaces={"svg": "http://www.w3.org/2000/svg", "inkscape": INKSCAPE_NS},
            )
            child_labels_1 = [c.get(ink_label) for c in mark1[0]]
            self.assertIn("1", child_labels_1)

    def test_cli_no_mark_numbers_dry_run(self) -> None:
        """Test --no-mark-numbers CLI option in dry-run mode."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(SAMPLE_SVG),
                    "--pattern",
                    "^Mark 45$",
                    "--no-mark-numbers",
                    "--dry-run",
                ]
            )
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn('[DRY-RUN] Would export: [g4500000] "Mark 45"', output)

    def test_cli_no_mark_numbers_real_export(self) -> None:
        """Test real export with --no-mark-numbers excludes the indicator child group."""
        if not shutil.which("inkscape"):
            self.skipTest("Inkscape CLI not installed in environment")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        str(SAMPLE_SVG),
                        "--pattern",
                        "^Mark 45$",
                        "--no-mark-numbers",
                        "--format",
                        "svg",
                        "--output-dir",
                        str(out_path),
                    ]
                )
            self.assertEqual(exit_code, 0)

            exported_file = (
                out_path / "fmt" / "svg" / "sport-specific-marks" / "gold-on-black" / "mark-45.svg"
            )
            self.assertTrue(exported_file.exists())
            self.assertGreater(exported_file.stat().st_size, 0)

            tree = etree.parse(str(exported_file))
            elem_ids = [e.get("id") for e in tree.getroot().iter() if e.get("id")]

            # Child group '45' has ID 'g4500004' in the master SVG; it must not be present in exported SVG
            self.assertNotIn("g4500004", elem_ids)
            # Artwork elements '45 Background' (g4500001) and '45 Mark' (g4500007) must be present
            self.assertIn("g4500001", elem_ids)
            self.assertIn("g4500007", elem_ids)


if __name__ == "__main__":
    unittest.main()
