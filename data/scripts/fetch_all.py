"""Run the full KAMouflage Vision data pipeline in order.

    python data/scripts/fetch_all.py                 # default: 600 camera-trap images
    python data/scripts/fetch_all.py --n-images 200  # quicker, smaller demo set
"""

import argparse

import build_demo_dataset
import fetch_bayanat
import fetch_camera_traps
import fetch_species_reference
from _common import log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-images", type=int, default=600)
    args = ap.parse_args()

    steps = [
        ("Bayanat (MOCCAE protected areas, local species lists)", fetch_bayanat.main, []),
        ("GBIF (UAE species reference + occurrence points)", fetch_species_reference.main, []),
        ("LILA BC camera-trap images", fetch_camera_traps.main, ["--n-images", str(args.n_images)]),
    ]
    failed = []
    for i, (title, fn, fn_args) in enumerate(steps, 1):
        log(f"\n== {i}/4 {title} ==")
        try:
            fn(fn_args)
        except Exception as e:  # one flaky source should not block the others; earlier downloads are kept
            log(f"!! {title} failed: {e!r}")
            failed.append(title)

    log("\n== 4/4 Build processed demo dataset ==")
    build_demo_dataset.main([])
    if failed:
        log("\nSome sources failed (re-run to retry): " + "; ".join(failed))


if __name__ == "__main__":
    main()
