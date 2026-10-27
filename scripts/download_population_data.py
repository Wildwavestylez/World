#!/usr/bin/env python3
"""Download consistent WorldPop 2020 population-count rasters for CZ/DE/AT.

Large source GeoTIFFs are saved OUTSIDE the repository by default.
Usage:
  python scripts/download_population_data.py --output-dir ../worldpop-source
Then prepare them:
  python scripts/prepare_population_data.py --input-dir ../worldpop-source --output-dir data/population

Requires Python 3.10+ and requests.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import requests

# Official WorldPop Global2 R2025A v1, constrained population counts, 2020,
# approximately 100 m. Keep all three countries on the same release.
BASE = "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2020"
COUNTRIES = {
    "CZE": ("cze_pop_2020_CN_100m_R2025A_v1.tif", f"{BASE}/CZE/v1/100m/constrained/cze_pop_2020_CN_100m_R2025A_v1.tif"),
    "DEU": ("deu_pop_2020_CN_100m_R2025A_v1.tif", f"{BASE}/DEU/v1/100m/constrained/deu_pop_2020_CN_100m_R2025A_v1.tif"),
    "AUT": ("aut_pop_2020_CN_100m_R2025A_v1.tif", f"{BASE}/AUT/v1/100m/constrained/aut_pop_2020_CN_100m_R2025A_v1.tif"),
}


def download(url: str, destination: Path) -> None:
    tmp = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type or "application/json" in content_type:
            raise RuntimeError(f"Unexpected response type {content_type!r} from {url}")
        with tmp.open("wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out.write(chunk)
    if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Download seems too small: {url}")
    tmp.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("../worldpop-source"),
                        help="directory outside the repository for original large GeoTIFFs")
    parser.add_argument("--countries", nargs="+", choices=COUNTRIES.keys(),
                        default=["CZE", "DEU", "AUT"])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for code in args.countries:
        filename, url = COUNTRIES[code]
        destination = args.output_dir / filename
        if destination.exists() and destination.stat().st_size > 1024 * 1024:
            print(f"Already present, skipping: {destination}")
            continue
        print(f"Downloading {code}: {url}")
        try:
            download(url, destination)
        except Exception as exc:
            print(f"ERROR downloading {code}: {exc}", file=sys.stderr)
            print("Check the current download link on https://hub.worldpop.org/project/categories?id=3", file=sys.stderr)
            return 1
        print(f"Saved {destination} ({destination.stat().st_size / 1024 / 1024:.1f} MiB)")
    print("Done. Run scripts/prepare_population_data.py on the downloaded directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
