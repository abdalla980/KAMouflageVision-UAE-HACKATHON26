"""Download MOCCAE / FCSC environment datasets from Bayanat (bayanat.ae), the UAE federal open data portal.

Bayanat has no public catalogue API, so this script uses the same endpoints the website uses:
  1. POST /DatasetsListing/GetDatasetsListing  (search by title)
  2. GET  /en/Datasets/Dataset-info?id=...       (resource list embedded as JSON in the page)
  3. GET  /api/DatasetResources/DownloadSingle  (the actual .xlsx file)
Dataset ids are session-scoped, so we always search by title first.

Output: data/raw/bayanat/<slug>/*.xlsx + *.csv, and data/raw/bayanat/manifest.json
"""

import argparse
import html
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

import openpyxl
import requests

from _common import RAW_DIR, USER_AGENT, http_request, log, write_csv, write_json

BASE = "https://bayanat.ae"
OUT_DIR = RAW_DIR / "bayanat"

# Exact dataset titles as listed on bayanat.ae (all published by MOCCAE or the
# Federal Competitiveness and Statistics Centre).
DATASETS = [
    "Protected Lands Coordinates in UAE",
    "Protected Lands in UAE",
    "Protected Lands by Area, Emirate and Zone",
    "Designated Protected Areas by Types and Emirates",
    "Natural Reserves in UAE by Emirate, Type and Establishment Year",
    "Long-Range Nature Reserves in the UAE",
    "Areas of Nature Reserves According to the Type and Emirate",
    "List of local Aves (Birds) in the UAE - 2023",
    "Local Birds List",
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


class Bayanat:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        page = http_request("GET", f"{BASE}/en/Datasets", session=self.s).text
        m = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', page)
        if not m:
            raise RuntimeError("Could not obtain Bayanat request token; the site layout may have changed.")
        self.token = m.group(1)

    def search(self, text, page_size=50):
        """Return [(dataset_id, card_text)] for a free-text search."""
        data = {
            "searchText": text, "lang": "en", "Language": "", "Entities": "", "Goals": "",
            "Topics": "", "Subtopics": "", "selectedFromDate": "", "selectedToDate": "",
            "SortingBy": "", "__RequestVerificationToken": self.token,
            "pagingDTO[CurrentPageNumber]": 1, "pagingDTO[PageCount]": page_size,
            "pagingDTO[IsFilterUpdated]": "true",
        }
        r = http_request("POST", f"{BASE}/DatasetsListing/GetDatasetsListing", data=data, session=self.s)
        pv = r.json().get("pv", "")
        results = []
        for m in re.finditer(r'Dataset-info\?id=([\w-]+)"[^>]*>(.*?)</a>', pv, re.S):
            text_ = clean_text(m.group(2))
            if text_:
                results.append((m.group(1), text_))
        return results

    def resources(self, dataset_id):
        page = http_request("GET", f"{BASE}/en/Datasets/Dataset-info", params={"id": dataset_id}, session=self.s).text
        items = []
        for raw in re.findall(r"data-item='(\{.*?\})'>", page, re.S):
            d = json.loads(html.unescape(raw))
            items.append({
                "resource_id": d["ID"],
                "name": d["NameEN"].strip(),
                "file_url": d.get("FileURL"),
                "columns": (d.get("DataResourcePreview") or {}).get("Columns"),
                "row_count": (d.get("DataResourcePreview") or {}).get("TotalCount"),
            })
        return items

    def download(self, resource_id, filename):
        r = http_request("GET", f"{BASE}/api/DatasetResources/DownloadSingle", session=self.s, timeout=120,
                         params={"resourceID": resource_id, "fileName": filename})
        return r.content


def save_resource(content, folder, stem):
    """Save a downloaded resource and write a UTF-8 CSV copy. Bayanat serves both .xlsx and .csv files."""
    if content[:2] == b"PK":
        src = folder / f"{stem}.xlsx"
        src.write_bytes(content)
        return src, xlsx_to_csv(src, folder / f"{stem}.csv")
    src = folder / f"{stem}.csv"
    text = content.decode("utf-8-sig", errors="replace")
    src.write_text(text, encoding="utf-8")
    return src, max(len([l for l in text.splitlines() if l.strip()]) - 1, 0)


def xlsx_to_csv(xlsx_path, csv_path):
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = [[("" if v is None else str(v).strip()) for v in row] for row in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if any(r)]
    if not rows:
        return 0
    header = [h or f"col_{i}" for i, h in enumerate(rows[0])]
    write_csv(csv_path, [dict(zip(header, r)) for r in rows[1:]], header)
    return len(rows) - 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extra-search", nargs="*", default=[], help="Also list (not download) results for these search terms")
    args = ap.parse_args(argv)

    api = Bayanat()
    manifest = {"source": "bayanat.ae (UAE Federal open data portal)",
                "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "datasets": []}

    for title in DATASETS:
        # Punctuation such as "(Birds)" can break the portal search, so retry with the first words.
        match = None
        for query in (title, " ".join(title.split()[:3])):
            hits = api.search(query)
            match = next(((i, t) for i, t in hits if t.lower().startswith(title.lower())), None)
            if match:
                break
        if not match:
            log(f"  ! not found on Bayanat: {title}")
            continue
        dataset_id, card = match
        publisher = re.search(r"(Ministry Of Climate Change & Environment|Federal Competitiveness and Statistics Center)", card)
        updated = re.search(r"Last Updated Date (\d{2}/\d{2}/\d{4})", card)
        folder = OUT_DIR / slugify(title)
        folder.mkdir(parents=True, exist_ok=True)
        entry = {"title": title, "publisher": publisher.group(1) if publisher else None,
                 "last_updated": updated.group(1) if updated else None,
                 "page_url": f"{BASE}/en/Datasets/Dataset-info?id={quote(dataset_id)}",
                 "resources": []}
        for res in api.resources(dataset_id):
            content = api.download(res["resource_id"], res["name"])
            src, n = save_resource(content, folder, slugify(res["name"]))
            entry["resources"].append({**res, "local_file": src.relative_to(OUT_DIR.parent.parent).as_posix(),
                                       "rows": n})
            log(f"  + {title} -> {src.name} ({n} rows)")
        manifest["datasets"].append(entry)

    for term in args.extra_search:
        log(f"\nSearch '{term}':")
        for _, text_ in api.search(term):
            log(f"  - {text_[:120]}")

    write_json(OUT_DIR / "manifest.json", manifest)
    log(f"Bayanat: {len(manifest['datasets'])}/{len(DATASETS)} datasets saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
