#!/usr/bin/env python3
"""SVG Group Exporter & Hierarchy Inspector.

Scans an SVG file to inspect, list, filter, and export group elements,
hierarchical subtrees, or full documents into structured directory layouts.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from lxml import etree

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SVG_NS = "http://www.w3.org/2000/svg"


class GroupNode(NamedTuple):
    """Represents a <g> element in the SVG hierarchy."""

    element: etree._Element
    id: str
    label: str
    depth: int
    ancestor_labels: list[str]
    parent_id: str | None


def get_supported_formats() -> list[str]:
    """Dynamically query Inkscape CLI for supported export formats.

    Parses the allowed export types from Inkscape's error output when an invalid
    format is supplied to `--export-type`.
    """
    inkscape_path = shutil.which("inkscape")
    if not inkscape_path:
        return ["svg", "png", "pdf", "eps", "ps"]

    result = subprocess.run(
        [inkscape_path, "--export-type=invalid_format"],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"Allowed values:\s*\[([^\]]+)\]", combined)
    if match:
        raw_items = match.group(1).split(",")
        formats: list[str] = []
        for item in raw_items:
            clean = re.sub(r"[^a-zA-Z0-9]", "", item).lower()
            if clean:
                formats.append(clean)
        if formats:
            return sorted(set(formats))

    return ["svg", "png", "pdf", "eps", "ps"]


def normalize_slug(text: str) -> str:
    """Normalize label or ID into a clean hyphenated slug.

    Converts alphanumeric characters to lowercase and replaces all other
    characters and whitespace with hyphens.
    """
    if not text:
        return "unlabeled"
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).lower()
    # Strip leading and trailing hyphens
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug or "unlabeled"


def parse_svg_groups(svg_file: Path) -> list[GroupNode]:
    """Parse all <g> elements from an SVG file and capture hierarchical ancestry."""
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(str(svg_file), parser)
    root = tree.getroot()

    nodes: list[GroupNode] = []

    def _traverse(
        elem: etree._Element,
        depth: int,
        ancestors: list[str],
        parent_id: str | None,
    ) -> None:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "g":
            gid = elem.get("id", "")
            lbl = elem.get(f"{{{INKSCAPE_NS}}}label", "")
            node = GroupNode(
                element=elem,
                id=gid,
                label=lbl,
                depth=depth,
                ancestor_labels=list(ancestors),
                parent_id=parent_id,
            )
            nodes.append(node)

            # Update ancestry for children
            current_label = lbl or gid or f"group-{gid}"
            new_ancestors = [*ancestors, current_label]
            for child in elem:
                _traverse(child, depth + 1, new_ancestors, gid)
        else:
            for child in elem:
                _traverse(child, depth, ancestors, parent_id)

    # Only traverse canvas root groups, skipping <defs>
    for top_elem in root:
        tag = top_elem.tag.split("}")[-1] if "}" in top_elem.tag else top_elem.tag
        if tag != "defs":
            _traverse(top_elem, depth=0, ancestors=[], parent_id=None)

    return nodes


def render_group_tree(nodes: list[GroupNode]) -> str:
    """Render a visual ASCII/Unicode tree of groups showing hierarchy and IDs."""
    if not nodes:
        return "(No groups found)"

    lines: list[str] = []

    # Map nodes by parent ID
    children_map: dict[str | None, list[GroupNode]] = {}
    for node in nodes:
        children_map.setdefault(node.parent_id, []).append(node)

    def _build_tree_lines(
        parent_id: str | None, prefix: str = "", is_root: bool = True
    ) -> None:
        children = children_map.get(parent_id, [])
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "" if is_root else ("└── " if is_last else "├── ")
            child_prefix = "" if is_root else ("    " if is_last else "│   ")

            label_display = child.label if child.label else "(no label)"
            id_display = f"[{child.id}]" if child.id else "[no id]"
            lines.append(f"{prefix}{connector}{label_display} {id_display}")

            _build_tree_lines(child.id, prefix + child_prefix, is_root=False)

    _build_tree_lines(None, prefix="", is_root=True)
    return "\n".join(lines)


def filter_groups(
    nodes: list[GroupNode], pattern: str | None, top_level_only: bool = False
) -> list[GroupNode]:
    """Filter group nodes by exact match, glob, or regex against label or ID."""
    if top_level_only:
        return [n for n in nodes if n.depth == 0 and (n.label or n.id)]

    if not pattern:
        return nodes

    pattern_stripped = pattern.strip()
    has_regex_chars = bool(re.search(r"[\^$*+?{}\\\[\]|()]", pattern_stripped))

    if not has_regex_chars:
        # Check for exact matches first
        exact_matches = [
            n
            for n in nodes
            if n.label.lower() == pattern_stripped.lower()
            or n.id.lower() == pattern_stripped.lower()
        ]
        if exact_matches:
            return exact_matches

        # Substring fallback
        return [
            n
            for n in nodes
            if pattern_stripped.lower() in n.label.lower()
            or pattern_stripped.lower() in n.id.lower()
        ]

    # Regex or glob matching
    matched: list[GroupNode] = []
    regex = None
    try:
        regex = re.compile(pattern_stripped, re.IGNORECASE)
    except re.error:
        pass

    for node in nodes:
        target_label = node.label
        target_id = node.id
        is_match = False

        if regex:
            if regex.search(target_label) or (target_id and regex.search(target_id)):
                is_match = True

        if not is_match:
            if fnmatch.fnmatch(
                target_label.lower(), pattern_stripped.lower()
            ) or fnmatch.fnmatch(target_id.lower(), pattern_stripped.lower()):
                is_match = True

        if is_match:
            matched.append(node)

    return matched


def export_group(
    svg_file: Path,
    node: GroupNode,
    fmt: str,
    output_base_dir: Path,
    dpi: float = 229.33,
    dry_run: bool = False,
    verbose: bool = False,
) -> Path:
    """Export an individual group element to the destination fmt hierarchy."""
    # Ensure inkscape CLI is available
    inkscape_path = shutil.which("inkscape")
    if not inkscape_path:
        msg = "Inkscape CLI executable ('inkscape') is required for exporting groups."
        raise RuntimeError(msg)

    # 1. Format directory: <output_base_dir>/fmt/<format>/
    fmt_dir = output_base_dir / "fmt" / fmt.lower()

    # 2. Ancestor directories: <output_base_dir>/fmt/<format>/<ancestor_1>/<ancestor_2>/...
    ancestor_path_parts = [normalize_slug(a) for a in node.ancestor_labels]
    target_dir = (
        fmt_dir.joinpath(*ancestor_path_parts) if ancestor_path_parts else fmt_dir
    )

    # 3. Leaf filename: <leaf_label>.<fmt>
    leaf_name = normalize_slug(node.label or node.id)
    output_file = target_dir / f"{leaf_name}.{fmt.lower()}"

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            inkscape_path,
            str(svg_file),
            f"--export-id={node.id}",
            "--export-id-only",
            f"--export-filename={output_file}",
        ]

        if fmt.lower() == "svg":
            cmd.append("--export-plain-svg")
        elif fmt.lower() == "png":
            cmd.append(f"--export-dpi={dpi}")

        if verbose:
            print(f"[VERBOSE] Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if verbose and result.stdout:
            print(result.stdout)
        if verbose and result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            msg = (
                f"Failed to export group '{node.id}' ({node.label}) "
                f"to {output_file}:\n{result.stderr}"
            )
            raise RuntimeError(msg)

    if verbose or dry_run:
        prefix = "[DRY-RUN] Would export" if dry_run else "Exported"
        print(f'{prefix}: [{node.id}] "{node.label}" -> {output_file}')

    return output_file


def export_full_document(
    svg_file: Path,
    fmt: str,
    output_base_dir: Path,
    dpi: float = 229.33,
    dry_run: bool = False,
    verbose: bool = False,
) -> Path:
    """Export the entire SVG document canvas without group isolation."""
    inkscape_path = shutil.which("inkscape")
    if not inkscape_path:
        msg = "Inkscape CLI executable ('inkscape') is required for document export."
        raise RuntimeError(msg)

    # 1. Format directory: <output_base_dir>/fmt/<format>/
    fmt_dir = output_base_dir / "fmt" / fmt.lower()

    # 2. Output file: <output_base_dir>/fmt/<format>/<svg_file.stem>.<format>
    output_file = fmt_dir / f"{svg_file.stem}.{fmt.lower()}"

    if not dry_run:
        fmt_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            inkscape_path,
            str(svg_file),
            f"--export-filename={output_file}",
        ]

        if fmt.lower() == "svg":
            cmd.append("--export-plain-svg")
        elif fmt.lower() == "png":
            cmd.append(f"--export-dpi={dpi}")

        if verbose:
            print(f"[VERBOSE] Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if verbose and result.stdout:
            print(result.stdout)
        if verbose and result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            msg = (
                f"Failed to export full document '{svg_file}' "
                f"to {output_file}:\n{result.stderr}"
            )
            raise RuntimeError(msg)

    if verbose or dry_run:
        prefix = (
            "[DRY-RUN] Would export full document"
            if dry_run
            else "Exported full document"
        )
        print(f"{prefix}: '{svg_file.name}' -> {output_file}")

    return output_file


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="export_svg_groups.py",
        description="Scan, list, filter, and export SVG groups, hierarchical subtrees, or entire documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all groups in a hierarchical tree:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg

  # List groups explicitly:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --list

  # List all supported Inkscape export formats:
  python3 tools/export_svg_groups.py --list-formats

  # Export a specific mark to plain SVG:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --group "Mark 5"

  # Export all marks matching a regex to PNG format:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --group "^Mark [1-5]$" --format png

  # Export the entire document canvas as PNG:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format png

  # Export all top-level sections to SVG in a target directory:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --format svg --output-dir ./dist
""",
    )

    parser.add_argument(
        "svg_file",
        nargs="?",
        type=Path,
        help="Path to the input SVG file.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all group labels and IDs in a hierarchical tree.",
    )
    parser.add_argument(
        "-F",
        "--list-formats",
        "--formats",
        dest="list_formats",
        action="store_true",
        help="Query and display the list of all supported Inkscape export formats.",
    )
    parser.add_argument(
        "-a",
        "--all",
        "--full",
        "--document",
        dest="full_document",
        action="store_true",
        help="Export the entire SVG document canvas as-is (output to <output_dir>/fmt/<format>/<basename>.<format>).",
    )
    parser.add_argument(
        "-g",
        "--group",
        "-p",
        "--pattern",
        dest="pattern",
        type=str,
        default=None,
        help=r"Filter group(s) by exact label, regex, or glob pattern (e.g. 'Mark 5', '^Mark \d+$', 'Mark *').",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default=None,
        help="Output export format (e.g. 'svg', 'png', 'pdf', 'eps'). Defaults to 'svg' when exporting groups or full document.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Target output base directory. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--dpi",
        type=float,
        default=229.33,
        help="Rasterization DPI for pixel-based exports (default: 229.33).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview export actions without generating files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display verbose logging during operations.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI execution entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    # Requirement 6: If no arguments or flags are given, print help
    if not argv:
        parser = build_parser()
        parser.print_help()
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    # Dynamic format listing
    if args.list_formats:
        supported = get_supported_formats()
        formatted_list = ", ".join(f".{fmt}" for fmt in supported)
        print(f"Supported Inkscape export formats ({len(supported)}):")
        print(f"  {formatted_list}")
        return 0

    if not args.svg_file:
        parser.print_help()
        return 0

    if not args.svg_file.exists():
        print(
            f"Error: Input SVG file '{args.svg_file}' does not exist.", file=sys.stderr
        )
        return 1

    # Validate output format if specified
    if args.format:
        clean_fmt = args.format.strip().lstrip(".").lower()
        supported = get_supported_formats()
        if clean_fmt not in supported:
            print(
                f"Error: Unsupported export format '{args.format}'.\n"
                f"Allowed formats ({len(supported)}): {', '.join(f'.{f}' for f in supported)}",
                file=sys.stderr,
            )
            return 1

    # Output directory (Requirement 11)
    output_dir = args.output_dir if args.output_dir else Path.cwd()

    # Full document export mode
    if args.full_document:
        fmt = (args.format or "svg").strip().lstrip(".").lower()
        try:
            export_full_document(
                svg_file=args.svg_file,
                fmt=fmt,
                output_base_dir=output_dir,
                dpi=args.dpi,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            action_label = "Would export" if args.dry_run else "Successfully exported"
            print(f"{action_label} full document as '{fmt.lower()}'.")
            return 0
        except Exception as e:
            print(f"Error exporting full document: {e}", file=sys.stderr)
            return 1

    # Parse groups from SVG
    groups = parse_svg_groups(args.svg_file)

    # Requirement 7 & 2: If no flags/options or --list is requested
    is_list_only = args.list or (args.pattern is None and args.format is None)

    if is_list_only:
        # If a filter pattern is also provided with --list, filter tree
        if args.pattern:
            matched = filter_groups(groups, args.pattern)
            print(
                f"Found {len(matched)} matching group(s) for pattern '{args.pattern}':\n"
            )
            for node in matched:
                path_str = " / ".join(node.ancestor_labels + [node.label or node.id])
                print(f"[{node.id}] {path_str}")
        else:
            print(render_group_tree(groups))
        return 0

    # Determine export format
    # Requirement 9: If group provided, but no format provided, default to svg
    # Requirement 10: If format provided, but no group provided, export all top-level groups
    fmt = (args.format or "svg").strip().lstrip(".").lower()
    top_level_default = args.pattern is None and args.format is not None

    targets = filter_groups(groups, args.pattern, top_level_only=top_level_default)

    if not targets:
        print(f"No groups matched pattern '{args.pattern}'.", file=sys.stderr)
        return 1

    print(
        f"Exporting {len(targets)} group(s) as '{fmt.lower()}' to '{output_dir / 'fmt' / fmt.lower()}'..."
    )

    exported_count = 0
    for node in targets:
        try:
            export_group(
                svg_file=args.svg_file,
                node=node,
                fmt=fmt,
                output_base_dir=output_dir,
                dpi=args.dpi,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            exported_count += 1
        except Exception as e:
            print(f"Error exporting [{node.id}] '{node.label}': {e}", file=sys.stderr)
            return 1

    action_label = "Would export" if args.dry_run else "Successfully exported"
    print(f"{action_label} {exported_count} group(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
