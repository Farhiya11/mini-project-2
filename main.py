import argparse
import csv
import os

from src.parser import load_all_testcases
from src.analysis import compute_wcrt

COL_W = [34, 8, 10, 8, 12, 10]
HEADER = (
    f"{'Case':<{COL_W[0]}}"
    f"{'ID':<{COL_W[1]}}"
    f"{'Name':<{COL_W[2]}}"
    f"{'PCP':<{COL_W[3]}}"
    f"{'Deadline':<{COL_W[4]}}"
    f"{'WCRT (us)':<{COL_W[5]}}"
)
SEPARATOR = "-" * len(HEADER)


def class_from_pcp(pcp):
    if pcp == 2:
        return "A"
    if pcp == 1:
        return "B"
    if pcp == 0:
        return "BE"
    return f"PCP{pcp}"


def print_results(all_rows):
    print(HEADER)
    print(SEPARATOR)

    for row in all_rows:
        status = "OK" if row["wcrt_us"] <= row["deadline_us"] else "MISS"
        print(
            f"{row['case']:<{COL_W[0]}}"
            f"{row['stream_id']:<{COL_W[1]}}"
            f"{row['name']:<{COL_W[2]}}"
            f"{row['pcp']:<{COL_W[3]}}"
            f"{row['deadline_us']:<{COL_W[4]}}"
            f"{row['wcrt_us']:<{COL_W[5]}.2f}"
            f"  {status}"
        )

    print(SEPARATOR)


def write_csv(rows, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        "case",
        "stream_id",
        "name",
        "class",
        "pcp",
        "deadline_us",
        "wcrt_us",
        "deadline_status",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            out = dict(row)
            out["deadline_status"] = "OK" if row["wcrt_us"] <= row["deadline_us"] else "MISS"
            writer.writerow(out)


def main():
    parser = argparse.ArgumentParser(description="Compute AVB WCRTs for TSN test cases.")
    parser.add_argument(
        "--base",
        default=".",
        help="Repository base path containing test_cases/",
    )
    parser.add_argument(
        "--out",
        default="results/wcrt_results.csv",
        help="CSV output path",
    )
    parser.add_argument(
        "--include-be",
        action="store_true",
        help="Also include PCP 0 / BE streams in the output. By default only AVB streams are written.",
    )
    args = parser.parse_args()

    testcases = load_all_testcases(args.base)

    if not testcases:
        raise RuntimeError("No test cases found. Expected folders under test_cases/ containing topology.json, streams.json, and routes.json.")

    all_rows = []

    for case_name, (streams, topology, routes) in testcases.items():
        stream_map = {s["id"]: s for s in streams}
        wcrt = compute_wcrt(streams, topology, routes)

        for sid in sorted(wcrt):
            s = stream_map[sid]
            pcp = s["PCP"]

            if not args.include_be and pcp == 0:
                continue

            deadline = s["destinations"][0]["deadline"]

            all_rows.append(
                {
                    "case": case_name,
                    "stream_id": sid,
                    "name": s["name"],
                    "class": class_from_pcp(pcp),
                    "pcp": pcp,
                    "deadline_us": deadline,
                    "wcrt_us": round(wcrt[sid], 6),
                }
            )

    print_results(all_rows)
    write_csv(all_rows, args.out)

    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()