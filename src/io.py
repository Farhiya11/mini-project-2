"""Input/output helpers for generator JSON files and result CSVs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .models import ALL_PCPS, Link, Stream
from .routing import route_to_links


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def unwrap_topology(topology_json: dict) -> dict:
    return topology_json["topology"] if "topology" in topology_json else topology_json


def parse_links(topology_json: dict, force_bandwidth_mbps: float | None = None) -> Dict[str, Link]:
    """Parse directed links, honoring per-link bandwidth overrides.

    If ``force_bandwidth_mbps`` is provided, it intentionally overrides every
    link. This is useful when you want to state the simplified assumption that
    the whole network uses one rate.
    """

    topology = unwrap_topology(topology_json)
    default_bw = float(topology.get("default_bandwidth_mbps", 100.0))
    links: Dict[str, Link] = {}
    for raw in topology["links"]:
        bw = force_bandwidth_mbps if force_bandwidth_mbps is not None else raw.get("bandwidth_mbps", default_bw)
        links[str(raw["id"])] = Link(
            id=str(raw["id"]),
            source=str(raw["source"]),
            destination=str(raw["destination"]),
            source_port=int(raw["sourcePort"]),
            destination_port=int(raw["destinationPort"]),
            delay_us=float(raw.get("delay", 0.0)),
            bandwidth_mbps=float(bw),
        )
    return links


def parse_streams(streams_json: dict, routes_json: dict, links: Dict[str, Link]) -> Dict[int, Stream]:
    routes = routes_json["routes"]
    streams: Dict[int, Stream] = {}
    for raw in streams_json["streams"]:
        stream_id = int(raw["id"])
        destinations = raw.get("destinations", [])
        if len(destinations) != 1:
            raise ValueError(
                f"Simulator first implementation supports one destination per stream; "
                f"stream {stream_id} has {len(destinations)}."
            )
        pcp = int(raw["PCP"])
        if pcp not in ALL_PCPS:
            raise ValueError(f"Unsupported PCP {pcp}; expected one of {ALL_PCPS}.")

        route_link_ids = route_to_links(stream_id, routes, links)
        streams[stream_id] = Stream(
            id=stream_id,
            name=str(raw.get("name", f"Stream{stream_id}")),
            source=str(raw["source"]),
            destination=str(destinations[0]["id"]),
            pcp=pcp,
            size_bytes=int(raw["size"]),
            period_us=float(raw["period"]),
            deadline_us=float(destinations[0]["deadline"]) if "deadline" in destinations[0] else None,
            route_link_ids=route_link_ids,
        )
    return streams


def read_wcrt_csv(path: Path) -> Dict[int, float]:
    """Read the provided WCRTs.csv.

    The current file is tab-separated and uses dots as decimal separators. The
    reader also accepts commas or semicolons to be defensive.
    """

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return {}
    header = lines[0]
    if "\t" in header:
        delimiter = "\t"
    elif ";" in header:
        delimiter = ";"
    else:
        delimiter = ","

    values: Dict[int, float] = {}
    for row in csv.DictReader(lines, delimiter=delimiter):
        values[int(row["ID"])] = float(row["WCRT"].replace(",", "."))
    return values


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: List[dict], columns: Iterable[str]) -> None:
    cols = list(columns)
    if not rows:
        print("(no rows)")
        return

    def fmt(value: object) -> str:
        return f"{value:.6g}" if isinstance(value, float) else str(value)

    widths = {col: max(len(col), *(len(fmt(row.get(col, ""))) for row in rows)) for col in cols}
    print("  ".join(col.ljust(widths[col]) for col in cols))
    print("  ".join("-" * widths[col] for col in cols))
    for row in rows:
        print("  ".join(fmt(row.get(col, "")).ljust(widths[col]) for col in cols))
