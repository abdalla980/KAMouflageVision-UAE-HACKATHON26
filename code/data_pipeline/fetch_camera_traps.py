"""Download a curated demo subset of real camera-trap images from LILA BC (lila.science).

We use arid / semi-arid Snapshot Safari projects whose habitat looks like the UAE desert. Instead of the
full multi-GB archives we read the COCO Camera Traps metadata and download only a balanced subset,
always keeping complete *sequences* (bursts of 3-10 frames from one trigger), because the pipeline
uses all frames of a burst to identify camouflaged animals.

Subset mix (per dataset quota):
  - every sequence with a species that also lives in the UAE (or a close relative)
  - night sequences (19:00-06:00), the hardest images for humans
  - ~35% empty sequences, to show the automatic empty-frame filter
  - other animals to fill up

Images are resized (EXIF kept) to save disk space. Human images were removed by LILA for privacy.

Output per dataset: data/raw/camera_traps/<key>/images/... + selection.csv + metadata zip
"""

import argparse
import io
import json
import random
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

from _common import RAW_DIR, http_get, log, write_csv, write_json

OUT_DIR = RAW_DIR / "camera_traps"
GCP = "https://storage.googleapis.com/public-datasets-lila/snapshot-safari"
LICENSE = "CDLA-Permissive-1.0 (https://cdla.io/permissive-1-0/)"

DATASETS = {
    "kga": {
        "name": "Snapshot Kgalagadi (Kalahari desert, South Africa/Botswana)",
        "metadata_url": f"{GCP}/KGA/SnapshotKgalagadi_S1_v1.0.json.zip",
        "image_base": f"{GCP}/KGA/KGA_public/",
        "info_url": "https://lila.science/datasets/snapshot-kgalagadi",
    },
    "kar": {
        "name": "Snapshot Karoo (semi-arid Karoo, South Africa)",
        "metadata_url": f"{GCP}/KAR/SnapshotKaroo_S1_v1.0.json.zip",
        "image_base": f"{GCP}/KAR/KAR_public/",
        "info_url": "https://lila.science/datasets/snapshot-karoo",
    },
}

# Source label -> (UAE counterpart used in the demo, how close the match is).
# "same species" / "same genus" / "same family" are biological matches; "analogue" only means a
# similar-looking animal in a similar niche. The pitch must present these as stand-ins, not UAE data.
UAE_COUNTERPART = {
    "gemsbokoryx": ("Arabian Oryx (Oryx leucoryx)", "same genus"),
    "caracal": ("Caracal (Caracal caracal)", "same species"),
    "catafricanwild": ("Arabian Wildcat (Felis lybica)", "same species"),
    "honeybadger": ("Honey Badger (Mellivora capensis)", "same species"),
    "harecape": ("Cape Hare (Lepus capensis)", "same species"),
    "hare": ("Cape Hare (Lepus capensis)", "same genus"),
    "foxcape": ("Arabian Red Fox / Blanford's Fox (Vulpes)", "same genus"),
    "foxbateared": ("Ruppell's Fox (Vulpes rueppellii)", "analogue"),
    "hyenabrown": ("Striped Hyena (Hyaena hyaena)", "same family"),
    "hyenaspotted": ("Striped Hyena (Hyaena hyaena)", "same family"),
    "steenbok": ("Arabian / Sand Gazelle (Gazella)", "analogue"),
    "springbok": ("Arabian / Sand Gazelle (Gazella)", "analogue"),
    "duiker": ("Arabian / Sand Gazelle (Gazella)", "analogue"),
    "duikercommongrey": ("Arabian / Sand Gazelle (Gazella)", "analogue"),
    "klipspringer": ("Arabian Tahr (Arabitragus jayakari)", "analogue"),
    "bustardkori": ("Houbara Bustard (Chlamydotis undulata)", "same family"),
    "bustardludwigs": ("Houbara Bustard (Chlamydotis undulata)", "same family"),
    "mongoosesmallcapegrey": ("White-tailed Mongoose (Ichneumia albicauda)", "same family"),
    "mongooseyellow": ("White-tailed Mongoose (Ichneumia albicauda)", "same family"),
    "porcupine": ("Indian Crested Porcupine (Hystrix indica)", "same genus"),
    "rodent": ("Desert rodents (jirds, gerbils, jerboas)", "analogue"),
    "reptilesamphibians": ("Desert reptiles (e.g. spiny-tailed lizard)", "analogue"),
    "tortoise": ("Desert reptiles (e.g. spiny-tailed lizard)", "analogue"),
    "birdofprey": ("Birds of prey", "analogue"),
    "birdsofprey": ("Birds of prey", "analogue"),
}
DROP_LABELS = {"human"}  # images removed by LILA for privacy


def load_metadata(key, cfg):
    folder = OUT_DIR / key
    folder.mkdir(parents=True, exist_ok=True)
    zpath = folder / "metadata.json.zip"
    if not zpath.exists():
        log(f"[{key}] downloading metadata ...")
        zpath.write_bytes(http_get(cfg["metadata_url"], timeout=300).content)
    with zipfile.ZipFile(zpath) as z:
        raw = z.read(z.namelist()[0]).decode("utf-8")
    return json.loads(raw.replace("NaN", "null"))


def build_sequences(meta):
    cats = {c["id"]: c["name"] for c in meta["categories"]}
    labels = defaultdict(set)
    for a in meta["annotations"]:
        labels[a["seq_id"]].add(cats[a["category_id"]])
    frames = defaultdict(list)
    for img in meta["images"]:
        if not img.get("corrupt"):
            frames[img["seq_id"]].append(img)
    seqs = []
    for seq_id, imgs in frames.items():
        lab = labels.get(seq_id, set())
        if not lab or lab & DROP_LABELS:
            continue
        imgs.sort(key=lambda i: i.get("frame_num", 0))
        hour = int(imgs[0]["datetime"][11:13])
        seqs.append({"seq_id": seq_id, "images": imgs, "labels": sorted(lab),
                     "empty": lab == {"empty"},
                     "night": hour >= 19 or hour < 6,
                     "uae_relevant": any(l in UAE_COUNTERPART for l in lab)})
    return seqs


def interleave_by_species(pool):
    """Round-robin over species so rare animals (caracal, wildcat ...) are not crowded out by common ones."""
    groups = defaultdict(list)
    for s in pool:
        groups[s["labels"][0]].append(s)
    out, queues = [], list(groups.values())
    while queues:
        out += [q.pop(0) for q in queues]
        queues = [q for q in queues if q]
    return out


def select_sequences(seqs, n_images, rng, empty_share=0.35):
    """Fill the image budget in priority order, always taking whole sequences."""
    rng.shuffle(seqs)
    buckets = [
        ("uae", interleave_by_species([s for s in seqs if s["uae_relevant"]]), 0.40),
        ("night", interleave_by_species([s for s in seqs if s["night"] and not s["empty"] and not s["uae_relevant"]]), 0.10),
        ("night_empty", [s for s in seqs if s["night"] and s["empty"]], 0.05),
        ("empty", [s for s in seqs if s["empty"] and not s["night"]], empty_share - 0.05),
        ("other", [s for s in seqs if not s["empty"] and not s["uae_relevant"] and not s["night"]], 1.0),
    ]
    chosen, used, total = [], set(), 0
    for name, pool, share in buckets:
        budget = n_images * share if name != "other" else n_images - total
        taken = 0
        for s in pool:
            if s["seq_id"] in used or taken + len(s["images"]) > budget or total + len(s["images"]) > n_images:
                continue
            chosen.append({**s, "bucket": name})
            used.add(s["seq_id"])
            taken += len(s["images"])
            total += len(s["images"])
    return chosen


def download_image(url, dest, max_side):
    if dest.exists():
        return True
    content = http_get(url, timeout=120).content
    im = Image.open(io.BytesIO(content))
    exif = im.info.get("exif")
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=88, **({"exif": exif} if exif else {}))
    return True


def process_dataset(key, n_images, max_side, workers, seed):
    cfg = DATASETS[key]
    meta = load_metadata(key, cfg)
    seqs = build_sequences(meta)
    chosen = select_sequences(seqs, n_images, random.Random(seed))
    log(f"[{key}] {len(seqs)} usable sequences -> selected {len(chosen)} sequences, "
        f"{sum(len(s['images']) for s in chosen)} images")

    rows, jobs = [], []
    for s in chosen:
        species = [l for l in s["labels"] if l != "empty"]
        counterpart = [UAE_COUNTERPART[l] for l in species if l in UAE_COUNTERPART]
        for img in s["images"]:
            dest = OUT_DIR / key / "images" / img["file_name"]
            jobs.append((cfg["image_base"] + img["file_name"], dest))
            rows.append({
                "dataset": key,
                "image_id": img["id"],
                "file_path": dest.relative_to(OUT_DIR.parent.parent).as_posix(),
                "source_url": cfg["image_base"] + img["file_name"],
                "seq_id": s["seq_id"],
                "frame_num": img.get("frame_num"),
                "seq_num_frames": img.get("seq_num_frames"),
                "datetime": img["datetime"],
                "source_location": img["location"],
                "ground_truth": "|".join(s["labels"]),
                "is_empty": s["empty"],
                "is_night": s["night"],
                "uae_counterpart": "|".join(c[0] for c in counterpart),
                "uae_match": "|".join(c[1] for c in counterpart),
                "selection_bucket": s["bucket"],
                "width": img.get("width"),
                "height": img.get("height"),
            })

    ok, failed = 0, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_image, url, dest, max_side): (url, dest) for url, dest in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                fut.result()
                ok += 1
            except Exception as e:  # keep going; record the failure
                failed.append(futures[fut][0])
                log(f"  ! {futures[fut][0]}: {e}")
            if i % 100 == 0:
                log(f"[{key}] {i}/{len(jobs)} images")

    failed_set = set(failed)
    rows = [r for r in rows if r["source_url"] not in failed_set]
    write_csv(OUT_DIR / key / "selection.csv", rows)
    write_json(OUT_DIR / key / "source.json", {**cfg, "license": LICENSE,
                                                 "images_downloaded": ok, "images_failed": len(failed)})
    log(f"[{key}] done: {ok} images ok, {len(failed)} failed")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets", nargs="*", default=list(DATASETS), choices=list(DATASETS))
    ap.add_argument("--n-images", type=int, default=600, help="Total images across all datasets (default 600)")
    ap.add_argument("--max-side", type=int, default=1600, help="Resize longest side to this many px (default 1600)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    per_dataset = args.n_images // len(args.datasets)
    total = 0
    for key in args.datasets:
        total += len(process_dataset(key, per_dataset, args.max_side, args.workers, args.seed))
    log(f"Camera traps: {total} images ready under {OUT_DIR}")


if __name__ == "__main__":
    main()
