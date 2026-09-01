#!/usr/bin/env python3
"""SVG Group Exporter & Hierarchy Inspector.

Scans an SVG file to inspect, list, filter, and export group elements,
hierarchical subtrees, or full documents into structured directory layouts.
"""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import gzip
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import NamedTuple

from lxml import etree

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SVG_NS = "http://www.w3.org/2000/svg"
DEFAULT_TIMEOUT = 120.0

ARCHIVE_FORMATS = {"tar", "zip", "svgz"}

RASTER_CONVERT_FORMATS = {
    "jpg",
    "jpeg",
    "webp",
    "tiff",
    "tif",
    "xcf",
    "gif",
    "bmp",
    "ico",
    "avif",
}


class GroupNode(NamedTuple):
    """Represents a <g> element in the SVG hierarchy."""

    element: etree._Element
    id: str
    label: str
    depth: int
    ancestor_labels: list[str]
    parent_id: str | None


def get_supported_formats(timeout: float = 30.0) -> list[str]:
    """Dynamically query Inkscape CLI for supported export formats.

    Parses the allowed export types from Inkscape's error output when an invalid
    format is supplied to `--export-type`.
    """
    inkscape_path = shutil.which("inkscape")
    if not inkscape_path:
        return ["svg", "png", "pdf", "eps", "ps"]

    try:
        result = subprocess.run(
            [inkscape_path, "--export-type=invalid_format"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
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
    except (subprocess.SubprocessError, OSError):
        pass

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
        raw_tag = str(elem.tag)
        tag = raw_tag.rpartition("}")[2] if "}" in raw_tag else raw_tag
        if tag == "g":
            gid = str(elem.get("id", ""))
            lbl = str(elem.get(f"{{{INKSCAPE_NS}}}label", ""))
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
        raw_top_tag = str(top_elem.tag)
        tag = raw_top_tag.rpartition("}")[2] if "}" in raw_top_tag else raw_top_tag
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

    def _build_tree_lines(parent_id: str | None, prefix: str = "", is_root: bool = True) -> None:
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
    with contextlib.suppress(re.error):
        regex = re.compile(pattern_stripped, re.IGNORECASE)

    for node in nodes:
        target_label = node.label
        target_id = node.id
        is_match = False

        if regex and (regex.search(target_label) or (target_id and regex.search(target_id))):
            is_match = True

        if not is_match and (
            fnmatch.fnmatch(target_label.lower(), pattern_stripped.lower())
            or fnmatch.fnmatch(target_id.lower(), pattern_stripped.lower())
        ):
            is_match = True

        if is_match:
            matched.append(node)

    return matched


def verify_exported_file(
    output_file: Path,
    verbose: bool = False,
    timeout: float = 15.0,
) -> None:
    """Verify that an exported output file exists, is non-empty, and passes sanity validation."""
    if not output_file.exists():
        msg = f"Export failed: Destination file '{output_file}' was not created."
        raise RuntimeError(msg)

    file_size = output_file.stat().st_size
    if file_size == 0:
        msg = f"Export failed: Destination file '{output_file}' was created but is empty (0 bytes)."
        raise RuntimeError(msg)

    # Archive validation
    suffix = output_file.suffix.lower()
    if suffix == ".tar":
        if not tarfile.is_tarfile(output_file):
            msg = f"Exported file '{output_file}' is not a valid tar archive."
            raise RuntimeError(msg)
        if verbose:
            print(f"[VERBOSE] Verified valid tar archive: {output_file}")
        return
    if suffix == ".zip":
        if not zipfile.is_zipfile(output_file):
            msg = f"Exported file '{output_file}' is not a valid zip archive."
            raise RuntimeError(msg)
        if verbose:
            print(f"[VERBOSE] Verified valid zip archive: {output_file}")
        return
    if suffix == ".svgz":
        try:
            with gzip.open(output_file, "rb") as f:
                header = f.read(10)
                if not header:
                    msg = f"Exported svgz file '{output_file}' is empty."
                    raise RuntimeError(msg)
            if verbose:
                print(f"[VERBOSE] Verified valid svgz archive: {output_file}")
            return
        except Exception as e:
            msg = f"Exported file '{output_file}' is not a valid svgz archive: {e}"
            raise RuntimeError(msg) from e
    if suffix == ".xaml":
        try:
            tree = etree.parse(str(output_file))
            root = tree.getroot()
            tag = str(root.tag).rpartition("}")[2] if "}" in str(root.tag) else str(root.tag)
            if tag not in ("ResourceDictionary", "Canvas", "DrawingGroup", "Viewbox"):
                msg = f"Exported XAML file '{output_file}' has unexpected root element '<{tag}>'."
                raise RuntimeError(msg)
            if verbose:
                print(f"[VERBOSE] Verified valid XAML document (<{tag}>): {output_file}")
            return
        except Exception as e:
            msg = f"Exported file '{output_file}' is not a valid XAML document: {e}"
            raise RuntimeError(msg) from e

    # Image validation via ImageMagick
    magick_path = shutil.which("magick") or shutil.which("identify")
    if magick_path:
        cmd = (
            [magick_path, "identify", str(output_file)]
            if "magick" in magick_path
            else [magick_path, str(output_file)]
        )
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            if res.returncode == 0 and verbose:
                print(f"[VERBOSE] ImageMagick sanity check passed: {res.stdout.strip()}")
            elif res.returncode != 0 and verbose:
                # Some vector formats (e.g. hpgl, pov) might not be fully identified by identify
                print(
                    f"[VERBOSE] Note: ImageMagick identify non-zero ({res.returncode}): {res.stderr.strip()}"
                )
        except (subprocess.SubprocessError, OSError):
            pass


def annotate_svg_layers(svg_path: Path, default_label: str = "Layer") -> None:
    """Annotate top-level groups in an SVG with inkscape:groupmode='layer' for layer-aware extensions (e.g. XAML)."""
    tree = etree.parse(str(svg_path))
    root = tree.getroot()
    has_changes = False
    for child in root.iterchildren():
        tag = str(child.tag).rpartition("}")[2] if "}" in str(child.tag) else str(child.tag)
        if tag not in ("defs", "metadata", "namedview") and tag == "g":
            child.set(f"{{{INKSCAPE_NS}}}groupmode", "layer")
            if not child.get(f"{{{INKSCAPE_NS}}}label"):
                child.set(f"{{{INKSCAPE_NS}}}label", default_label)
            has_changes = True
    if has_changes:
        tree.write(str(svg_path), encoding="utf-8", xml_declaration=True)


def remove_mark_number_indicators(
    svg_path: Path,
    output_path: Path | None = None,
    target_group_id: str | None = None,
) -> Path:
    """Remove child number indicator groups (e.g. child group labeled '45' from 'Mark 45') from an SVG document.

    If target_group_id is provided, only the indicator child of that specific group is removed.
    Otherwise, indicator children of all 'Mark <N>' groups across the SVG are removed.
    """
    tree = etree.parse(str(svg_path))
    root = tree.getroot()
    inkscape_label_attr = f"{{{INKSCAPE_NS}}}label"

    removals: list[tuple[etree._Element, etree._Element]] = []
    for elem in list(root.iter()):
        tag = str(elem.tag).rpartition("}")[2] if "}" in str(elem.tag) else str(elem.tag)
        if tag != "g":
            continue

        label = elem.get(inkscape_label_attr)
        if not label:
            continue

        m = re.match(r"^Mark\s+(\d+)$", label.strip(), re.IGNORECASE)
        if not m:
            continue

        if target_group_id is not None and elem.get("id") != target_group_id:
            continue

        num_str = m.group(1)
        for child in list(elem):
            child_label = child.get(inkscape_label_attr)
            if child_label == num_str:
                removals.append((elem, child))

    for parent, child in removals:
        parent.remove(child)

    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            output_path = Path(tmp_svg.name)

    tree.write(str(output_path), encoding="utf-8", xml_declaration=True)
    return output_path


def export_group(
    svg_file: Path,
    node: GroupNode,
    fmt: str,
    output_base_dir: Path,
    dpi: float = 229.33,
    timeout: float = DEFAULT_TIMEOUT,
    dry_run: bool = False,
    verbose: bool = False,
    no_mark_numbers: bool = False,
) -> Path:
    # 1. Format directory: <output_base_dir>/fmt/<format>/
    fmt_clean = fmt.strip().lstrip(".").lower()
    fmt_dir = output_base_dir / "fmt" / fmt_clean

    # 2. Ancestor directories: <output_base_dir>/fmt/<format>/<ancestor_1>/<ancestor_2>/...
    ancestor_path_parts = [normalize_slug(a) for a in node.ancestor_labels]
    target_dir = fmt_dir.joinpath(*ancestor_path_parts) if ancestor_path_parts else fmt_dir

    # 3. Leaf filename: <leaf_label>.<fmt>
    leaf_name = normalize_slug(node.label or node.id)
    output_file = target_dir / f"{leaf_name}.{fmt_clean}"

    if not dry_run:
        inkscape_path = shutil.which("inkscape")
        if not inkscape_path:
            msg = "Inkscape CLI executable ('inkscape') is required for exporting groups."
            raise RuntimeError(msg)

        magick_path = shutil.which("magick") or shutil.which("convert")
        target_dir.mkdir(parents=True, exist_ok=True)

        active_svg = svg_file
        tmp_cleaned_svg: Path | None = None
        if no_mark_numbers:
            tmp_cleaned_svg = remove_mark_number_indicators(svg_file, target_group_id=node.id)
            active_svg = tmp_cleaned_svg
            if verbose:
                print(f"[VERBOSE] Removed mark number indicator for [{node.id}] '{node.label}'")

        try:
            if fmt_clean in ("svg", "png", "pdf", "eps", "ps"):
                # Native C++ direct export
                cmd = [
                    inkscape_path,
                    str(active_svg),
                    f"--export-id={node.id}",
                    "--export-id-only",
                    f"--export-filename={output_file}",
                ]

                if fmt_clean == "svg":
                    cmd.append("--export-plain-svg")
                elif fmt_clean == "png":
                    cmd.append(f"--export-dpi={dpi}")

                if verbose:
                    print(f"[VERBOSE] Running: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired as e:
                    msg = (
                        f"Export of group '{node.id}' ({node.label}) timed out "
                        f"after {timeout} seconds: {' '.join(cmd)}"
                    )
                    raise RuntimeError(msg) from e

                if verbose and result.stdout:
                    print(result.stdout)
                if verbose and result.stderr:
                    print(result.stderr, file=sys.stderr)

                if result.returncode != 0:
                    msg = (
                        f"Failed to export group '{node.id}' ({node.label}) "
                        f"to {output_file} (exit code {result.returncode}):\n{result.stderr}"
                    )
                    raise RuntimeError(msg)

            elif fmt_clean in RASTER_CONVERT_FORMATS and magick_path:
                # High-fidelity raster pipeline: Render isolated PNG with Cairo -> Convert via ImageMagick
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
                    tmp_png_path = Path(tmp_png.name)

                try:
                    render_cmd = [
                        inkscape_path,
                        str(active_svg),
                        f"--export-id={node.id}",
                        "--export-id-only",
                        f"--export-dpi={dpi}",
                        f"--export-filename={tmp_png_path}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Rendering intermediate PNG: {' '.join(render_cmd)}")

                    try:
                        render_res = subprocess.run(
                            render_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Raster render of group '{node.id}' ({node.label}) timed out "
                            f"after {timeout} seconds: {' '.join(render_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if (
                        render_res.returncode != 0
                        or not tmp_png_path.exists()
                        or tmp_png_path.stat().st_size == 0
                    ):
                        msg = f"Failed to render intermediate PNG for group '{node.id}' ({node.label}):\n{render_res.stderr}"
                        raise RuntimeError(msg)

                    # Convert PNG to target raster format via ImageMagick
                    convert_cmd = [magick_path, str(tmp_png_path), str(output_file)]
                    if verbose:
                        print(f"[VERBOSE] Converting raster image: {' '.join(convert_cmd)}")

                    try:
                        conv_res = subprocess.run(
                            convert_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"ImageMagick conversion of '{node.id}' timed out "
                            f"after {timeout} seconds: {' '.join(convert_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if conv_res.returncode != 0:
                        msg = f"ImageMagick failed to convert '{tmp_png_path}' to '{output_file}':\n{conv_res.stderr}"
                        raise RuntimeError(msg)
                finally:
                    if tmp_png_path.exists():
                        tmp_png_path.unlink()

            elif fmt_clean in ARCHIVE_FORMATS:
                # Package isolated SVG into archive
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
                    tmp_svg_path = Path(tmp_svg.name)

                try:
                    extract_cmd = [
                        inkscape_path,
                        str(active_svg),
                        f"--export-id={node.id}",
                        "--export-id-only",
                        "--export-plain-svg",
                        f"--export-filename={tmp_svg_path}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Isolating group SVG: {' '.join(extract_cmd)}")

                    try:
                        extract_res = subprocess.run(
                            extract_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Isolation of group '{node.id}' ({node.label}) timed out "
                            f"after {timeout} seconds: {' '.join(extract_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if (
                        extract_res.returncode != 0
                        or not tmp_svg_path.exists()
                        or tmp_svg_path.stat().st_size == 0
                    ):
                        msg = (
                            f"Failed to isolate group '{node.id}' ({node.label}) "
                            f"to temporary SVG:\n{extract_res.stderr}"
                        )
                        raise RuntimeError(msg)

                    if fmt_clean == "tar":
                        with tarfile.open(output_file, "w") as tar:
                            tar.add(tmp_svg_path, arcname=f"{leaf_name}.svg")
                    elif fmt_clean == "zip":
                        with zipfile.ZipFile(
                            output_file, "w", compression=zipfile.ZIP_DEFLATED
                        ) as zf:
                            zf.write(tmp_svg_path, arcname=f"{leaf_name}.svg")
                    elif fmt_clean == "svgz":
                        with tmp_svg_path.open("rb") as f_in, gzip.open(output_file, "wb") as f_out:
                            f_out.writelines(f_in)
                finally:
                    if tmp_svg_path.exists():
                        tmp_svg_path.unlink()

            else:
                # Two-step export for extension/script formats (e.g. hpgl, dxf, tex, pov, sif, etc.)
                # Step 1: Extract isolated SVG sub-tree
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
                    tmp_svg_path = Path(tmp_svg.name)

                try:
                    extract_cmd = [
                        inkscape_path,
                        str(active_svg),
                        f"--export-id={node.id}",
                        "--export-id-only",
                        "--export-plain-svg",
                        f"--export-filename={tmp_svg_path}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Isolating group SVG: {' '.join(extract_cmd)}")

                    try:
                        extract_res = subprocess.run(
                            extract_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Isolation of group '{node.id}' ({node.label}) timed out "
                            f"after {timeout} seconds: {' '.join(extract_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if (
                        extract_res.returncode != 0
                        or not tmp_svg_path.exists()
                        or tmp_svg_path.stat().st_size == 0
                    ):
                        msg = (
                            f"Failed to isolate group '{node.id}' ({node.label}) "
                            f"to temporary SVG:\n{extract_res.stderr}"
                        )
                        raise RuntimeError(msg)

                    # Step 1.5: If format is XAML, annotate the isolated group with inkscape:groupmode="layer"
                    if fmt_clean == "xaml":
                        annotate_svg_layers(tmp_svg_path, default_label=node.label or node.id)

                    # Step 2: Convert isolated SVG to target format
                    convert_cmd = [
                        inkscape_path,
                        str(tmp_svg_path),
                        f"--export-filename={output_file}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Converting isolated SVG: {' '.join(convert_cmd)}")

                    try:
                        convert_res = subprocess.run(
                            convert_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Conversion of isolated group '{node.id}' ({node.label}) timed out "
                            f"after {timeout} seconds: {' '.join(convert_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if verbose and convert_res.stdout:
                        print(convert_res.stdout)
                    if verbose and convert_res.stderr:
                        print(convert_res.stderr, file=sys.stderr)

                    if (
                        convert_res.returncode != 0
                        or "Failed to save" in convert_res.stderr
                        or "Script Error" in convert_res.stderr
                    ):
                        msg = (
                            f"Failed to export isolated group '{node.id}' ({node.label}) "
                            f"to {output_file}:\n{convert_res.stderr}"
                        )
                        raise RuntimeError(msg)
                finally:
                    if tmp_svg_path.exists():
                        tmp_svg_path.unlink()
        finally:
            if tmp_cleaned_svg and tmp_cleaned_svg.exists():
                tmp_cleaned_svg.unlink()

        # Post-export file verification and sanity checking
        verify_exported_file(output_file, verbose=verbose, timeout=timeout)

    if verbose or dry_run:
        prefix = "[DRY-RUN] Would export" if dry_run else "Exported"
        print(f'{prefix}: [{node.id}] "{node.label}" -> {output_file}')

    return output_file


def export_full_document(
    svg_file: Path,
    fmt: str,
    output_base_dir: Path,
    dpi: float = 229.33,
    timeout: float = DEFAULT_TIMEOUT,
    dry_run: bool = False,
    verbose: bool = False,
    no_mark_numbers: bool = False,
) -> Path:
    # 1. Format directory: <output_base_dir>/fmt/<format>/
    fmt_clean = fmt.strip().lstrip(".").lower()
    fmt_dir = output_base_dir / "fmt" / fmt_clean

    # 2. Output file: <output_base_dir>/fmt/<format>/<svg_file.stem>.<format>
    output_file = fmt_dir / f"{svg_file.stem}.{fmt_clean}"

    if not dry_run:
        inkscape_path = shutil.which("inkscape")
        if not inkscape_path:
            msg = "Inkscape CLI executable ('inkscape') is required for document export."
            raise RuntimeError(msg)

        magick_path = shutil.which("magick") or shutil.which("convert")
        fmt_dir.mkdir(parents=True, exist_ok=True)

        active_svg = svg_file
        tmp_cleaned_svg: Path | None = None
        if no_mark_numbers:
            tmp_cleaned_svg = remove_mark_number_indicators(svg_file)
            active_svg = tmp_cleaned_svg
            if verbose:
                print("[VERBOSE] Removed mark number indicators from full document")

        try:
            if fmt_clean in ("svg", "png", "pdf", "eps", "ps"):
                cmd = [
                    inkscape_path,
                    str(active_svg),
                    f"--export-filename={output_file}",
                ]

                if fmt_clean == "svg":
                    cmd.append("--export-plain-svg")
                elif fmt_clean == "png":
                    cmd.append(f"--export-dpi={dpi}")

                if verbose:
                    print(f"[VERBOSE] Running: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired as e:
                    msg = (
                        f"Export of full document '{svg_file.name}' timed out "
                        f"after {timeout} seconds: {' '.join(cmd)}"
                    )
                    raise RuntimeError(msg) from e

                if verbose and result.stdout:
                    print(result.stdout)
                if verbose and result.stderr:
                    print(result.stderr, file=sys.stderr)

                if result.returncode != 0:
                    msg = (
                        f"Failed to export full document '{svg_file}' "
                        f"to {output_file} (exit code {result.returncode}):\n{result.stderr}"
                    )
                    raise RuntimeError(msg)

            elif fmt_clean in RASTER_CONVERT_FORMATS and magick_path:
                # High-fidelity raster pipeline for full document
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
                    tmp_png_path = Path(tmp_png.name)

                try:
                    render_cmd = [
                        inkscape_path,
                        str(active_svg),
                        f"--export-dpi={dpi}",
                        f"--export-filename={tmp_png_path}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Rendering full document PNG: {' '.join(render_cmd)}")

                    try:
                        render_res = subprocess.run(
                            render_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Full document PNG render timed out "
                            f"after {timeout} seconds: {' '.join(render_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if (
                        render_res.returncode != 0
                        or not tmp_png_path.exists()
                        or tmp_png_path.stat().st_size == 0
                    ):
                        msg = f"Failed to render full document PNG:\n{render_res.stderr}"
                        raise RuntimeError(msg)

                    convert_cmd = [magick_path, str(tmp_png_path), str(output_file)]
                    if verbose:
                        print(
                            f"[VERBOSE] Converting full document raster image: {' '.join(convert_cmd)}"
                        )

                    try:
                        conv_res = subprocess.run(
                            convert_cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"ImageMagick full document conversion timed out "
                            f"after {timeout} seconds: {' '.join(convert_cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if conv_res.returncode != 0:
                        msg = f"ImageMagick failed to convert '{tmp_png_path}' to '{output_file}':\n{conv_res.stderr}"
                        raise RuntimeError(msg)
                finally:
                    if tmp_png_path.exists():
                        tmp_png_path.unlink()

            elif fmt_clean in ARCHIVE_FORMATS:
                if fmt_clean == "tar":
                    with tarfile.open(output_file, "w") as tar:
                        tar.add(active_svg, arcname=f"{svg_file.stem}.svg")
                elif fmt_clean == "zip":
                    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.write(active_svg, arcname=f"{svg_file.stem}.svg")
                elif fmt_clean == "svgz":
                    with active_svg.open("rb") as f_in, gzip.open(output_file, "wb") as f_out:
                        f_out.writelines(f_in)

            elif fmt_clean == "xaml":
                # XAML extension requires layers for resources; annotate copy of document
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
                    tmp_svg_path = Path(tmp_svg.name)
                try:
                    shutil.copy2(active_svg, tmp_svg_path)
                    annotate_svg_layers(tmp_svg_path, default_label=svg_file.stem)
                    cmd = [
                        inkscape_path,
                        str(tmp_svg_path),
                        f"--export-filename={output_file}",
                    ]
                    if verbose:
                        print(f"[VERBOSE] Running: {' '.join(cmd)}")

                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=timeout,
                        )
                    except subprocess.TimeoutExpired as e:
                        msg = (
                            f"Export of full document '{svg_file.name}' timed out "
                            f"after {timeout} seconds: {' '.join(cmd)}"
                        )
                        raise RuntimeError(msg) from e

                    if verbose and result.stdout:
                        print(result.stdout)
                    if verbose and result.stderr:
                        print(result.stderr, file=sys.stderr)

                    if (
                        result.returncode != 0
                        or "Failed to save" in result.stderr
                        or "Script Error" in result.stderr
                    ):
                        msg = (
                            f"Failed to export full document '{svg_file}' "
                            f"to {output_file}:\n{result.stderr}"
                        )
                        raise RuntimeError(msg)
                finally:
                    if tmp_svg_path.exists():
                        tmp_svg_path.unlink()

            else:
                # Fallback direct invocation for other formats
                cmd = [
                    inkscape_path,
                    str(active_svg),
                    f"--export-filename={output_file}",
                ]

                if verbose:
                    print(f"[VERBOSE] Running: {' '.join(cmd)}")

                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired as e:
                    msg = (
                        f"Export of full document '{svg_file.name}' timed out "
                        f"after {timeout} seconds: {' '.join(cmd)}"
                    )
                    raise RuntimeError(msg) from e

                if verbose and result.stdout:
                    print(result.stdout)
                if verbose and result.stderr:
                    print(result.stderr, file=sys.stderr)

                if (
                    result.returncode != 0
                    or "Failed to save" in result.stderr
                    or "Script Error" in result.stderr
                ):
                    msg = (
                        f"Failed to export full document '{svg_file}' "
                        f"to {output_file}:\n{result.stderr}"
                    )
                    raise RuntimeError(msg)
        finally:
            if tmp_cleaned_svg and tmp_cleaned_svg.exists():
                tmp_cleaned_svg.unlink()

        # Post-export file verification and sanity checking
        verify_exported_file(output_file, verbose=verbose, timeout=timeout)

    if verbose or dry_run:
        prefix = "[DRY-RUN] Would export full document" if dry_run else "Exported full document"
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

  # Export mark 45 without its number indicator badge:
  python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --group "Mark 45" --no-mark-numbers

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
        help="Output export format (e.g. 'svg', 'png', 'pdf', 'eps', 'jpg', 'webp', 'tiff', 'tar', 'zip', 'svgz'). Defaults to 'svg'.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Target output base directory. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--no-mark-numbers",
        "--hide-mark-numbers",
        "--no-mark-indicators",
        "--hide-mark-indicators",
        "--no-indicators",
        dest="no_mark_numbers",
        action="store_true",
        default=False,
        help="Turn off / remove child mark number identifier groups (e.g. child group labeled '45' in 'Mark 45') before export.",
    )
    parser.add_argument(
        "--dpi",
        type=float,
        default=229.33,
        help="Rasterization DPI for pixel-based exports (default: 229.33).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Execution timeout in seconds for individual Inkscape export operations (default: {DEFAULT_TIMEOUT}s).",
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
        supported = get_supported_formats(timeout=args.timeout)
        formatted_list = ", ".join(f".{fmt}" for fmt in supported)
        print(f"Supported Inkscape export formats ({len(supported)}):")
        print(f"  {formatted_list}")
        return 0

    if not args.svg_file:
        parser.print_help()
        return 0

    if not args.svg_file.exists():
        print(f"Error: Input SVG file '{args.svg_file}' does not exist.", file=sys.stderr)
        return 1

    # Validate output format if specified
    if args.format:
        clean_fmt = args.format.strip().lstrip(".").lower()
        supported = get_supported_formats(timeout=args.timeout)
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
                timeout=args.timeout,
                dry_run=args.dry_run,
                verbose=args.verbose,
                no_mark_numbers=args.no_mark_numbers,
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
            print(f"Found {len(matched)} matching group(s) for pattern '{args.pattern}':\n")
            for node in matched:
                path_str = " / ".join([*node.ancestor_labels, node.label or node.id])
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

    source_svg = args.svg_file
    cleaned_temp_svg: Path | None = None
    if args.no_mark_numbers and not args.dry_run:
        cleaned_temp_svg = remove_mark_number_indicators(args.svg_file)
        source_svg = cleaned_temp_svg

    exported_count = 0
    try:
        for node in targets:
            try:
                export_group(
                    svg_file=source_svg,
                    node=node,
                    fmt=fmt,
                    output_base_dir=output_dir,
                    dpi=args.dpi,
                    timeout=args.timeout,
                    dry_run=args.dry_run,
                    verbose=args.verbose,
                    no_mark_numbers=False,
                )
                exported_count += 1
            except Exception as e:
                print(f"Error exporting [{node.id}] '{node.label}': {e}", file=sys.stderr)
                return 1
    finally:
        if cleaned_temp_svg and cleaned_temp_svg.exists():
            cleaned_temp_svg.unlink(missing_ok=True)

    action_label = "Would export" if args.dry_run else "Successfully exported"
    print(f"{action_label} {exported_count} group(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
