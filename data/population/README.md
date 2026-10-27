# Population data for World

This folder is for compact, locally served population tiles used by the World map game.

## Source and attribution

- WorldPop Global 2 Population Counts, approximately 100 m population-count raster.
- Data hub: https://hub.worldpop.org/project/categories?id=3
- WorldPop describes country-specific 100 m and 1 km population-count datasets for 2015–2030.
- License: CC BY 4.0 for the referenced open datasets; verify the selected dataset's release statement and retain its exact attribution before publishing derived data.
- The preparation script defaults the manifest's reference year to 2020; use a matching source raster and update the year/metadata if another release is selected.

## Prepare the tiles

1. Download the population-count GeoTIFF for each of Czechia (CZE), Germany (DEU), and Austria (AUT) from the WorldPop Data Hub. Prefer a consistent release/year and population-count product for all three countries.
2. Keep the original GeoTIFFs outside the Git repository (they can be large).
3. Install Python dependencies:

   ```bash
   python -m pip install rasterio numpy
   ```

4. Run from the repository root:

   ```bash
   python scripts/prepare_population_data.py --input-dir /path/to/worldpop-tiffs --output-dir data/population
   ```

The script creates 0.25-degree compressed Float32 tiles and a `manifest.json`. Each raster cell retains its population count; `-9999` marks NoData. These are intermediate data assets, not yet wired into the browser game. The browser integration must decompress tiles, test newly covered cells against the polygon, and keep a persistent set of counted cell IDs so cells are counted once only.

## Repository size

Do not commit original GeoTIFFs. After running the converter, inspect total output size before committing generated tiles. If the output is still too large for normal Git history, publish the generated `data/population` folder as a versioned GitHub Release asset or use Git LFS instead of adding it to every Git checkout.

## Notes

WorldPop values are modelled estimates, not a definitive census of every named village. The data are spatial population counts and work well for estimating population in a changing polygon.
