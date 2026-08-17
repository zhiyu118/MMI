"""Runs every implemented source's pull script. Stubs (raising NotImplementedError)
are skipped with a warning rather than failing the whole refresh.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmi.sources import acs, bls_laus, cnt_ht, hrsa, pep, sfid  # noqa: E402

# cdc_natality isn't runnable — birth rate comes from pep.py instead. See its docstring.
ANNUAL_SOURCES = [acs, pep, hrsa, sfid, cnt_ht]
MONTHLY_SOURCES = [bls_laus]


def run(modules):
    failures = []
    for mod in modules:
        name = mod.__name__.rsplit(".", 1)[-1]
        try:
            mod.main()
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
