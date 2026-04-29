from src.parser import load_all_testcases
from src.analysis import compute_wcrt

COL_W = [8, 10, 8, 12, 10]
HEADER = f"{'ID':<{COL_W[0]}}{'Name':<{COL_W[1]}}{'PCP':<{COL_W[2]}}{'Deadline':<{COL_W[3]}}{'WCRT (us)':<{COL_W[4]}}"
SEPARATOR = "-" * len(HEADER)

def print_results(case_name, streams, topology, routes):
    stream_map = {s["id"]: s for s in streams}
    wcrt = compute_wcrt(streams, topology, routes)

    print(f"\n{'=' * len(SEPARATOR)}")
    print(f"  {case_name}")
    print(f"{'=' * len(SEPARATOR)}")
    print(HEADER)
    print(SEPARATOR)
    for sid in sorted(wcrt):
        s = stream_map[sid]
        deadline = s["destinations"][0]["deadline"]
        w = wcrt[sid]
        status = "OK" if w <= deadline else "MISS"
        print(f"{sid:<{COL_W[0]}}{s['name']:<{COL_W[1]}}{s['PCP']:<{COL_W[2]}}{deadline:<{COL_W[3]}}{w:<{COL_W[4]}.2f}  {status}")
    print(SEPARATOR)

def main():
    testcases = load_all_testcases(".")
    for case_name, (streams, topology, routes) in testcases.items():
        print_results(case_name, streams, topology, routes)

if __name__ == "__main__":
    main()