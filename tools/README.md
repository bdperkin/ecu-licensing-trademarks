# Tooling & Quality Assurance Suite (`tools/`)

This directory contains automated audit scripts, group extraction utilities, unit tests, and validation dictionaries used to verify the structural integrity, XML correctness, labeling hygiene, and asset exports of the SVG files in this repository.

---

## Directory Contents

```text
tools/
├── audit_svg.py               # Main automated SVG structural and labeling audit tool
├── test_audit_svg.py          # Unit test suite covering all 8 audit check routines
├── export_svg_groups.py       # SVG group hierarchy inspector, tree viewer, and batch exporter
├── test_export_svg_groups.py  # Unit test suite for export_svg_groups.py
├── wordlist.txt               # Approved proper nouns, acronyms, and trademarks for spellchecking
└── duplicates.txt             # Duplicate group label ignore list (0 entries; all labels are globally unique)
```

---

## `audit_svg.py` Overview

`audit_svg.py` is a command-line utility and Python module that inspects Inkscape SVG documents against 8 automated quality checks. It returns an exit code of `0` when all active checks pass cleanly and `1` if any issues are detected.

### The 8 Automated Checks

| # | Check Name | CLI Flag / Identifier | Description |
| :-: | :--- | :--- | :--- |
| **1** | **Missing Labels** | `--missing`, `-c missing` | Detects any canvas `<g>` elements missing an `inkscape:label` attribute. |
| **2** | **Duplicate Labels** | `--duplicates`, `-c duplicates` | Detects non-unique group labels across the SVG. Supports `--strict` to bypass ignore lists and flags unused ignore entries. |
| **3** | **Spelling Errors** | `--spelling`, `-c spelling` | Tokenizes and spellchecks group labels via `pyspellchecker`, referencing `wordlist.txt` for approved proper nouns/acronyms. |
| **4** | **Empty Groups** | `--empty`, `-c empty` | Detects container `<g>` elements that contain zero child objects (0 objects). |
| **5** | **Single-Object Groups** | `--single`, `-c single` | Identifies redundant wrapper `<g>` elements that contain only 1 child object (1 object). |
| **6** | **Label Formatting** | `--formatting`, `-c formatting` | Detects leading/trailing whitespace and multiple consecutive spaces in group labels. |
| **7** | **Numbered Marks** | `--marks`, `-c marks` | Verifies sequential numbering (e.g. `Mark 1` through `Mark 91`) and checks that each mark contains a matching number child (`1`..`91`). |
| **8** | **Ungrouped Elements** | `--ungrouped`, `-c ungrouped` | Detects raw drawable elements (`<path>`, `<rect>`, `<circle>`, etc.) placed directly at the canvas root outside of section groups. |

### CLI Usage & Options

```bash
# Run all 8 checks with summary statistics
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg -s

# Run in strict mode (bypassing duplicate ignore lists)
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --strict -s

# Run specific checks (e.g. formatting and numbered marks)
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg -c formatting marks
```

---

## `export_svg_groups.py` Overview

`export_svg_groups.py` scans an SVG file to inspect, list, filter, and export group elements and hierarchical subtrees into structured directory layouts.

### Key Behaviors

- **No arguments**: Prints help message.
- **File only (`python3 tools/export_svg_groups.py <file.svg>`)**: Prints an ASCII/Unicode hierarchy tree showing all groups with their IDs and labels.
- **Group filtering (`-g`, `--group`, `-p`, `--pattern`)**: Filters groups by exact label, regex (e.g. `^Mark [1-5]$`), or glob (e.g. `Mark *`).
- **Format defaults (`-f`, `--format`)**: Defaults to `svg` when a group filter is supplied. Defaults to exporting all 25 top-level section groups when `--format` is supplied without a group filter.
- **Format discovery (`-F`, `--list-formats`, `--formats`)**: Dynamically queries the local Inkscape CLI and lists all supported export formats.
- **Format validation**: Validates requested formats against dynamically discovered formats and reports allowed formats if unsupported.
- **Full document export (`-a`, `--all`, `--full`, `--document`)**: Exports the entire SVG canvas as-is to `<output_dir>/fmt/<format>/<basename>.<format>`.
- **Verbose logging (`-v`, `--verbose`)**: Enables detailed logging and displays exact subprocess CLI commands and progress.
- **Hierarchy preservation**: Exports into `<output_dir>/fmt/<format>/<ancestor_1>/<ancestor_2>/.../<leaf_name>.<format>` with lowercase hyphenated slugs.

### CLI Usage Examples

```bash
# View all supported Inkscape export formats:
python3 tools/export_svg_groups.py --list-formats

# View hierarchical tree of groups and IDs:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg

# Export a single mark to SVG:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --group "Mark 5"

# Export marks 1 through 5 to PNG format:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --group "^Mark [1-5]$" --format png

# Export the entire document canvas to PNG:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format png

# Export all 25 top-level sections into ./dist:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --format svg --output-dir ./dist
```

---

## Unit Testing

To execute all unit test suites in the `tools/` directory:

```bash
python3 -m unittest discover -s tools
```

---

## Ignore Dictionaries

- **[`wordlist.txt`](wordlist.txt)**: Approved proper nouns, acronyms, and trademark terms:
  `Arrrgh`, `diplo`, `EC`, `Ficklen`, `Greenville`, `Minges`, `NC`, `OLCP`, `PANTONE`, `SPC`.
- **[`duplicates.txt`](duplicates.txt)**: Empty. All 1,045 groups have globally unique labels.
