def compute_wcrt(streams, topology, routes, idle_slope=0.5):
    """
    Compute Worst-Case Response Times (WCRTs) for AVB streams using CBS analysis.

    For each stream the WCRT is the sum of per-link Worst-Case Delays (WCDs)
    along its route (propagation delays are not included).

    Per link, for stream i with transmission time C_i = frame_size*8 / bandwidth:

      SPI_i  = sum_{j: same PCP, j≠i}  C_j / idle_slope
      LPI_i  = max_{k: PCP_k < PCP_i}  C_k          (0 if none)

      Class A (highest PCP on the link):
        HPI_i  = 0
        WCD_i  = C_i + SPI_i + LPI_i

      Class B (all other streams):
        HPI_i  = LPI_i + max_{j: Class A}  C_j
        WCD_i  = C_i + SPI_i + LPI_i + HPI_i

    Parameters
    ----------
    streams   : list of stream dicts (from streams.json)
    topology  : topology dict (from topology.json)
    routes    : list of route dicts (from routes.json)
    idle_slope: CBS idle-slope fraction (default 0.5)

    Returns
    -------
    dict  stream_id -> WCRT in microseconds
    """
    default_bw = topology.get("default_bandwidth_mbps", 100)

    # link_id -> link dict
    link_map = {link["id"]: link for link in topology["links"]}

    # (source_node, dest_node) -> link_id  (assumes at most one link per pair)
    endpoint_to_link = {
        (link["source"], link["destination"]): link["id"]
        for link in topology["links"]
    }

    # stream_id -> stream dict
    stream_map = {s["id"]: s for s in streams}

    # flow_id -> list of paths; each path is an ordered list of link_ids
    flow_paths = {}
    for route in routes:
        fid = route["flow_id"]
        paths = []
        for path in route["paths"]:
            link_ids = []
            for i in range(len(path) - 1):
                src = path[i]["node"]
                dst = path[i + 1]["node"]
                lid = endpoint_to_link.get((src, dst))
                if lid is not None:
                    link_ids.append(lid)
            paths.append(link_ids)
        flow_paths[fid] = paths

    # link_id -> set of stream_ids that traverse it
    link_streams = {}
    for fid, paths in flow_paths.items():
        for path in paths:
            for lid in path:
                link_streams.setdefault(lid, set()).add(fid)

    def get_C(stream_id, link_id):
        """Transmission time in microseconds."""
        size = stream_map[stream_id]["size"]          # bytes
        bw = link_map[link_id].get("bandwidth_mbps", default_bw)  # Mbps
        return size * 8 / bw

    wcrt = {}
    for stream in streams:
        sid = stream["id"]
        if sid not in flow_paths:
            continue

        max_wcrt = 0.0
        for path in flow_paths[sid]:
            path_wcrt = 0.0
            for lid in path:
                on_link = link_streams.get(lid, set())
                pcp_i = stream_map[sid]["PCP"]

                C_i = get_C(sid, lid)

                max_pcp = max(stream_map[s]["PCP"] for s in on_link)

                # Same Priority Interference
                SPI_i = sum(
                    get_C(j, lid) / idle_slope
                    for j in on_link
                    if j != sid and stream_map[j]["PCP"] == pcp_i
                )

                # Lower Priority Interference
                LPI_i = max(
                    (get_C(k, lid) for k in on_link if stream_map[k]["PCP"] < pcp_i),
                    default=0.0,
                )

                # Higher Priority Interference
                if pcp_i == max_pcp:
                    # Class A — no higher-priority AVB interference
                    HPI_i = 0.0
                else:
                    # Class B
                    max_C_A = max(
                        get_C(j, lid) for j in on_link if stream_map[j]["PCP"] == max_pcp
                    )
                    HPI_i = LPI_i + max_C_A

                path_wcrt += C_i + SPI_i + LPI_i + HPI_i

            max_wcrt = max(max_wcrt, path_wcrt)

        wcrt[sid] = max_wcrt

    return wcrt
