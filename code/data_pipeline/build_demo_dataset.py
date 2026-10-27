"""Combine all raw sources into the clean tables the KAMouflage Vision app reads.

- Simulated camera deployments: each source camera location is placed inside a real UAE terrestrial
  protected area, using MOCCAE's "Protected Lands Coordinates in UAE" (Bayanat). Placement is
  deterministic and clearly marked as simulated.
- Timestamps keep their real time of day and day of year (so activity patterns stay genuine) and are
  shifted by whole years into the recent past.
- Species reference: GBIF UAE species, flagged for domestic/captive animals, plus MOCCAE's local bird list.

Output (data/processed/):
  cameras.csv            simulated camera deployments (camera_id, reserve, emirate, lat, lon, ...)
  images.csv             one row per image, with camera, UAE timestamp and ground-truth labels
  species_reference.csv  UAE species list (mammals, reptiles from GBIF; birds from MOCCAE)
  protected_areas.csv    MOCCAE protected areas with coordinates
  data_sources.json      provenance and licenses for every source (for the pitch / README)
"""

import argparse
import hashlib
import math
import re
from datetime import datetime

from _common import PROCESSED_DIR, RAW_DIR, log, read_csv, write_csv, write_json
from fetch_camera_traps import UAE_COUNTERPART

# Terrestrial reserves where camera traps make sense, in order of preference. Names as in the MOCCAE data.
PREFERRED_RESERVES = ["Arabian Oryx", "Al Houbara", "Al Marzoum", "Qaser Al Sarab", "Al Wathba",
                      "Dubai Desert Conservation", "The Wadi Wurayah", "Jabel Hafit"]

# GBIF also holds records of pets, livestock and zoo animals; camera-trap monitoring targets wildlife.
DOMESTIC_OR_CAPTIVE = {"Felis catus", "Canis familiaris", "Canis lupus", "Camelus dromedarius", "Capra hircus",
                       "Ovis aries", "Equus asinus", "Equus caballus", "Bos taurus", "Dolichotis patagonum",
                       "Oryctolagus cuniculus"}


def stable_unit(text):
    """Deterministic pseudo-random number in [0, 1) derived from text."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) / 0x100000000


def load_protected_areas():
    path = RAW_DIR / "bayanat" / "protected-lands-coordinates-in-uae" / "protected-lands-coordinates-in-uae-ds.csv"
    rows = []
    for r in read_csv(path):
        try:
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except (KeyError, ValueError):
            continue
        rows.append({"name": r["Protected Name - EN"].strip(), "name_ar": r["Protected Name - AR"].strip(),
                     "emirate": r["Emirate_EN"].strip(), "type": r["Type_EN"].strip(),
                     "area_km2": float(r["Area"] or 0), "latitude": lat, "longitude": lon})
    return rows


def pick_reserves(areas, n):
    land = [a for a in areas if a["type"].lower().startswith("terrestrial")]
    chosen = []
    for pref in PREFERRED_RESERVES:
        chosen += [a for a in land if a["name"].lower().startswith(pref.lower()) and a not in chosen]
    chosen += sorted((a for a in land if a not in chosen), key=lambda a: -a["area_km2"])
    return chosen[:n]


def place_cameras(source_locations, reserves):
    cameras, per_reserve = {}, {}
    for i, loc in enumerate(sorted(source_locations)):
        res = reserves[i % len(reserves)]
        per_reserve[res["name"]] = per_reserve.get(res["name"], 0) + 1
        # Spread cameras up to ~1/3 of the reserve's radius (max 8 km) around its reference point.
        radius_km = min(math.sqrt(max(res["area_km2"], 1) / math.pi) / 3, 8)
        d = radius_km * math.sqrt(stable_unit(loc + "r"))
        theta = 2 * math.pi * stable_unit(loc + "t")
        lat = res["latitude"] + (d / 111.0) * math.cos(theta)
        lon = res["longitude"] + (d / (111.0 * math.cos(math.radians(res["latitude"])))) * math.sin(theta)
        short = re.sub(r"\(.*?\)", "", res["name"]).replace("The ", "")
        code = "".join(w[0] for w in short.split() if w[0].isalpha()).upper()
        cameras[loc] = {
            "camera_id": f"CAM-{code}-{per_reserve[res['name']]:02d}",
            "reserve": res["name"], "reserve_ar": res["name_ar"], "emirate": res["emirate"],
            "latitude": round(lat, 5), "longitude": round(lon, 5),
            "source_location": loc, "simulated": True,
        }
    return cameras


def shift_years(dt_str, target_last_year, max_year):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    try:
        return dt.replace(year=dt.year + (target_last_year - max_year))
    except ValueError:  # 29 Feb -> 28 Feb
        return dt.replace(year=dt.year + (target_last_year - max_year), day=28)


def build_species_reference():
    rows = []
    for r in read_csv(RAW_DIR / "gbif" / "uae_species.csv"):
        rows.append({**r, "source": "GBIF", "domestic_or_captive": r["scientific_name"] in DOMESTIC_OR_CAPTIVE})
    birds_dir = RAW_DIR / "bayanat" / "list-of-local-aves-birds-in-the-uae-2023"
    for path in birds_dir.glob("*.csv"):
        for r in read_csv(path):
            sci = next((v for k, v in r.items() if k and "Scientific" in k), "").strip()
            if not sci:
                continue
            common_ar = next((v for k, v in r.items() if k and "Common" in k), "").strip()
            rows.append({"scientific_name": sci, "common_name_ar": common_ar, "taxon_group": "Aves",
                         "class": "Aves", "source": "MOCCAE via Bayanat", "domestic_or_captive": False})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reserves", type=int, default=8, help="Number of reserves to place cameras in (default 8)")
    ap.add_argument("--last-year", type=int, default=2025, help="Shift timestamps so the latest year is this")
    args = ap.parse_args(argv)

    areas = load_protected_areas()
    reserves = pick_reserves(areas, args.reserves)
    log("Reserves used for simulated cameras: " + ", ".join(r["name"] for r in reserves))

    images = []
    for sel in sorted((RAW_DIR / "camera_traps").glob("*/selection.csv")):
        images += read_csv(sel)
    if not images:
        raise SystemExit("No camera-trap images found. Run fetch_camera_traps.py first.")

    # Re-apply the UAE counterpart mapping so fixes to it don't require re-downloading images.
    for r in images:
        labels = [l for l in r["ground_truth"].split("|") if l in UAE_COUNTERPART]
        r["uae_counterpart"] = "|".join(UAE_COUNTERPART[l][0] for l in labels)
        r["uae_match"] = "|".join(UAE_COUNTERPART[l][1] for l in labels)

    cameras = place_cameras({f"{r['dataset']}:{r['source_location']}" for r in images}, reserves)
    max_year = max(int(r["datetime"][:4]) for r in images)
    for r in images:
        cam = cameras[f"{r['dataset']}:{r['source_location']}"]
        r["original_datetime"] = r["datetime"]
        r["datetime"] = shift_years(r["datetime"], args.last_year, max_year).isoformat(sep=" ")
        r.update({k: cam[k] for k in ("camera_id", "reserve", "emirate", "latitude", "longitude")})

    image_cols = ["image_id", "file_path", "camera_id", "reserve", "emirate", "latitude", "longitude",
                  "datetime", "seq_id", "frame_num", "seq_num_frames", "ground_truth", "is_empty",
                  "is_night", "uae_counterpart", "uae_match", "dataset", "source_location",
                  "original_datetime", "source_url", "selection_bucket", "width", "height"]
    write_csv(PROCESSED_DIR / "images.csv", images, image_cols)
    write_csv(PROCESSED_DIR / "cameras.csv", sorted(cameras.values(), key=lambda c: c["camera_id"]))
    write_csv(PROCESSED_DIR / "protected_areas.csv", areas)
    species = build_species_reference()
    write_csv(PROCESSED_DIR / "species_reference.csv", species,
              ["scientific_name", "common_name", "common_name_ar", "taxon_group", "class", "order", "family",
               "genus", "iucn_category", "iucn_code", "uae_record_count", "domestic_or_captive",
               "gbif_species_key", "source"])

    write_json(PROCESSED_DIR / "data_sources.json", {
        "camera_trap_images": {
            "source": "LILA BC - Snapshot Kgalagadi & Snapshot Karoo (Snapshot Safari)",
            "url": "https://lila.science/datasets", "license": "CDLA-Permissive-1.0",
            "note": "Real camera-trap photos from comparable arid habitats; NOT UAE images.",
        },
        "camera_locations": {
            "source": "MOCCAE 'Protected Lands Coordinates in UAE' via bayanat.ae",
            "note": "Real reserve coordinates; camera positions inside them are SIMULATED.",
        },
        "timestamps": {"note": f"Real time-of-day and season, years shifted so the latest is {args.last_year}."},
        "species_reference": {
            "source": "GBIF.org UAE occurrence records (mammals, reptiles) + MOCCAE local bird list (Bayanat)",
            "url": "https://www.gbif.org/country/AE/summary",
        },
        "protected_areas": {"source": "MOCCAE via bayanat.ae", "url": "https://bayanat.ae"},
    })
    log(f"Processed: {len(images)} images, {len(cameras)} cameras, {len(species)} species, "
        f"{len(areas)} protected areas -> {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
