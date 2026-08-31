# Formatted & Exported Assets (`fmt/`)

This directory contains rendered, transformed, and formatted alternate export formats generated directly from the master vector sources in [`src/`](../src/).

---

## Directory Structure

```text
fmt/
├── README.md                    # Documentation for formatted assets
├── png/                         # Raster PNG image exports
│   └── 2023-05-08-art-sheet-01.png  # High-resolution raster render (229.33 DPI)
└── svg/                         # Standardized plain SVG vector exports
    └── 2023-05-08-art-sheet-01.svg  # Plain SVG export (Inkscape metadata stripped)
```

---

## Export Formats

### PNG (`fmt/png/`)

High-resolution raster images rendered from the master vector SVG files at print-quality resolution:

- **[`2023-05-08-art-sheet-01.png`](png/2023-05-08-art-sheet-01.png)**:
  - **Source**: [`src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg`](../src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg)
  - **Resolution**: 229.33 DPI (high-fidelity multi-page canvas render)
  - **Purpose**: Visual review, documentation previews, and reference rasterization.

### SVG (`fmt/svg/`)

Standardized plain vector SVG files stripped of Inkscape-specific metadata:

- **[`2023-05-08-art-sheet-01.svg`](svg/2023-05-08-art-sheet-01.svg)**:
  - **Source**: [`src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg`](../src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg)
  - **Format**: Plain SVG (`--export-plain-svg`)
  - **Purpose**: General vector consumption and third-party tool compatibility.

---

## Regeneration

To regenerate formatted assets from the master SVG using the [`export_svg_groups.py`](../tools/export_svg_groups.py) utility:

```bash
# Export the complete document canvas as high-resolution PNG:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format png

# Export the complete document canvas as plain SVG:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format svg
```
