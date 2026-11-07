"""Regenerate rules/p1546_land.csv with the ITU reference implementation of P.1546-6.

ECC T/R 25-08 A1.2.3 defines the coordination threshold for 10 % of the time, so the
table holds 10 % time curves: land path, 50 % locations, rural receiver with 10 m
antenna and 10 m clutter, no terrain information, 1 kW ERP, rounded to 0.01 dB.

    bt_loss(f, 10, h1, 10, 10, "Rural", [d], ["Land"], 0, 50, 0, 1, h1)[0]

With TIME_PERCENT = 50 it reproduces the earlier 50 % table byte for byte (checked).
Py1546 (github.com/eeveetza/Py1546, commit e235629) needs numpy<2 (it uses np.mat) and
matplotlib. Not run by the tests; run it by hand when the grid or time percentage changes:

    MPLBACKEND=Agg <venv-with-numpy<2-and-matplotlib>/bin/python \\
        scripts/gen_p1546_table.py <path to Py1546 src/src> > rules/p1546_land.csv
"""

import contextlib
import csv
import sys
import warnings

TIME_PERCENT = 10
FREQS_MHZ = (100, 600, 2000)
HEIGHTS_M = (10, 20, 37.5, 75, 150, 300, 600, 1200)
DISTANCES_KM = (
    *range(1, 11),
    *range(15, 101, 5),
    *range(110, 201, 10),
    *range(225, 1001, 25),
)


def main(py1546_src):
    sys.path.insert(0, py1546_src)
    warnings.filterwarnings("ignore")
    from Py1546 import P1546

    writer = csv.writer(sys.stdout)
    writer.writerow(["f_mhz", "h1_m", "d_km", "e_dbuv_m"])
    for f in FREQS_MHZ:
        for h1 in HEIGHTS_M:
            for d in DISTANCES_KM:
                # Py1546 prints clutter warnings to stdout; keep them out of the CSV.
                with contextlib.redirect_stdout(sys.stderr):
                    e = P1546.bt_loss(
                        f, TIME_PERCENT, h1, 10, 10, "Rural", [d], ["Land"], 0, 50, 0, 1, h1
                    )[0]
                writer.writerow([f, f"{h1:g}", d, round(float(e), 2)])


if __name__ == "__main__":
    main(sys.argv[1])
