# What's above Boston

A live 3D view of the planes over Boston, with the approaches in use at Logan: [whatsabove.boston](https://whatsabove.boston).

Fork of [whatsabove.nyc](https://github.com/credibilllhen/whatsabovenyc). The page is static and lives in `site/`, published to GitHub Pages by `.github/workflows/site.yml`.

Live data comes from the shared poller in the whatsabovenyc repo (`worker/`). It runs a separate Boston instance, fed by the home relay with `RELAY_CITIES=nyc,boston`. Boston's files are in the same R2 bucket under `boston/`, served at `https://data.whatsabove.nyc/boston/`.

## Data

- `site/approaches.json`: Logan's published approaches, built from FAA CIFP by `tools/build_approaches.py`:
  `python3 tools/build_approaches.py FAACIFP18 > site/approaches.json`.
  Also copy the file to `worker/cities/boston-approaches.json` in the whatsabovenyc repo so the poller agrees.
  The current file is from a 2024 cycle.
- Coastline (`LAND_ENC` in the page): Massachusetts 2020 Census municipalities, clipped to the shoreline, plus OpenStreetMap land (geo-maps, ODbL) for NH and RI, built by `tools/build_land.py`.
