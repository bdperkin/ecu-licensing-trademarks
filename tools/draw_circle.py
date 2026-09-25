#!/usr/bin/env python3
"""
draw-circle.py

Extracts shapes and paths from an SVG file, computes the precise minimum enclosing
circle (bounding circle), and inserts a 50% opacity grey circle as a sibling to the
specified target element with the label "(bounding circle)".

Usage:
    # 1. List contents in tree format:
    python3 draw-circle.py <svg_file>

    # 2. Draw bounding circle around a group/object/path:
    python3 draw-circle.py <svg_file> <target_id_or_label>

    # Optional flags:
    python3 draw-circle.py <svg_file> <target> -o <output_file>
    python3 draw-circle.py <svg_file> <target> --position [after|before]
    python3 draw-circle.py <svg_file> --show-defs
"""

import argparse
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import smallestenclosingcircle
from svgpathtools.document import CONVERSIONS
from svgpathtools.parser import parse_path, parse_transform
from svgpathtools.path import transform

try:
    from scipy.spatial import ConvexHull

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SVG_NS = "http://www.w3.org/2000/svg"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"


def register_svg_namespaces(svg_path: str):
    """
    Scans the SVG for declared namespaces and registers them with ElementTree
    so that existing prefixes (e.g. inkscape, sodipodi) and the default SVG
    namespace are properly preserved when writing back to disk.
    """
    namespaces = {}
    for _event, elem in ET.iterparse(svg_path, events=["start-ns"]):
        prefix, uri = elem
        namespaces[prefix] = uri

    for prefix, uri in namespaces.items():
        if uri == SVG_NS and prefix != "":
            continue
        ET.register_namespace(prefix, uri)

    if SVG_NS in namespaces.values() or "" not in namespaces:
        ET.register_namespace("", SVG_NS)

    if "inkscape" not in namespaces:
        ET.register_namespace("inkscape", INKSCAPE_NS)
    if "sodipodi" not in namespaces:
        ET.register_namespace("sodipodi", SODIPODI_NS)


def get_element_label(elem: ET.Element) -> str:
    """Returns the Inkscape or SVG label of an element if present."""
    return elem.attrib.get(f"{{{INKSCAPE_NS}}}label") or elem.attrib.get("label", "")


def get_element_display_name(elem: ET.Element) -> str:
    """Formats an element tag, label, and ID for tree display."""
    tag = elem.tag.split("}")[-1]
    eid = elem.attrib.get("id", "")
    label = get_element_label(elem)
    parts = [tag]
    if label:
        parts.append(f'"{label}"')
    if eid:
        parts.append(f"(id: {eid})")
    return " ".join(parts)


def print_svg_tree(
    elem: ET.Element,
    prefix: str = "",
    is_last: bool = True,
    is_root: bool = True,
    show_defs: bool = False,
):
    """Recursively prints the SVG hierarchy in a tree format."""
    tag = elem.tag.split("}")[-1]
    line = get_element_display_name(elem)

    if is_root:
        print(line)
    else:
        connector = "└── " if is_last else "├── "
        print(prefix + connector + line)

    # Collapse defs if large unless user requested --show-defs
    if tag == "defs" and not show_defs:
        sub_count = len(list(elem.iter())) - 1
        if sub_count > 10:
            sub_prefix = prefix + ("    " if is_last else "│   ")
            print(
                f"{sub_prefix}└── [{sub_count} definition elements hidden; use --show-defs to expand]"
            )
            return

    # Filter out editor-only metadata nodes (namedview, metadata)
    children = [c for c in elem if c.tag.split("}")[-1] not in ["metadata", "namedview"]]
    new_prefix = prefix + ("    " if is_last else "│   ") if not is_root else ""
    for i, child in enumerate(children):
        print_svg_tree(
            child,
            prefix=new_prefix,
            is_last=(i == len(children) - 1),
            is_root=False,
            show_defs=show_defs,
        )


def find_target_element(root: ET.Element, target: str):
    """
    Locates an element in the SVG tree matching the target by:
    1. Exact ID match
    2. Exact Label match
    3. Case-insensitive ID or Label match
    """
    # 1. Exact ID
    by_id = [e for e in root.iter() if e.attrib.get("id") == target]
    if by_id:
        return by_id[0]

    # 2. Exact Label
    by_label = [e for e in root.iter() if get_element_label(e) == target]
    if len(by_label) == 1:
        return by_label[0]
    elif len(by_label) > 1:
        print(
            f"Error: Ambiguous target '{target}'. Multiple elements match this label:",
            file=sys.stderr,
        )
        for e in by_label:
            tag = e.tag.split("}")[-1]
            eid = e.attrib.get("id", "<no id>")
            print(f"  - {tag} (id: {eid})", file=sys.stderr)
        print("Please specify the exact element ID instead.", file=sys.stderr)
        sys.exit(1)

    # 3. Case-insensitive ID match
    target_lower = target.lower()
    by_id_ci = [e for e in root.iter() if e.attrib.get("id", "").lower() == target_lower]
    if len(by_id_ci) == 1:
        return by_id_ci[0]

    # 4. Case-insensitive Label match
    by_label_ci = [e for e in root.iter() if get_element_label(e).lower() == target_lower]
    if len(by_label_ci) == 1:
        return by_label_ci[0]
    elif len(by_label_ci) > 1:
        print(
            f"Error: Ambiguous target '{target}'. Multiple elements match case-insensitively:",
            file=sys.stderr,
        )
        for e in by_label_ci:
            tag = e.tag.split("}")[-1]
            eid = e.attrib.get("id", "<no id>")
            lbl = get_element_label(e)
            print(f'  - {tag} "{lbl}" (id: {eid})', file=sys.stderr)
        print("Please specify the exact element ID instead.", file=sys.stderr)
        sys.exit(1)

    return None


def collect_paths_in_parent_frame(elem: ET.Element, current_matrix: np.ndarray) -> list:
    """
    Recursively traverses an element subtree, accumulating transformations
    and converting all shapes (path, rect, circle, ellipse, line, polyline,
    polygon, image) into path objects expressed in the coordinate frame of
    the target's parent.
    """
    tf_str = elem.attrib.get("transform")
    if tf_str:
        try:
            m_matrix = current_matrix.dot(parse_transform(tf_str))
        except Exception:
            m_matrix = current_matrix
    else:
        m_matrix = current_matrix

    tag = elem.tag.split("}")[-1]
    paths = []

    if tag in CONVERSIONS:
        try:
            d = CONVERSIONS[tag](elem)
            if d and d.strip():
                p = parse_path(d)
                paths.append(transform(p, m_matrix))
        except Exception as err:
            print(
                f'Warning: Could not convert shape <{tag} id="{elem.attrib.get("id")}">: {err}',
                file=sys.stderr,
            )
    elif tag == "image":
        try:
            x = float(elem.attrib.get("x", 0))
            y = float(elem.attrib.get("y", 0))
            w = float(elem.attrib.get("width", 0))
            h = float(elem.attrib.get("height", 0))
            if w > 0 and h > 0:
                p = parse_path(f"M {x} {y} h {w} v {h} h {-w} Z")
                paths.append(transform(p, m_matrix))
        except Exception as err:
            print(
                f'Warning: Could not process image <image id="{elem.attrib.get("id")}">: {err}',
                file=sys.stderr,
            )

    for child in elem:
        paths.extend(collect_paths_in_parent_frame(child, m_matrix))

    return paths


def sample_path_points(paths: list, sample_density: int = 200) -> list:
    """
    Extracts all segment start/end nodes and samples points along the perimeter
    curves to ensure the geometry's outer envelope is completely captured.
    """
    points = []
    for path in paths:
        # 1. Add all segment endpoints (nodes)
        for seg in path:
            points.append((seg.start.real, seg.start.imag))
            points.append((seg.end.real, seg.end.imag))

        # 2. Sample along perimeter curves
        if len(path) > 0 and sample_density > 0:
            for i in range(sample_density):
                t = i / float(sample_density)
                try:
                    pt = path.point(t)
                    points.append((pt.real, pt.imag))
                except Exception:
                    pass

    return points


def calculate_bounding_circle(points: list):
    """
    Calculates the exact minimum enclosing circle using Welzl's algorithm.
    Uses 2D Convex Hull vertices when available to accelerate calculation on
    complex geometries with thousands of points.
    """
    if not points:
        return None

    # Filter distinct points
    unique_points = list({(round(p[0], 6), round(p[1], 6)): p for p in points}.values())

    if len(unique_points) == 1:
        return unique_points[0][0], unique_points[0][1], 0.0

    # Accelerate using ConvexHull if scipy is installed and point set is non-trivial
    if HAS_SCIPY and len(unique_points) >= 10:
        pts_arr = np.array(unique_points, dtype=np.float64)
        try:
            hull = ConvexHull(pts_arr)
            hull_pts = [(pts_arr[v, 0], pts_arr[v, 1]) for v in hull.vertices]
            random.Random(42).shuffle(hull_pts)
            return smallestenclosingcircle.make_circle(hull_pts)
        except Exception:
            pass

    pts = list(unique_points)
    random.Random(42).shuffle(pts)
    return smallestenclosingcircle.make_circle(pts)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate and draw the minimum enclosing circle for an SVG element, "
            "or list the SVG hierarchy in tree format."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # List all groups, objects, and paths in the SVG:
  python3 draw-circle.py drawing.svg

  # Draw bounding circle around group 'g1' and save in-place:
  python3 draw-circle.py drawing.svg g1

  # Draw bounding circle around object with label 'Legacy Mark' to output file:
  python3 draw-circle.py drawing.svg "Legacy Mark" -o output.svg
""",
    )
    parser.add_argument("svg_file", help="Path to the input SVG file (required)")
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help=(
            "ID or label of the group/object/path/etc. to enclose. If omitted, "
            "the contents of the SVG are listed in tree format."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Path to save the modified SVG (default: overwrite input SVG file)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=200,
        help="Number of perimeter sample points per path (default: 200)",
    )
    parser.add_argument(
        "--show-defs",
        action="store_true",
        help="Expand all elements inside <defs> when listing tree format",
    )
    parser.add_argument(
        "--position",
        choices=["after", "before"],
        default="after",
        help="Insert the sibling circle 'after' (default) or 'before' the target element",
    )

    args = parser.parse_args()

    if not Path(args.svg_file).is_file():
        print(f"Error: File '{args.svg_file}' not found.", file=sys.stderr)
        sys.exit(1)

    register_svg_namespaces(args.svg_file)

    try:
        tree = ET.parse(args.svg_file)
        root = tree.getroot()
    except ET.ParseError as err:
        print(f"Error parsing SVG XML in '{args.svg_file}': {err}", file=sys.stderr)
        sys.exit(1)

    # 1. If target is not provided: list SVG contents in tree format
    if args.target is None:
        print_svg_tree(root, show_defs=args.show_defs)
        print("\nTip: To draw a bounding circle around any element, run:")
        print(f"  python3 {Path(sys.argv[0]).name} {args.svg_file} <id_or_label>")
        return

    # 2. Target is provided: find target element
    target_elem = find_target_element(root, args.target)
    if target_elem is None:
        print(f"Error: Element '{args.target}' not found in '{args.svg_file}'.", file=sys.stderr)
        print(
            f"Run 'python3 {Path(sys.argv[0]).name} {args.svg_file}' to view available elements.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build parent mapping
    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map.get(target_elem)
    if parent is None:
        print(
            f"Error: Cannot draw a sibling circle to the root <{root.tag.split('}')[-1]}> element.",
            file=sys.stderr,
        )
        sys.exit(1)

    target_id = target_elem.attrib.get("id") or "target"
    target_label = get_element_label(target_elem)
    target_tag = target_elem.tag.split("}")[-1]

    # Collect paths within target, transformed into parent's coordinate frame
    paths = collect_paths_in_parent_frame(target_elem, np.identity(3))
    if not paths:
        print(
            f'Error: No drawable paths or shapes found inside <{target_tag} id="{target_id}">.',
            file=sys.stderr,
        )
        sys.exit(1)

    # Sample perimeter points and nodes
    points = sample_path_points(paths, sample_density=args.samples)
    if not points:
        print(
            f'Error: Could not extract sample points from paths in <{target_tag} id="{target_id}">.',
            file=sys.stderr,
        )
        sys.exit(1)

    # Compute precise minimum enclosing circle
    circle_res = calculate_bounding_circle(points)
    if circle_res is None:
        print("Error: Could not calculate bounding circle.", file=sys.stderr)
        sys.exit(1)

    center_x, center_y, radius = circle_res

    # Output calculation metrics
    label_suffix = f' label="{target_label}"' if target_label else ""
    print(f'Target Element:  <{target_tag} id="{target_id}"{label_suffix}>')
    print(f"Circle Center X: {center_x:.4f}")
    print(f"Circle Center Y: {center_y:.4f}")
    print(f"Circle Radius:   {radius:.4f}")
    print(f"Circle Diameter: {radius * 2:.4f}")

    # Remove any existing bounding circle sibling for this target to prevent duplicates
    circle_id = f"{target_id}-bounding-circle"
    for sibling in list(parent):
        if sibling.attrib.get("id") == circle_id:
            parent.remove(sibling)

    # Create the 50% opacity grey circle element with label "(bounding circle)"
    circle_attrib = {
        "id": circle_id,
        "cx": f"{center_x:.6f}".rstrip("0").rstrip("."),
        "cy": f"{center_y:.6f}".rstrip("0").rstrip("."),
        "r": f"{radius:.6f}".rstrip("0").rstrip("."),
        "fill": "gray",
        "fill-opacity": "0.5",
        "stroke": "none",
        "style": "display:none;fill:gray;fill-opacity:0.5;stroke:none;",
        f"{{{INKSCAPE_NS}}}label": "(bounding circle)",
        "label": "(bounding circle)",
    }
    circle_elem = ET.Element(f"{{{SVG_NS}}}circle", circle_attrib)
    title_elem = ET.SubElement(circle_elem, f"{{{SVG_NS}}}title")
    title_elem.text = "(bounding circle)"

    # Insert circle as sibling
    target_idx = list(parent).index(target_elem)
    if args.position == "before":
        parent.insert(target_idx, circle_elem)
    else:
        parent.insert(target_idx + 1, circle_elem)

    # Save modified SVG
    output_path = args.output if args.output else args.svg_file
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"Successfully drawn sibling circle '{circle_id}' saved to '{output_path}'.")


if __name__ == "__main__":
    main()
