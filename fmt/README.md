# Formatted & Exported Assets (`fmt/`)

This directory contains rendered, transformed, and formatted alternate export formats generated directly from the master vector sources in [`src/`](../src/).

---

## Directory Structure

```text
fmt/
├── README.md                                    # Documentation for formatted assets
├── jpg/                                         # High-resolution JPEG raster exports
│   ├── 2023-05-08-art-sheet-01.jpg              # Full-sheet raster render (229.33 DPI)
│   ├── primary-mark/                            # Marks 1–7
│   ├── primary-word-mark/                       # Marks 8–14
│   ├── secondary-word-mark/                     # Marks 15–21
│   ├── additional-word-marks/                   # Marks 22–35
│   ├── sport-specific-marks/                    # Marks 36–50 (organized by color lockup)
│   ├── pirate-state-of-mind-marks/              # Marks 51–53
│   ├── script-pirates/                          # Marks 54–55
│   ├── peedee-mark/                             # Marks 56–57
│   ├── helmet-mark/                             # Mark 58
│   ├── no-quarter-mark/                         # Mark 59
│   ├── fonts/                                   # Marks 60–62
│   ├── brand-pattern-swatches/                  # Marks 63–66
│   ├── vertical-pattern/                        # Marks 67–74
│   ├── horizontal-pattern/                      # Marks 75–82
│   └── institutional-marks/                     # Marks 83–91
├── png/                                         # High-resolution PNG raster exports
│   ├── 2023-05-08-art-sheet-01.png              # Full-sheet raster render (229.33 DPI)
│   └── ...                                      # Per-mark transparent PNG exports
├── svg/                                         # Standardized plain SVG vector exports
│   ├── 2023-05-08-art-sheet-01.svg              # Full-sheet plain SVG (metadata stripped)
│   └── ...                                      # Individual mark plain SVG vector files
└── webp/                                        # Modern WebP raster exports
    ├── 2023-05-08-art-sheet-01.webp             # Full-sheet WebP render
    └── ...                                      # Per-mark WebP exports
```

---

## Export Formats

### 1. Plain SVG (`fmt/svg/`)

Standardized plain vector SVG files stripped of Inkscape-specific metadata:

- **Full Document**: [`fmt/svg/2023-05-08-art-sheet-01.svg`](svg/2023-05-08-art-sheet-01.svg)
- **Individual Marks**: Plain SVG exports for individual marks preserving vector scalability.

### 2. High-Resolution PNG (`fmt/png/`)

Lossless raster images rendered from the master vector SVG with transparency:

- **Full Document**: [`fmt/png/2023-05-08-art-sheet-01.png`](png/2023-05-08-art-sheet-01.png)
- **Individual Marks**: Transparent PNG renders exported at print quality (229.33 DPI).

### 3. High-Quality JPEG (`fmt/jpg/`)

High-quality JPEG raster images rendered against clean white backgrounds:

- **Full Document**: [`fmt/jpg/2023-05-08-art-sheet-01.jpg`](jpg/2023-05-08-art-sheet-01.jpg)
- **Individual Marks**: Marks 1 through 91 categorized in hierarchical subdirectories.

### 4. Optimized WebP (`fmt/webp/`)

Modern, highly compressed WebP raster files ideal for web embedding:

- **Full Document**: [`fmt/webp/2023-05-08-art-sheet-01.webp`](webp/2023-05-08-art-sheet-01.webp)
- **Individual Marks**: Complete set of Marks 1 through 91 in WebP format.

---

## Regeneration

To regenerate formatted assets from the master SVG using the [`export_svg_groups.py`](../tools/export_svg_groups.py) utility:

```bash
# Export the complete document canvas:
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format svg
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format png
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format jpg
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --full --format webp

# Export all marks matching a pattern (e.g. Marks 1 through 91):
python3 tools/export_svg_groups.py src/art-sheet-5-8-23/2023-05-08-art-sheet-01.svg --pattern "^Mark [0-9]+$" --format svg
```
