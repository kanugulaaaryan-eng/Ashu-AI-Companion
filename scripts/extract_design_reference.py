#!/usr/bin/env python3
"""
Ashu Design Reference Sheet - Grid Extractor & Asset Verification

This script:
1. Extracts the 4x6 grid cells from the design reference sheet
2. Saves them as individual PNG files for visual comparison
3. Verifies delivered assets against their grid references
"""

from PIL import Image
import numpy as np
import os
import json
from pathlib import Path

REFERENCE_SHEET = Path("docs/design/ashu_design_reference_sheet.png")
MANIFEST = Path("docs/design/ASHU_ASSET_MANIFEST.json")
OUTPUT_DIR = Path("docs/design/reference_grid")
ASSETS_DIR = Path("web/assets/ashu/portraits")  # Android uses drawable-nodpi


def extract_grid():
    """Extract 4x6 grid cells from reference sheet."""
    if not REFERENCE_SHEET.exists():
        print(f"Reference sheet not found: {REFERENCE_SHEET}")
        return

    img = Image.open(REFERENCE_SHEET)
    arr = np.array(img)
    h, w = arr.shape[:2]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Extracting 4x6 grid from {REFERENCE_SHEET} ({w}x{h})")
    print(f"Cell size: {w//6}x{h//4}")

    for row in range(4):
        for col in range(6):
            y1 = row * h // 4
            y2 = (row + 1) * h // 4
            x1 = col * w // 6
            x2 = (col + 1) * w // 6
            region = arr[y1:y2, x1:x2]
            cell_img = Image.fromarray(region)
            cell_img.save(OUTPUT_DIR / f"grid_r{row}_c{col}.png")
            print(f"  Saved grid_r{row}_c{col}.png ({x2-x1}x{y2-y1})")

    print(f"\nGrid cells saved to {OUTPUT_DIR}/")


def verify_assets():
    """Verify delivered assets match their grid references."""
    if not MANIFEST.exists():
        print(f"Manifest not found: {MANIFEST}")
        return

    with open(MANIFEST) as f:
        manifest = json.load(f)

    print("\n=== Asset Verification ===")
    for asset in manifest['assets']:
        name = asset['name']
        status = asset['status']
        grid_ref = asset.get('design_reference', {})

        if status == 'delivered':
            # Find the actual asset file
            asset_path = None
            for ext in ['.webp', '.png']:
                for search_dir in [ASSETS_DIR, Path("android/app/src/main/res/drawable-nodpi")]:
                    candidate = search_dir / f"{name}{ext}"
                    if candidate.exists():
                        asset_path = candidate
                        break
                if asset_path:
                    break

            if asset_path:
                img = Image.open(asset_path)
                grid_info = f"Grid[{grid_ref.get('grid_row','?')},{grid_ref.get('grid_col','?')}]"
                print(f"  [OK] {name}: {asset_path} ({img.size}, {img.mode}) - {grid_info}")
            else:
                # Try with v2_ prefix
                for ext in ['.webp', '.png']:
                    for search_dir in [ASSETS_DIR, Path("android/app/src/main/res/drawable-nodpi")]:
                        candidate = search_dir / f"ashu_v2_{name.replace('ashu_', '')}{ext}"
                        if candidate.exists():
                            img = Image.open(candidate)
                            grid_info = f"Grid[{grid_ref.get('grid_row','?')},{grid_ref.get('grid_col','?')}]"
                            print(f"  [OK] {name}: {candidate} ({img.size}, {img.mode}) - {grid_info}")
                            asset_path = candidate
                            break
                    if asset_path:
                        break
                if not asset_path:
                    print(f"  [MISSING] {name}: DELIVERED but file not found!")
        elif status == 'pending_credits':
            grid_info = f"Grid[{grid_ref.get('grid_row','?')},{grid_ref.get('grid_col','?')}]"
            print(f"  [PENDING] {name}: PENDING - {grid_info}")


def create_comparison_grid():
    """Create a visual comparison: reference grid cells vs delivered assets."""
    if not MANIFEST.exists():
        return

    with open(MANIFEST) as f:
        manifest = json.load(f)

    delivered = [a for a in manifest['assets'] if a['status'] == 'delivered']

    # Create a comparison image
    cell_w, cell_h = 256, 256
    cols = 6
    rows = 4
    comp_w = cols * cell_w
    comp_h = rows * cell_h * 2  # Top: reference, Bottom: delivered (or placeholder)

    comparison = Image.new('RGB', (comp_w, comp_h), (240, 240, 240))

    # Load reference sheet
    ref_img = Image.open(REFERENCE_SHEET)
    ref_arr = np.array(ref_img)

    for asset in delivered:
        name = asset['name']
        grid_ref = asset.get('design_reference', {})
        row = grid_ref.get('grid_row', 0)
        col = grid_ref.get('grid_col', 0)

        # Paste reference grid cell (top half)
        y1 = row * ref_arr.shape[0] // 4
        y2 = (row + 1) * ref_arr.shape[0] // 4
        x1 = col * ref_arr.shape[1] // 6
        x2 = (col + 1) * ref_arr.shape[1] // 6
        ref_cell = ref_arr[y1:y2, x1:x2]
        ref_cell_img = Image.fromarray(ref_cell).resize((cell_w, cell_h))
        comparison.paste(ref_cell_img, (col * cell_w, row * cell_h))

        # Paste delivered asset (bottom half) - if found
        asset_path = None
        for ext in ['.webp', '.png']:
            for search_dir in [ASSETS_DIR, Path("android/app/src/main/res/drawable-nodpi")]:
                candidate = search_dir / f"ashu_v2_{name.replace('ashu_', '')}{ext}"
                if candidate.exists():
                    asset_path = candidate
                    break
            if asset_path:
                break

        if asset_path:
            delivered_img = Image.open(asset_path)
            # Resize to fit cell, preserving aspect
            delivered_img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
            # Center in cell
            paste_x = col * cell_w + (cell_w - delivered_img.width) // 2
            paste_y = (rows * cell_h) + row * cell_h + (cell_h - delivered_img.height) // 2
            if delivered_img.mode == 'RGBA':
                comparison.paste(delivered_img, (paste_x, paste_y), delivered_img)
            else:
                comparison.paste(delivered_img, (paste_x, paste_y))

    output_path = OUTPUT_DIR / "comparison_reference_vs_delivered.png"
    comparison.save(output_path)
    print(f"\nComparison image saved to {output_path}")


if __name__ == "__main__":
    print("Ashu Design Reference Sheet Tool")
    print("=" * 40)

    extract_grid()
    verify_assets()
    create_comparison_grid()

    print("\nDone!")