# Formatted & Exported Assets (`fmt/`)

This directory contains rendered, transformed, and formatted alternate export formats generated directly from the master vector sources in [`src/`](../src/).

---

## Directory Structure

```text
fmt/
├── README.md                            # Documentation for formatted assets
└── png/                                 # Raster PNG image exports
    └── art-sheet-5-8-23/
        └── 2023-05-08-art-sheet-01.png  # High-resolution raster render (229.33 DPI)
```

---

## Export Formats

### PNG (`fmt/png/`)

High-resolution raster images rendered from the master vector SVG files at print-quality resolution:

- **[`art-sheet-5-8-23/2023-05-08-art-sheet-01.png`](png/art-sheet-5-8-23/2023-05-08-art-sheet-01.png)**:
  - **Source**: [`src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg`](../src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg)
  - **Resolution**: 229.33 DPI (high-fidelity multi-page canvas render)
  - **Purpose**: Visual review, documentation previews, and reference rasterization.

---

## Regeneration

To regenerate the PNG render from the master SVG using the Inkscape CLI:

```bash
inkscape src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg \
  --export-filename=fmt/png/art-sheet-5-8-23/2023-05-08-art-sheet-01.png \
  --export-dpi=229.33
```
