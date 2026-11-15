# Data licenses and attribution

| Path | Source | License / terms | Attribution |
|---|---|---|---|
| `data/raw/osm/` | OpenStreetMap via Geofabrik (SRC-024) | Open Database License (ODbL) 1.0. Derived databases must stay under ODbL. | © OpenStreetMap contributors, https://www.openstreetmap.org/copyright |
| `data/raw/gtfs/` | data.gov.my GTFS static: BAS.MY Johor Bahru, KTMB (SRC-038, SRC-039) | Malaysian government open data; terms per data.gov.my (owner to confirm the exact license wording before Stage 6) | Source: data.gov.my |
| `vp-data` branch | data.gov.my GTFS-Realtime vehicle positions (SRC-040) | As above | Source: data.gov.my |
| `data/raw/osm/jb-study.osm.pbf` | OpenStreetMap via Geofabrik (SRC-024), Stage 2 study-area clip, tag-filtered | ODbL 1.0 | © OpenStreetMap contributors |
| `data/concept/*.geojson`, `results/stage2/` | Derived from OSM (ODbL) plus our concept routing | Derived database: ODbL 1.0 (share-alike) | © OpenStreetMap contributors; concept geometry by this project |
| DEM (not committed; fetched per run) | Copernicus DEM GLO-30 (SRC-041) | Copernicus DEM licence, attribution required | © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA |
| Flood raster (not committed; fetched per run) | JRC CEMS-GloFAS flood hazard RP100 (SRC-042) | CC BY 4.0 | © European Union, Joint Research Centre |
| `data/manifests/plans-list-extract.csv` | JPBD Johor plan list (SRC-026) | Government document; matched lines only (max 240 characters each) for status | Source: PLANMalaysia@Johor |
| `data/manifests/source-probe.csv` | Our probe of URLs in the source register | Metadata only (status, hash, page title, term matches); no page text is stored | Each source is credited in `docs/sources/source-register.csv` |

## Photos (Wikimedia Commons)

`site/photos/jb/*.jpg` are downloaded from Wikimedia Commons by `pipeline/explorer/photos.py`.
Each file keeps its own license (CC0, CC BY, CC BY-SA or public domain only; the script refuses
anything else). Per-file title, page URL, author, license and license URL are in
`site/data/jb/photos.json`, and the explorer shows "Photo: author · license · Wikimedia Commons"
linked to the file page wherever a photo appears. Photos may be resized and re-encoded (a
modification under CC BY / CC BY-SA); the original is on the linked file page.

Code license: **MIT** (see `LICENSE`, added by the owner 2026-11-04). The MIT license
covers the code and docs written for this project. Third-party data keeps the licenses
listed above. In particular, the OSM extract stays under ODbL.
