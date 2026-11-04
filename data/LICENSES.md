# Data licenses and attribution

| Path | Source | License / terms | Attribution |
|---|---|---|---|
| `data/raw/osm/` | OpenStreetMap via Geofabrik (SRC-024) | Open Database License (ODbL) 1.0. Derived databases must stay under ODbL. | © OpenStreetMap contributors, https://www.openstreetmap.org/copyright |
| `data/raw/gtfs/` | data.gov.my GTFS static: BAS.MY Johor Bahru, KTMB (SRC-038, SRC-039) | Malaysian government open data; terms per data.gov.my (owner to confirm the exact license wording before Stage 6) | Source: data.gov.my |
| `vp-data` branch | data.gov.my GTFS-Realtime vehicle positions (SRC-040) | As above | Source: data.gov.my |
| `data/manifests/source-probe.csv` | Our probe of URLs in the source register | Metadata only (status, hash, page title, term matches); no page text is stored | Each source is credited in `docs/sources/source-register.csv` |

Code license: **MIT** (see `LICENSE`, added by the owner 2026-11-04). The MIT license
covers the code and docs written for this project. Third-party data keeps the licenses
listed above. In particular, the OSM extract stays under ODbL.
