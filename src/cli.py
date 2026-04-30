"""Command-line interface for the TSN/CBS simulator."""

from __future__ import annotations

import argparse
from pathlib import Path

from .engine import Simulator
from .io import load_json, print_table, read_wcrt_csv, write_csv
from .reports import add_wcrt_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Readable TSN/CBS simulator for DRTS Mini-project 2")
    parser.add_argument("--topology", type=Path, required=True, help="Path to topology.json")
    parser.add_argument("--streams", type=Path, required=True, help="Path to streams.json")
    parser.add_argument("--routes", type=Path, required=True, help="Path to routes.json")
    parser.add_argument("--wcrt", type=Path, default=None, help="Optional WCRTs.csv for AVB comparison")
    parser.add_argument("--out", type=Path, default=Path("simulation_results.csv"), help="Per-stream output CSV")
    parser.add_argument("--ports-out", type=Path, default=Path("port_results.csv"), help="Per-port output CSV")
    parser.add_argument("--sim-time", type=float, default=None, help="Simulation time in microseconds")
    parser.add_argument(
        "--hyperperiods",
        type=int,
        default=5,
        help="Used when --sim-time is omitted; releases all streams at t=0 and runs this many hyperperiods",
    )
    parser.add_argument("--warmup", type=float, default=0.0, help="Ignore frames released before this time")
    parser.add_argument(
        "--idle-slope-fraction",
        type=float,
        default=0.5,
        help="Reserved fraction per AVB class. sendSlope is idleSlope - portRate; default gives +0.5C/-0.5C.",
    )
    parser.add_argument(
        "--force-bandwidth-mbps",
        type=float,
        default=None,
        help="Optional simplification: ignore per-link/default JSON rates and force one bandwidth for every link.",
    )
    parser.add_argument("--l2-overhead-bytes", type=int, default=0, help="Optional per-frame on-wire overhead")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    simulator = Simulator(
        topology_json=load_json(args.topology),
        streams_json=load_json(args.streams),
        routes_json=load_json(args.routes),
        idle_slope_fraction_value=args.idle_slope_fraction,
        l2_overhead_bytes=args.l2_overhead_bytes,
        force_bandwidth_mbps=args.force_bandwidth_mbps,
    )

    sim_time_us = args.sim_time if args.sim_time is not None else simulator.default_sim_time_us(args.hyperperiods)
    simulator.run(sim_time_us=sim_time_us, warmup_us=args.warmup, drain=True)

    stream_rows = simulator.per_stream_rows()
    if args.wcrt is not None:
        stream_rows = add_wcrt_comparison(stream_rows, read_wcrt_csv(args.wcrt))

    write_csv(args.out, stream_rows)
    write_csv(args.ports_out, simulator.per_port_rows(sim_time_us))

    print(f"Simulation time: {sim_time_us:g} us")
    print(f"Generated frames: {simulator.generated_frames}")
    print(f"Completed frames observed: {len(simulator.records)}")
    print(f"Wrote: {args.out}")
    print(f"Wrote: {args.ports_out}")

    columns = ["stream_id", "class", "frames_observed", "max_rt_us", "deadline_us", "deadline_misses"]
    if args.wcrt is not None:
        columns += ["analytical_wcrt_us", "slack_wcrt_minus_observed_us", "observed_leq_wcrt"]
    print_table(stream_rows, columns)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
