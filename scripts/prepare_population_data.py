#!/usr/bin/env python3
"""Prepare WorldPop GeoTIFFs for the World game.

Input: one WorldPop population-count GeoTIFF per country (population counts per
~100 m pixel), downloaded from the official WorldPop Data Hub.
Output: small gzip-compressed Float32 tiles + manifest.json. No raster data is
committed by this script unless the user explicitly chooses the output folder.

Install: python -m pip install rasterio numpy
Run: python scripts/prepare_population_data.py --input-dir /path/to/worldpop-tiffs
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

COUNTRIES = {
    "CZE": {"folder": "cz", "name": "Czechia"},
    "DEU": {"folder": "de", "name": "Germany"},
    "AUT": {"folder": "at", "name": "Austria"},
}
TILE_DEGREES = 0.25


def country_code(path: Path) -> str | None:
    text = path.name.upper()
    for code in COUNTRIES:
        if re.search(rf"(^|[^A-Z]){code}([^A-Z]|$)", text):
            return code
    # WorldPop filenames commonly contain ISO3 country code without separators.
    for code in COUNTRIES:
        if code in text:
            return code
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("data/population"), type=Path)
    parser.add_argument("--tile-degrees", type=float, default=TILE_DEGREES)
    args = parser.parse_args()

    if args.tile_degrees <= 0:
        parser.error("--tile-degrees must be positive")
    rasters = sorted(args.input_dir.glob("*.tif")) + sorted(args.input_dir.glob("*.tiff"))
    if not rasters:
        parser.error(f"No GeoTIFFs found in {args.input_dir}")

    manifest = {
        "schemaVersion": 1,
        "source": "WorldPop Global 2 Population Counts",
        "sourceUrl": "https://hub.worldpop.org/project/categories?id=3",
        "dataYear": 2020,
        "resolution": "approximately 100 m",
        "license": "CC BY 4.0; retain attribution to WorldPop / University of Southampton",
        "tileDegrees": args.tile_degrees,
        "valueFormat": "Float32 little-endian, population count per pixel; -9999 means NoData",
        "countries": {},
    }

    for raster_path in rasters:
        code = country_code(raster_path)
        if code is None:
            print(f"Skip (country code not recognized in filename): {raster_path.name}")
            continue
        country = COUNTRIES[code]
        country_dir = args.output_dir / country["folder"]
        country_dir.mkdir(parents=True, exist_ok=True)
        tiles = []

        with rasterio.open(raster_path) as src:
            if src.crs is None:
                raise RuntimeError(f"Missing CRS: {raster_path}")
            bounds = src.bounds
            # WorldPop population rasters are expected in geographic WGS84.
            if src.crs.to_epsg() != 4326:
                raise RuntimeError(
                    f"{raster_path.name} uses {src.crs}; expected EPSG:4326. "
                    "Reproject explicitly rather than silently shifting cells."
                )
            west = math.floor(bounds.left / args.tile_degrees) * args.tile_degrees
            east = math.ceil(bounds.right / args.tile_degrees) * args.tile_degrees
            south = math.floor(bounds.bottom / args.tile_degrees) * args.tile_degrees
            north = math.ceil(bounds.top / args.tile_degrees) * args.tile_degrees
            tile_y = south
            while tile_y < north:
                tile_x = west
                while tile_x < east:
                    left, bottom = tile_x, tile_y
                    right, top = tile_x + args.tile_degrees, tile_y + args.tile_degrees
                    window = rasterio.windows.from_bounds(
                        left, bottom, right, top, transform=src.transform
                    ).round_offsets().round_lengths()
                    window = window.intersection(Window(0, 0, src.width, src.height))
                    if window.width > 0 and window.height > 0:
                        arr = src.read(1, window=window, masked=True)
                        data = np.asarray(arr.filled(-9999), dtype="<f4")
                        # Keep dimensions/georeferencing for exact cell lookup.
                        name = f"{tile_x:+07.2f}_{tile_y:+06.2f}.f32.gz"
                        out_path = country_dir / name
                        with out_path.open("wb") as raw:
                            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
                                gz.write(data.tobytes(order="C"))
                        transform = rasterio.windows.transform(window, src.transform)
                        tiles.append({
                            "file": f"{country['folder']}/{name}",
                            "west": transform.c,
                            "north": transform.f,
                            "pixelWidth": transform.a,
                            "pixelHeight": transform.e,
                            "width": int(window.width),
                            "height": int(window.height),
                            "sourceRowOffset": int(window.row_off),
                            "sourceColOffset": int(window.col_off),
                        })
                    tile_x += args.tile_degrees
                tile_y += args.tile_degrees

        manifest["countries"][country["folder"]] = {
            "iso3": code,
            "name": country["name"],
            "sourceFile": raster_path.name,
            "tiles": tiles,
        }
        print(f"Prepared {country['name']}: {len(tiles)} tiles")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Manifest written: {manifest_path}")


if __name__ == "__main__":
    main()
