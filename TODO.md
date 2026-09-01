# ECU Art Sheet Review & Task Tracker

Comprehensive status, architectural review, and task tracking for the East Carolina University Trademark Licensing Art Sheet SVG ([`src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg`](src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg)).

---

## Executive Summary & Current Health

- **Total Canvas Groups**: `1,045`
- **Label Coverage**: **100%** (1,045 of 1,045 groups labeled, 0 missing labels)
- **Top-Level Sections**: `25` logical sections organized across 3 pages
- **Audit Tool Status (8 Automated Checks)**:
  - `0` missing label errors (Check 1: `missing`)
  - `0` duplicate label errors (Check 2: `duplicates`)
  - `0` spelling errors (Check 3: `spelling` - 10 proper nouns / acronyms in `tools/wordlist.txt`)
  - `0` empty groups (Check 4: `empty`)
  - `0` single-object groups (Check 5: `single`)
  - `0` label formatting defects (Check 6: `formatting`)
  - `91` numbered marks verified sequentially with indicator groups (Check 7: `marks`)
  - `0` ungrouped / stranded elements at canvas root (Check 8: `ungrouped`)
  - `0` unused entries in ignore lists

---

## Top-Level Section Architecture

| Page | Section Label | Description | Sub-Groups |
| :--- | :--- | :--- | :---: |
| **Page 1** | `Page 1 Title` | Title block (OLCP Logo, ECU header, revision date) | 5 |
| | `Information Section` | Location, Mascot, Established, Conference details | 17 |
| | `Verbiage Section` | 4-column approved verbiage list | 39 |
| | `Colors Section` | Palette swatches, CMYK/RGB values, PANTONE guidelines | 57 |
| | `Primary Mark` | Marks 1–7 (Skull & Crossbones primary marks) | 36 |
| | `Primary Word Mark` | Marks 8–14 (ECU word marks & color column titles) | 84 |
| | `Secondary Word Mark` | Marks 15–21 (Pirates word marks) | 68 |
| | `Additional Word Marks`| Marks 22–35 (East Carolina word marks) | 208 |
| | `Page 1 Footer` | Table guidelines footer cells (`Note`, `Marks`, `Use`) | 7 |
| **Page 2** | `Page 2 Title` | Title block | 5 |
| | `Sport Specific Marks` | Marks 36–50 (Sport lockups & guideline text) | 103 |
| | `Pirate State of Mind Marks` | Marks 51–53 | 13 |
| | `Script Pirates` | Marks 54–55 | 8 |
| | `PeeDee Mark` | Marks 56–57 | 11 |
| | `Helmet Mark` | Mark 58 | 7 |
| | `No Quarter Mark` | Mark 59 & letters A–Z | 23 |
| | `Fonts` | Marks 60–62 (Matrix & Gotham character sets A–Z) | 176 |
| | `Page 2 Footer` | Table guidelines footer cells | 7 |
| **Page 3** | `Page 3 Title` | Title block | 5 |
| | `Brand Pattern Swatches` | Swatches 63–66 & guideline note cell | 26 |
| | `Vertical Pattern` | Patterns 67–74 & 75–82 vertical swatch columns | 47 |
| | `Horizontal Pattern` | Patterns 67–74 & 75–82 horizontal swatch columns | 47 |
| | `Institutional Marks` | Marks 83–91 & usage guidelines | 61 |
| | `Additional Pertinent Information` | Guideline bullet list & notes | 23 |
| | `Page 3 Footer` | Table guidelines footer cells | 7 |

---

## TODO / Task Tracker

### 1. Completed Work

- [x] **Audit Script Development (`tools/audit_svg.py`)**
  - [x] Check 1: Missing `inkscape:label` group detection
  - [x] Check 2: Duplicate group label detection with occurrence counts and XML element path tracing
  - [x] Check 3: Spell check on group labels using `pyspellchecker`
  - [x] Check 4: Empty group (`0` objects) detection
  - [x] Check 5: Single-object group (`1` object) detection
  - [x] Single alphanumeric character ignore filter for empty and single-child checks (e.g. `'A'`, `'1'`, `'a'`)
  - [x] Ignore `<defs>` descendant groups (font glyph definitions and template patterns) in audit discovery
  - [x] Inverse duplicate check: flag entries in `duplicates.txt` not present in the SVG
  - [x] Inverse spelling check: flag entries in `wordlist.txt` not present in any SVG label
  - [x] Check selection CLI flags (`-c`, `--checks`, `--missing`, `--duplicates`, `--spelling`, `--empty`, `--single`)
  - [x] Summary statistics reporting (`-s`, `--stats`, `--statistics`)
  - [x] Strict duplicate check mode (`--strict-duplicates`, `--strict`, `--no-ignore-duplicates`) to audit all duplicates without ignore lists
  - [x] Default sibling file discovery for `wordlist.txt` and `duplicates.txt`

- [x] **SVG Group Structure & Labeling (Page 1)**
  - [x] Page 1 Title (`Page 1 Title Cell`, `Page 1 OLCP Logo`, `Page 1 ECU (East Carolina University)`, `Page 1 Current Revision Date`)
  - [x] Information Section (`Conference`, `Mascot Name`, `Mascot`, `Location`, `Established`)
  - [x] Verbiage Section (4 approved verbiage columns)
  - [x] Colors Section (palette swatches, RGB/CMYK values, PANTONE trademark guideline bullets)
  - [x] Primary Mark Section (Marks 1–7)
  - [x] Primary Word Mark Section (Marks 8–14, color variant headers, and letter decomposition)
  - [x] Secondary Word Mark Section (Marks 15–21 and letter decomposition)
  - [x] Additional Word Marks Section (Marks 22–35, `East` and `Carolina` sub-groups)
  - [x] Page 1 Footer (`Page 1 Note`, `Page 1 Marks`, `Page 1 Use`)

- [x] **SVG Group Structure & Labeling (Page 2)**
  - [x] Page 2 Title (`Page 2 Title Cell`, `Page 2 OLCP Logo`, `Page 2 ECU (East Carolina University)`, `Page 2 Current Revision Date`)
  - [x] Sport Specific Marks (Marks 36–50, sport names and logo sub-groups, guidelines)
  - [x] Pirate State of Mind Marks (Marks 51–53)
  - [x] Script Pirates Section (Marks 54–55, consolidated title header)
  - [x] PeeDee Mark Section (Marks 56–57)
  - [x] Helmet Mark Section (Mark 58)
  - [x] No Quarter Mark Section (Mark 59 & letters A–Z)
  - [x] Fonts Section (Marks 60–62, Matrix & Gotham letter glyphs A–Z)
  - [x] Page 2 Footer (`Page 2 Note`, `Page 2 Marks`, `Page 2 Use`)

- [x] **SVG Group Structure & Labeling (Page 3)**
  - [x] Page 3 Title (`Page 3 Title Cell`, `Page 3 OLCP Logo`, `Page 3 ECU (East Carolina University)`, `Page 3 Current Revision Date`)
  - [x] Brand Pattern Swatches (Swatches 63–66 & guideline note cell)
  - [x] Vertical and Horizontal Patterns (Patterns 67–82, signal flags & icon patterns)
  - [x] Institutional Marks (Marks 83–91, consolidated footnote texts & mark prefixes)
  - [x] Additional Pertinent Information Section (guideline bullets & consolidated text)
  - [x] Page 3 Footer (`Page 3 Note`, `Page 3 Marks`, `Page 3 Use`)

- [x] **Audit & Hygiene Cleanliness**
  - [x] Achieve 100% labeled group coverage across SVG (0 missing labels)
  - [x] Resolve all false-positive typo fragments and trim `tools/wordlist.txt` down to 10 valid proper nouns/acronyms
  - [x] Eliminate all duplicate labels across entire SVG (reducing `tools/duplicates.txt` down to 0 entries)
  - [x] Adopt uniform `Mark N` prefixes across all 91 marks (`Mark 1` through `Mark 91`)
  - [x] Standardize background layer wrapping and numbering (`[N] Background`) across all marks (Marks 15–20, 52, 55, 84, 87)
  - [x] Complete letter and symbol path labeling across all word mark variants (Primary 8–14, Secondary 15–21, Additional 22–35)
  - [x] Prefix font character glyphs in Marks 60–62 with font and mark names (`[N] Matrix [A-Z]`, `[N] Gotham [A-Z]`) and Mark 59 letters
  - [x] Rename and align `ECU Health Note` in Institutional Marks
  - [x] Expand `tools/audit_svg.py` to 8 automated checks (adding label formatting, numbered marks sequence/indicator validation, and canvas-root stranded element checks)
  - [x] Configure `.pre-commit-config.yaml` and GitHub Actions CI workflow (`.github/workflows/ci.yml`) to automatically audit the SVG on commits and pull requests
  - [x] Develop `tools/export_svg_groups.py` with multi-tier export pipeline (native C++, ImageMagick raster conversion, Python tar/zip/svgz archives, and layer-annotated XAML)
  - [x] Implement configurable subprocess timeout (`--timeout`), post-export file verification, and ImageMagick sanity checking
  - [x] Build comprehensive unit test suite in `tools/test_export_svg_groups.py` (33 unit tests passing)
  - [x] Integrate Astral toolchain (`uv`, `ruff`, `ty`) across development, packaging (`pyproject.toml`, `uv.lock`), 14 pre-commit hooks (`ty-check`), and CI matrix workflows
  - [x] Export full document and all 91 marks across PNG, SVG, JPG, and WebP formats into `fmt/`
  - [x] Add `.gitignore` ignoring non-primary intermediate export formats in `fmt/` and environment caches

---

## Future Evaluation: Tooling, Linters, Formatters & Validators by Filetype

The following catalog outlines potential quality assurance tooling, static analyzers, linters, formatters, and integrity validators for all filetypes present in this repository, cataloged for future evaluation:

### Filetype Summary Matrix

| Filetype | Current Tooling in Repo | Candidate Tooling / High-Value Validators | Proposed Integration Layer |
| :--- | :--- | :--- | :--- |
| **`.md`** | `markdownlint-cli` (v0.41.0) | `lychee` (broken link/anchor checker), `prettier` (formatter), `vale` (style linter) | Pre-commit / CI Job |
| **`.gitignore`** | `trailing-whitespace`, `end-of-file-fixer` | `git check-ignore` (pattern tester), `check-gitignore` (alphabetical/duplicate audit) | Pre-commit / Test Suite |
| **`.pdf`** | `check-added-large-files` | `qpdf --check` (structural integrity), `pdfinfo` (poppler), `pdfcpu validate` (ISO 32000) | CI / Unit Test |
| **`.png`** | ImageMagick `identify` (export validator) | `pngcheck` (chunk & CRC integrity check), `oxipng` (lossless optimization) | Unit Test / Pre-commit |
| **`.jpg`** | ImageMagick `identify` (export validator) | `jpeginfo -c` (syntax & corruption audit), `jpegtran` / `mozjpeg` | Unit Test / Pre-commit |
| **`.svg`** | `audit_svg.py` (8 automated checks), `check-xml` | `xmllint --noout` (schema & namespace audit), `svgo` (SVG optimizer) | Pre-commit / CI Job |
| **`.lock`** | Checked into git (`uv.lock`) | `uv lock --check` (verifies lockfile parity with `pyproject.toml`) | CI `astral-quality` Job |
| **`.yaml` / `.yml`** | `check-yaml` (pre-commit-hooks) | `actionlint` (GitHub Actions workflow static checker), `yamllint` | Pre-commit / CI Job |
| **`.toml`** | Parsed by `uv`, `ruff`, and `ty` | `check-toml` (pre-commit-hooks), `taplo` (formatter), `validate-pyproject` | Pre-commit / CI Job |
| **`.webp`** | ImageMagick `identify` (export validator) | `webpinfo` / `dwebp` (bitstream & chunk validation) | Unit Test / Pre-commit |
| **`.txt`** | `requirements-txt-fixer`, `audit_svg.py` inverse ignore checks | `codespell` (fast repo-wide spellcheck) | Pre-commit / CI Job |
| **`.py`** | `ruff`, `ruff-format`, `ty`, `unittest` | `bandit` (security AST linter), `coverage.py` (code coverage metrics) | Pre-commit / CI Job |

---

### Detailed Tooling Catalog by Filetype

#### 1. Markdown (`.md`)

- **`lychee` / `markdown-link-check`**: Validates all relative file paths, internal anchor targets (`#heading-id`), and external HTTP/HTTPS links across documentation files to eliminate dead references.
- **`prettier`**: Opinionated Markdown and table formatter to ensure consistent spacing, table pipe alignment, and list indentation across all READMEs.
- **`vale`**: Prose and style linter for technical documentation and trademark guidelines.

#### 2. Git Ignore (`.gitignore`)

- **`check-gitignore` / `sort-gitignore`**: Enforces alphabetical ordering and detects redundant, shadowed, or duplicate ignore rules.
- **`git check-ignore -v`**: Diagnostic utility for verifying pattern matching against paths.

#### 3. PDF Documents (`.pdf`)

- **`qpdf --check`**: Deep structural and syntax analysis of PDF files, cross-reference tables, and embedded object streams to prevent corrupted references.
- **`pdfinfo` (`poppler-utils`)**: Extracts and verifies metadata, page geometry, PDF version conformance, and encryption states.
- **`pdfcpu validate`**: Command-line PDF processing library providing strict ISO 32000 PDF validation.

#### 4. Raster Images (`.png`, `.jpg`, `.webp`)

- **`pngcheck` (`pngcheck -q -v file.png`)**: Audits PNG chunk ordering, validates CRC checksums, and flags incomplete or corrupted zlib data streams.
- **`jpeginfo` (`jpeginfo -c file.jpg`)**: Verifies JPEG syntax, markers, Huffman tables, and flags corrupted or truncated scans.
- **`webpinfo` / `dwebp` (`dwebp image.webp -o /dev/null`)**: Decodes WebP bitstream headers (VP8, VP8L, VP8X, ALPH, ICCP) and verifies lossy/lossless payload validity.
- **`oxipng` / `mozjpeg`**: Lossless compression optimizers for repository distribution assets.

#### 5. Vector Graphics (`.svg`)

- **`xmllint --noout` (`libxml2`)**: Validates XML grammar, schema conformance, and XML namespace declarations across all SVG files.
- **`svgo`**: SVG optimizer and linter for identifying redundant elements, unused defs, and precision anomalies.

#### 6. Lockfiles & Dependencies (`uv.lock`, `requirements*.txt`)

- **`uv lock --check`**: Asserts in CI that `uv.lock` remains 100% synchronized with `pyproject.toml` without auto-modifying it.
- **`pip-audit` / `uv run pip-audit`**: Scans locked dependencies against the Open Source Vulnerability (OSV) and PyPI advisory databases.

#### 7. YAML (`.yaml`, `.yml`)

- **`actionlint`**: Static checker dedicated to GitHub Actions workflow files (`.github/workflows/*.yml`), verifying expression types, context keys, runner constraints, and security best practices.
- **`yamllint`**: Comprehensive YAML linter checking document formatting, indentation, key duplication, and boolean notation.

#### 8. TOML (`pyproject.toml`)

- **`check-toml`**: Standard hook in `pre-commit/pre-commit-hooks` to validate TOML syntax.
- **`taplo`**: Specialized TOML formatter and schema validator (`taplo check`, `taplo fmt`).
- **`validate-pyproject`**: Validates `pyproject.toml` metadata against PEP 517, PEP 518, and PEP 621 packaging specifications.

#### 9. Plain Text & Dictionaries (`.txt`)

- **`codespell`**: High-performance spelling checker for source code, plain text files, comments, and documentation.

#### 10. Python Code (`.py`)

- **`bandit`**: Security AST static analysis tool for detecting common security flaws (insecure temporary files, command injections, weak cryptography).
- **`coverage.py` (`pytest-cov` / `coverage run`)**: Measures code coverage and ensures unit tests cover all branching logic in `tools/`.

---

### High-Priority Immediate Candidates for Next Iteration

1. **`check-toml`**: Add to `pre-commit-hooks` in `.pre-commit-config.yaml` to validate `pyproject.toml`.
2. **`uv lock --check`**: Add to `.github/workflows/ci.yml` `astral-quality` job to enforce lockfile parity in CI.
3. **`actionlint`**: Add to `.pre-commit-config.yaml` or CI to audit workflow syntax and security.
4. **`pngcheck` / `jpeginfo` / `dwebp`**: Integrate into `tools/test_export_svg_groups.py` for automated raster bitstream integrity testing.
