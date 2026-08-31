# Tooling & Quality Assurance Suite (`tools/`)

This directory contains automated audit scripts, unit tests, and validation dictionaries used to verify the structural integrity, XML correctness, and labeling hygiene of the SVG assets in this repository.

---

## Directory Contents

```text
tools/
├── audit_svg.py         # Main automated SVG structural and labeling audit tool
├── test_audit_svg.py    # Unit test suite covering all 8 audit check routines
├── wordlist.txt         # Approved proper nouns, acronyms, and trademarks for spellchecking
└── duplicates.txt       # Duplicate group label ignore list (0 entries; all labels are globally unique)
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

---

## CLI Usage & Options

```bash
# Run all 8 checks with summary statistics
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg -s

# Run in strict mode (bypassing duplicate ignore lists)
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --strict -s

# Run specific checks (e.g. formatting and numbered marks)
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg -c formatting marks

# Specify custom wordlist or duplicates files
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg -w tools/wordlist.txt -d tools/duplicates.txt
```

### Command-Line Arguments Reference

- `svg_path`: Path to the SVG file to audit.
- `-w, --wordlist`: Path to a custom word list file for spellchecking.
- `-d, --duplicates-list`: Path to a custom duplicate labels ignore file.
- `--strict-duplicates, --strict`: Disables duplicate ignore lists and reports all duplicate labels.
- `-c, --checks`: Space- or comma-separated list of checks to run (`missing`, `duplicates`, `spelling`, `empty`, `single`, `formatting`, `marks`, `ungrouped`, `all`).
- `-s, --stats, --summary`: Prints comprehensive audit statistics and metrics at the end of the run.

---

## Unit Testing (`test_audit_svg.py`)

The unit test suite validates production art sheet compliance and exercises all 8 audit check routines using synthetic SVG test fixtures.

To execute the test suite:

```bash
python3 -m unittest tools/test_audit_svg.py
```

---

## Ignore Dictionaries

- **[`wordlist.txt`](wordlist.txt)**: Contains 10 valid proper nouns, institutional acronyms, and trademark terms:
  `Arrrgh`, `diplo`, `EC`, `Ficklen`, `Greenville`, `Minges`, `NC`, `OLCP`, `PANTONE`, `SPC`.
- **[`duplicates.txt`](duplicates.txt)**: Empty file. Group label disambiguation has achieved 100% global uniqueness across all 1,045 groups in the art sheet SVG.
