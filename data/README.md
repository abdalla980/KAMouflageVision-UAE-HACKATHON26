# KAMouflage Vision – Data

Everything the prototype needs, fetched by one command:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python data/scripts/fetch_all.py  # ~600 images, ~300 MB, a few minutes
```

## Folder layout

```
data/
├── scripts/
│   ├── fetch_all.py                 run everything below in order
│   ├── fetch_bayanat.py             MOCCAE datasets from bayanat.ae
│   ├── fetch_species_reference.py   UAE species list + occurrences from GBIF
│   ├── fetch_camera_traps.py        curated camera-trap subset from LILA BC
│   └── build_demo_dataset.py        merge into clean tables for the app
├── raw/          all downloads (in the repo; re-create with fetch_all.py)
│   ├── bayanat/        9 MOCCAE / FCSC datasets (.xlsx + .csv) + manifest.json
│   ├── gbif/           uae_species.csv, uae_occurrences.csv
│   └── camera_traps/   kga/, kar/  -> images/ + selection.csv
└── processed/    what the app reads
    ├── images.csv             one row per image: camera, reserve, GPS, UAE timestamp, ground truth
    ├── cameras.csv            simulated camera deployments inside real UAE reserves
    ├── species_reference.csv  UAE mammals & reptiles (GBIF, with IUCN status) + birds (MOCCAE)
    ├── protected_areas.csv    MOCCAE protected areas with coordinates
    └── data_sources.json      provenance & licenses
```

## Sources (the challenge asks for these four data types)

| Challenge data type | Source | Real or simulated |
|---|---|---|
| Camera-trap imagery | LILA BC – Snapshot Kgalagadi & Snapshot Karoo (arid southern Africa), CDLA-Permissive-1.0 | Real camera-trap photos, **not from the UAE** |
| Species reference records | GBIF UAE occurrences (mammals, reptiles; IUCN status) + MOCCAE "List of local Aves (Birds) in the UAE – 2023" (Bayanat) | Real UAE data |
| Location metadata | MOCCAE "Protected Lands Coordinates in UAE" (Bayanat) | Real reserves; **camera positions inside them are simulated** |
| Observation timestamps | From the camera-trap EXIF/metadata | Real time of day & season; years shifted to 2024–2025 |

Bayanat datasets downloaded (all published by MOCCAE or the Federal Competitiveness and Statistics Centre):
Protected Lands Coordinates in UAE · Protected Lands in UAE · Protected Lands by Area, Emirate and Zone ·
Designated Protected Areas by Types and Emirates · Natural Reserves in UAE by Emirate, Type and Establishment Year ·
Long-Range Nature Reserves in the UAE · Areas of Nature Reserves According to the Type and Emirate ·
List of local Aves (Birds) in the UAE – 2023 · Local Birds List.
Bayanat has **no wildlife sightings or camera-trap data**; that is MOCCAE's internal archive, which replaces
the LILA images in the 90-day pilot.

### UAE counterparts

The demo images show southern-African species. `images.csv` maps each to a UAE counterpart and says how close
the match is: `same species` (caracal, African/Arabian wildcat, honey badger, cape hare), `same genus`
(gemsbok → Arabian oryx, cape fox → Arabian red fox), `same family`, or `analogue` (similar-looking animal in a
similar niche, e.g. steenbok → gazelle). Present these as stand-ins in the pitch.

### Notes

- Human images were removed by LILA for privacy; sequences labelled "human" are skipped.
- GBIF includes pets, livestock and zoo animals; `species_reference.csv` flags them in `domestic_or_captive`.
- Bayanat has no public catalogue API; `fetch_bayanat.py` uses the same endpoints as the website and may need
  updating if the site changes.
