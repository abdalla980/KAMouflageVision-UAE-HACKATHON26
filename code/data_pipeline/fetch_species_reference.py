"""Build the UAE species reference list from GBIF (gbif.org).

For each target taxon (default: mammals and squamate reptiles) we take every species that has
occurrence records in the UAE, then add English name, family, IUCN Red List category and record count.
We also keep the georeferenced occurrence points (used later as a geographic prior and on the map).

Output:
  data/raw/gbif/uae_species.csv
  data/raw/gbif/uae_occurrences.csv
"""

import argparse
from concurrent.futures import ThreadPoolExecutor

from _common import RAW_DIR, http_get, log, write_csv, write_json

API = "https://api.gbif.org/v1"
OUT_DIR = RAW_DIR / "gbif"


def taxon_key(name, rank):
    d = http_get(f"{API}/species/match", params={"name": name, "rank": rank, "strict": "true"}).json()
    if "usageKey" not in d:
        raise RuntimeError(f"GBIF could not match {rank} {name}")
    return d["usageKey"]


def species_facets(country, tkey):
    params = {"country": country, "taxonKey": tkey, "limit": 0, "facet": "speciesKey", "facetLimit": 1000}
    d = http_get(f"{API}/occurrence/search", params=params).json()
    return {int(c["name"]): c["count"] for c in d["facets"][0]["counts"]} if d["facets"] else {}


def species_details(key):
    sp = http_get(f"{API}/species/{key}").json()
    try:
        iucn = http_get(f"{API}/species/{key}/iucnRedListCategory", retries=1).json()
    except Exception:
        iucn = {}
    vern = http_get(f"{API}/species/{key}/vernacularNames", params={"limit": 100}).json().get("results", [])
    english = [v["vernacularName"] for v in vern if v.get("language") == "eng"]
    common = max(set(english), key=english.count) if english else ""
    return {
        "gbif_species_key": key,
        "scientific_name": sp.get("species") or sp.get("canonicalName"),
        "common_name": common,
        "class": sp.get("class", ""),
        "order": sp.get("order", ""),
        "family": sp.get("family", ""),
        "genus": sp.get("genus", ""),
        "iucn_category": iucn.get("category", "NOT_EVALUATED"),
        "iucn_code": iucn.get("code", ""),
    }


def occurrences(country, tkey, max_records):
    rows, offset = [], 0
    while offset < max_records:
        params = {"country": country, "taxonKey": tkey, "hasCoordinate": "true",
                  "hasGeospatialIssue": "false", "limit": 300, "offset": offset}
        d = http_get(f"{API}/occurrence/search", params=params).json()
        for o in d["results"]:
            if not o.get("speciesKey"):
                continue
            rows.append({
                "gbif_occurrence_key": o["key"],
                "gbif_species_key": o["speciesKey"],
                "scientific_name": o.get("species", ""),
                "latitude": o.get("decimalLatitude"),
                "longitude": o.get("decimalLongitude"),
                "event_date": (o.get("eventDate") or "")[:10],
                "basis_of_record": o.get("basisOfRecord", ""),
                "dataset_key": o.get("datasetKey", ""),
                "license": o.get("license", ""),
            })
        offset += 300
        if d.get("endOfRecords"):
            break
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", default="AE", help="ISO 3166-1 alpha-2 country code (default AE)")
    # Note: in the GBIF backbone, Squamata (lizards & snakes) is ranked as a CLASS.
    ap.add_argument("--taxa", nargs="*", default=["Mammalia:CLASS", "Squamata:CLASS"],
                    help="Taxa as Name:RANK (default: Mammalia:CLASS Squamata:CLASS)")
    ap.add_argument("--max-occurrences", type=int, default=5000, help="Max occurrence points per taxon")
    args = ap.parse_args(argv)

    species_rows, occ_rows = [], []
    for spec in args.taxa:
        name, rank = spec.split(":")
        tkey = taxon_key(name, rank)
        counts = species_facets(args.country, tkey)
        log(f"GBIF {name}: {len(counts)} species with records in {args.country}")
        with ThreadPoolExecutor(max_workers=8) as pool:
            details = list(pool.map(species_details, counts))
        for d in details:
            d["uae_record_count"] = counts[d["gbif_species_key"]]
            d["taxon_group"] = name
        species_rows += details
        occ_rows += occurrences(args.country, tkey, args.max_occurrences)

    species_rows.sort(key=lambda r: (r["taxon_group"], -r["uae_record_count"]))
    write_csv(OUT_DIR / "uae_species.csv", species_rows)
    write_csv(OUT_DIR / "uae_occurrences.csv", occ_rows)
    write_json(OUT_DIR / "README.json", {
        "source": "GBIF.org occurrence and species APIs",
        "query": {"country": args.country, "taxa": args.taxa},
        "citation": "GBIF.org (accessed via API). Individual records carry their own licenses (see 'license' column).",
    })
    log(f"GBIF: {len(species_rows)} species, {len(occ_rows)} occurrence points saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
