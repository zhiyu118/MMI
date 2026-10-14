"""Runs every implemented source's pull script. Stubs (raising NotImplementedError)
are skipped with a warning rather than failing the whole refresh.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmi import michigan  # noqa: E402
from mmi.sources import acs, bls_laus, cnt_ht, hrsa, pep, sfid  # noqa: E402

# cdc_natality isn't runnable — birth rate comes from pep.py instead. See its docstring.
# hrsa is split: HPSA rolls on a monthly cadence (no fixed release date, drifts
# fast — see SESSION_NOTES), AHRF is genuinely annual and wasteful to re-pull
# more often (large file, doesn't change more than once a year).
ANNUAL_SOURCES = [
    ("acs", acs.main),
    ("pep", pep.main),
    ("hrsa_ahrf", hrsa.main_ahrf),
    ("sfid", sfid.main),
    ("cnt_ht", cnt_ht.main),
    ("michigan_acs", michigan.main_acs),
    ("michigan_cnt", michigan.main_cnt),
]
MONTHLY_SOURCES = [
    ("bls_laus", bls_laus.main),
    ("hrsa_hpsa", hrsa.main_hpsa),
    ("michigan_bls", michigan.main_bls),
]


def run(sources):
    failures = []
    for name, func in sources:
        try:
            func()
        except NotImplementedError as e:
            print(f"SKIPPED {name}: {e}")
        except Exception as e:
            print(f"FAILED {name}: {e}")
            failures.append(name)
    if failures:
        raise SystemExit(f"Refresh had failures (not just planned skips): {failures}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "annual"
    run(ANNUAL_SOURCES if target == "annual" else MONTHLY_SOURCES)
