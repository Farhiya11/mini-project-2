"""Route handling for the test-case-generator route format.

Important convention: in routes.json a hop {"node": X, "port": p} names the
EGRESS port used when leaving node X. Therefore the first source end-system hop
is a real output port and must be included in the simulated path.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .models import Link


def route_to_links(flow_id: int, routes: Iterable[dict], links: Dict[str, Link]) -> Tuple[str, ...]:
    route = next((route for route in routes if int(route["flow_id"]) == int(flow_id)), None)
    if route is None:
        raise ValueError(f"No route found for flow_id={flow_id}.")
    if not route.get("paths"):
        raise ValueError(f"Route for flow_id={flow_id} has no paths.")

    path = route["paths"][0]
    if len(path) < 2:
        raise ValueError(f"Route for flow_id={flow_id} has fewer than two hops.")

    by_egress = {(link.source, link.source_port): link for link in links.values()}
    link_ids = []
    for index, hop in enumerate(path[:-1]):
        node = str(hop["node"])
        egress_port = int(hop["port"])
        next_node = str(path[index + 1]["node"])

        link = by_egress.get((node, egress_port))
        if link is None:
            raise ValueError(
                f"No topology link leaves node {node} on egress port {egress_port} "
                f"for flow {flow_id}."
            )
        if link.destination != next_node:
            raise ValueError(
                f"Route/topology mismatch for flow {flow_id}: hop {node}:{egress_port} "
                f"leads to {link.destination}, but routes.json next hop is {next_node}."
            )
        link_ids.append(link.id)

    return tuple(link_ids)
