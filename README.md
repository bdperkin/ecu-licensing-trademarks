# East Carolina University Trademark Licensing Art Sheet & Tooling

Comprehensive repository containing normalized vector SVG assets, reference publications, automated quality assurance tooling, and continuous integration workflows for the East Carolina University (ECU) Trademark Licensing Art Sheet.

---

## Legal & Non-Affiliation Disclaimer

> [!IMPORTANT]
> **Disclaimer of Ownership and Non-Affiliation**:
> The maintainer and contributors of this repository have **NO ownership, affiliation, association, authorization, sponsorship, or endorsement** by East Carolina University (ECU), the East Carolina University Office of Licensing and Trademarks, the Collegiate Licensing Company (CLC), Learfield, or any athletic conference or subsidiary.
>
> All university logos, word marks, mascot illustrations, seal depictions, brand patterns, slogans, and intellectual property referenced or contained in these visual assets are the exclusive trademarked property of **East Carolina University** and their respective trademark holders.
>
> The maintainer claims ownership **solely over the open-source code, automated audit tooling, unit tests, and structural SVG normalization scripts** authored in this repository. All visual assets and documentation are provided strictly for technical, educational, and archival purposes. Any commercial use or reproduction of East Carolina University trademarks requires prior written authorization from East Carolina University or the Collegiate Licensing Company (CLC).

---

## Repository Architecture

```text
.
├── src/                                     # Curated, strictly validated master vector assets
│   ├── README.md                            # Documentation for vector source assets
│   └── art-sheet-5-8-23/
│       └── 2023-05-08-art-sheet-01.svg      # Master 3-page vector art sheet (Inkscape SVG)
├── fmt/                                     # Formatted and rendered export assets
│   ├── README.md                            # Documentation for formatted assets
│   ├── jpg/                                 # JPEG raster exports (full sheet & marks 1–91)
│   ├── png/                                 # PNG raster exports (full sheet & marks 1–91)
│   ├── svg/                                 # Plain SVG vector exports (full sheet & marks 1–91)
│   └── webp/                                # WebP raster exports (full sheet & marks 1–91)
├── tools/                                   # Automated quality assurance & export suite
│   ├── README.md                            # Documentation for audit & export tools
│   ├── audit_svg.py                         # 8-check automated SVG structure & label audit tool
│   ├── test_audit_svg.py                    # Unit test suite for audit routines
│   ├── export_svg_groups.py                 # Multi-tier group & full document export utility
│   ├── test_export_svg_groups.py            # Unit test suite for export routines (33 tests)
│   ├── wordlist.txt                         # Approved proper nouns & acronyms for spellcheck
│   └── duplicates.txt                       # Duplicate label ignore list (0 entries; 100% unique)
├── site-upload-content/                     # Original raw reference documents & extracts
│   ├── README.md                            # Documentation for reference materials
│   ├── 2023_ECU_Athletics_Brand_Guide.pdf   # Complete 43-page ECU Athletics Brand Guide (PDF)
│   ├── Art-Sheet-5.8.23.pdf                 # Original 3-page consolidated Art Sheet (PDF)
│   ├── extracted_links.txt                  # Reference URL catalog from official ECU portals
│   ├── 2023-ecu-athletics-brand-guide-pdf/  # Split per-page PDF pages (1–43)
│   ├── 2023-ecu-athletics-brand-guide-svg/  # Vectorized per-page SVG extracts (1–43)
│   ├── art-sheet-5-8-23-pdf/                # Split art sheet PDF
│   └── art-sheet-5-8-23-svg/                # Raw art sheet SVG extract
├── .github/
│   ├── dependabot.yml                       # Automated weekly dependency & workflow updates
│   └── workflows/
│       ├── ci.yml                           # CI workflow (Astral uv, ruff, ty, unit tests, audit)
│       └── codeql.yml                       # CodeQL automated code scanning workflow
├── .pre-commit-config.yaml                  # 14 pre-commit hooks for all repository file types
├── pyproject.toml                           # Astral toolchain configuration (uv, ruff, ty)
├── uv.lock                                  # Locked reproducible dependencies
├── requirements.txt                         # Runtime Python dependencies (lxml, pyspellchecker)
├── requirements-dev.txt                     # Developer & CI dependencies (pre-commit, ruff, ty)
├── SECURITY.md                              # Security policy & private vulnerability reporting
├── TODO.md                                  # Review checklist, section architecture, & status tracker
└── README.md                                # Top-level documentation & trademark guidelines
```

---

## Trademark Notes & Guidelines (from Art Sheet SVG)

The following notes, restrictions, and usage guidelines are extracted and expanded directly from the official labels in [`src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg`](src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg):

### 1. Licensing Administration & Approval Notice

- **Program Administration**: The marks of East Carolina University are controlled under a licensing program administered by the [Collegiate Licensing Company (CLC)](https://clc.com/). Any commercial use of these marks requires prior written approval from CLC or East Carolina University.
- **Trademark Designators**: The symbols `®` (Registered Trademark) and `™` (Trademark) represent the official legal status of the respective marks and must be retained as indicated on the art sheet.
- **Contact & Inquiries**: For information regarding trademark licensing, product purchasing approvals, or policy procedures, visit the [ECU Licensing Portal](https://licensing.ecu.edu/).

### 2. Color Palette & Reproduction Standards

- **Primary University Colors**:
  - **ECU Purple**: PANTONE 268 C | CMYK `82, 98, 0, 12` | RGB `89, 45, 130` | HEX `#592D82`
  - **ECU Gold**: PANTONE 109 C / 123 C | CMYK `0, 24, 94, 0` | RGB `255, 194, 17` | HEX `#FFC211`
- **Secondary / Neutral Colors**:
  - **Gray**: PANTONE Cool Gray 7 C | CMYK `20, 14, 12, 40` | RGB `151, 153, 155` | HEX `#97999B`
  - **Black**: Process Black | CMYK `0, 0, 0, 100` | RGB `35, 31, 32` | HEX `#231F20`
  - **White**: Process White | CMYK `0, 0, 0, 0` | RGB `255, 255, 255` | HEX `#FFFFFF`
- **Color Matching Warning**: Approved University colors or the designated PANTONE colors listed on the art sheet must be used. Digital and screen representations are not intended to replace PANTONE Color Standards; refer to current PANTONE publications for physical color matching.
- **Prohibitions**: No color substitutions, unapproved gradients, or color inversions are permitted.

### 3. Primary & Secondary Marks (Marks 1–21)

- **Primary Mark (Marks 1–7)**: The Skull & Crossbones is the primary athletic identity mark. It must always appear with authorized contrast backgrounds and cannot be paired with other athletic marks without explicit licensing approval.
- **Primary Word Mark (Marks 8–14)**: The `ECU` slab-serif word mark is approved across 7 standard color configurations (Purple/Gold outline, Gold/Purple outline, Solid Purple, Solid Gold, Solid White, Solid Black, Purple/Black outline).
- **Secondary Word Mark (Marks 15–21)**: The `Pirates` slab-serif word mark is approved across 7 standard color configurations.
- **Additional Word Marks (Marks 22–35)**: The `East Carolina` arched and stacked word mark configurations.

### 4. Sport Specific Marks (Marks 36–50)

- **Approved Sport Identifiers**: Baseball, Basketball, Cross Country, Football, Golf, Soccer, Softball, Swimming & Diving, Tennis, Track & Field, Volleyball.
- **Typography & Lockup Rules**: Sport identifiers must use official Gotham or Matrix typography lockups with standardized spacing, proportions, and background contrast.

### 5. Special Mark Restrictions

- **No Quarter Mark (Mark 59)**: *Mark must be used on a red flag or a depiction of a red flag.*
- **ECU Health Logo (Mark 90)**: *Only entities connected to the hospital system and the medical school are permitted to use this logo.*
- **University Seal (Mark 91)**: *The University Seal is restricted to official University documents, presidential use, and select academic merchandise approved by licensing.*
- **Pirate State of Mind (Marks 51–53)** & **Script Pirates (Marks 54–55)**: Slogan and script marks subject to designated retail and apparel application guidelines.

### 6. Brand Patterns & Swatches (Marks 63–82)

- **Brand Swatches (Swatches 63–66)**: Official flag and texture swatches.
- **Signal Flag & Icon Patterns (Patterns 67–82)**: Vertical and horizontal nautical signal flags and athletic icon patterns. Patterns must be used in accordance with approved orientation guidelines (do not use vertical patterns for horizontal stripe treatments).

### 7. Approved Verbiage & Information

- **Approved Verbiage**: *East Carolina University®*, *East Carolina™*, *ECU®*, *Pirates®*, *Pirate Nation®*, *Purple & Gold™*, *Paint It Purple™*, *No Quarter™*, *We The East™*, *Arrrgh™*.
- **Institutional Facts**:
  - Location: **Greenville, NC**
  - Established: **1907**
  - Mascot: **PeeDee the Pirate**
  - Conference Affiliation: **American Athletic Conference (AAC)**
- **Cross-Licensing Policy**: Cross-licensing with other collegiate or commercial marks may be permitted only with an additional written co-branding agreement.

---

## Quality Assurance & Automated Validation

The repository includes a validation and export testing suite ensuring all vector and raster assets meet structural standards:

```bash
# Run all 8 automated checks in strict mode
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --strict -s

# Run unit test suite (33 tests covering audit & export pipelines)
python3 -m unittest discover -s tools

# Run static type checking via Astral ty
ty check

# Run linting and format checks via Astral ruff
uv run ruff check .
uv run ruff format --check .

# Run all pre-commit hooks locally
pre-commit run --all-files
```

### Automated Checks Summary

1. **Missing Labels (`missing`)**: 100% labeled coverage across all 1,045 groups (`0` missing).
2. **Duplicate Labels (`duplicates`)**: 100% globally unique label names (`0` duplicates).
3. **Spelling & Typos (`spelling`)**: Validated via `pyspellchecker` against [`tools/wordlist.txt`](tools/wordlist.txt) (`0` typos).
4. **Empty Groups (`empty`)**: Zero empty containers (`0` empty).
5. **Single-Object Groups (`single`)**: Zero redundant single-child wrapper groups (`0` single-object groups).
6. **Label Formatting (`formatting`)**: Zero leading/trailing whitespace or multiple spaces.
7. **Numbered Marks (`marks`)**: Sequential validation for all 91 marks and number indicator children.
8. **Ungrouped Elements (`ungrouped`)**: Zero stranded visual elements at canvas root.

---

## Contributing & Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/bdperkin/ecu-licensing-trademarks.git
   cd ecu-licensing-trademarks
   ```

2. **Synchronize environment and dependencies with Astral `uv`**:

   ```bash
   uv sync --all-extras --dev
   ```

3. **Install pre-commit hooks**:

   ```bash
   uv run pre-commit install
   ```

---

## External Links & References

- [East Carolina University Official Website](https://www.ecu.edu/)
- [ECU Trademark Licensing Portal](https://licensing.ecu.edu/)
- [ECU Athletics Official Portal](https://ecupirates.com/)
- [Collegiate Licensing Company (CLC)](https://clc.com/)
