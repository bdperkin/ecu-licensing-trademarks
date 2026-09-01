# Source Vector Assets (`src/`)

This directory contains the curated, normalized, and strictly validated master source vector assets (Inkscape SVG) for the East Carolina University Trademark Licensing Art Sheet.

---

## Directory Structure

```text
src/
├── README.md                        # Documentation for source vector assets
└── art-sheet-5-8-23/
    └── 2023-05-08-art-sheet-01.svg  # Master 3-page vector art sheet (Inkscape SVG)
```

---

## Production Vector Asset Details

### Master Vector Art Sheet ([`2023-05-08-art-sheet-01.svg`](art-sheet-5-8-23/2023-05-08-art-sheet-01.svg))

The master vector asset is a 3-page consolidated canvas containing all 91 official university marks, approved verbiage, color swatches, typography, and licensing footnotes:

- **Total Canvas Groups**: `1,045` `<g>` elements across 25 top-level canvas sections.
- **Labeling Coverage**: **100%** (all 1,045 groups contain descriptive `inkscape:label` attributes).
- **Label Uniqueness**: **100% Globally Unique** (`1,045` distinct label names; `0` duplicate names).
- **Structural Integrity**: Zero empty groups, zero single-object wrapper groups, and zero stranded canvas-root elements.

> [!NOTE]
> Formatted raster renders (PNG, JPG, WebP) and plain SVG vector files generated from this master SVG are stored in [`fmt/`](../fmt/). See [`fmt/README.md`](../fmt/README.md) for details.

---

## Art Sheet Page Organization

| Page | Section Label | Content & Marks |
| :--- | :--- | :--- |
| **Page 1** | `Page 1 Title` | OLCP logo, ECU header, revision date block |
| | `Information Section` | Location (*Greenville, NC*), Mascot (*PeeDee the Pirate*), Established (*1907*), Conference (*AAC*) |
| | `Verbiage Section` | Approved university terminology and slogans (4-column layout) |
| | `Colors Section` | Primary & secondary PANTONE / CMYK / RGB color swatches and reproduction guidelines |
| | `Primary Mark` | **Marks 1–7**: Skull & Crossbones primary marks |
| | `Primary Word Mark` | **Marks 8–14**: ECU primary word marks across 7 color configurations |
| | `Secondary Word Mark` | **Marks 15–21**: Pirates secondary word marks across 7 color configurations |
| | `Additional Word Marks` | **Marks 22–35**: East Carolina word mark configurations |
| | `Page 1 Footer` | Trademark symbols, licensing administration, and approval requirements |
| **Page 2** | `Page 2 Title` | Header block |
| | `Sport Specific Marks` | **Marks 36–50**: Baseball, Basketball, Football, Golf, Soccer, Swimming, Tennis, Track & Field, Volleyball |
| | `Pirate State of Mind Marks` | **Marks 51–53**: State silhouette and slogan lockups |
| | `Script Pirates Marks` | **Marks 54–55**: Script typography marks |
| | `PeeDee the Pirate Marks` | **Marks 56–57**: Mascot illustrations |
| | `Helmet Mark` | **Mark 58**: Football helmet illustration |
| | `No Quarter Mark` | **Mark 59**: No Quarter pirate logo and flag lockup |
| | `Fonts Section` | **Marks 60–62**: Matrix and Gotham typography alphabets (A–Z) across 3 color variations |
| | `Page 2 Footer` | Licensing notice and trademark guidelines |
| **Page 3** | `Page 3 Title` | Header block |
| | `Brand Pattern Swatches` | **Swatches 63–66**: Flag and brand pattern swatches |
| | `Vertical and Horizontal Patterns` | **Patterns 67–82**: Nautical signal flags, icon patterns, and stripe treatments |
| | `Institutional Marks` | **Marks 83–91**: ECU institutional variations, ECU Health lockups, University Seal |
| | `Additional Pertinent Information` | Expanded university guidelines, cross-licensing policy, and athletic rules |
| | `Page 3 Footer` | Licensing notice and contact details |

---

## Validation

To audit the structural hygiene and XML validity of the SVG file, run:

```bash
python3 tools/audit_svg.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --strict -s
```

See the [`tools/` documentation](../tools/README.md) for full details on automated checks.
