"""Reporting and WCRT comparison helpers."""

from __future__ import annotations

from typing import Dict, List

from .models import EPS


def add_wcrt_comparison(rows: List[dict], analytical_wcrt_us: Dict[int, float]) -> List[dict]:
    compared: List[dict] = []
    for row in rows:
        out = dict(row)
        stream_id = int(row["stream_id"])
        observed = row.get("max_rt_us", "")
        if stream_id in analytical_wcrt_us and observed != "":
            observed_float = float(observed)
            wcrt = analytical_wcrt_us[stream_id]
            out["analytical_wcrt_us"] = wcrt
            out["slack_wcrt_minus_observed_us"] = wcrt - observed_float
            out["observed_leq_wcrt"] = observed_float <= wcrt + EPS
        else:
            out["analytical_wcrt_us"] = ""
            out["slack_wcrt_minus_observed_us"] = ""
            out["observed_leq_wcrt"] = ""
        compared.append(out)
    return compared
