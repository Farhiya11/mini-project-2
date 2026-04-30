"""Discrete-event TSN/CBS simulation engine."""

from __future__ import annotations

from collections import defaultdict
from math import gcd
from typing import Dict, List

from .cbs import OutputPort
from .events import EventQueue
from .io import parse_links, parse_streams
from .models import ALL_PCPS, AVB_PCPS, EPS, Frame, FrameRecord, Link, Stream


def lcm_int(values: List[int]) -> int:
    result = 1
    for value in values:
        result = result * value // gcd(result, value)
    return result


class Simulator:
    def __init__(
        self,
        topology_json: dict,
        streams_json: dict,
        routes_json: dict,
        idle_slope_fraction_value: float = 0.5,
        l2_overhead_bytes: int = 0,
        force_bandwidth_mbps: float | None = None,
    ) -> None:
        idle_slope_fraction = {pcp: float(idle_slope_fraction_value) for pcp in AVB_PCPS}
        reserved_sum = sum(idle_slope_fraction.values())
        if reserved_sum > 1.0 + EPS:
            raise ValueError(
                f"Invalid CBS reservation: AVB idleSlope fractions sum to {reserved_sum}, "
                "but the validity condition requires <= 1."
            )

        self.event_queue = EventQueue()
        self.links: Dict[str, Link] = parse_links(topology_json, force_bandwidth_mbps=force_bandwidth_mbps)
        self.streams: Dict[int, Stream] = parse_streams(streams_json, routes_json, self.links)
        self.ports: Dict[str, OutputPort] = {
            link_id: OutputPort(link, self.event_queue, idle_slope_fraction, l2_overhead_bytes)
            for link_id, link in self.links.items()
        }
        self.records: List[FrameRecord] = []
        self.generated_frames = 0
        self._frame_uid = 0

    def default_sim_time_us(self, hyperperiods: int = 5) -> float:
        """Return several hyperperiods for critical-instant simulation.

        The test cases use integer microsecond periods. If a later test uses
        non-integer periods, fall back to several maximum periods.
        """

        periods = [stream.period_us for stream in self.streams.values()]
        if all(abs(p - round(p)) <= EPS for p in periods):
            return float(hyperperiods * lcm_int([int(round(p)) for p in periods]))
        return float(hyperperiods * max(periods))

    def run(self, sim_time_us: float, warmup_us: float = 0.0, drain: bool = True) -> None:
        self._schedule_critical_instant_releases(sim_time_us)
        hard_stop = sim_time_us + (10 * max((stream.period_us for stream in self.streams.values()), default=0.0))

        while self.event_queue:
            now_us, events = self.event_queue.pop_batch()
            if not drain and now_us > sim_time_us + EPS:
                break
            if drain and now_us > hard_stop + EPS:
                break

            for port in self.ports.values():
                port.update_credit(now_us)

            for event in events:
                if event.kind == "release":
                    frame = event.item
                    assert isinstance(frame, Frame)
                    self.ports[frame.current_link_id].enqueue(frame, now_us)
                elif event.kind == "tx_complete":
                    link_id = str(event.item)
                    port = self.ports[link_id]
                    frame = port.complete_transmission(now_us)
                    frame.hop_index += 1
                    propagation_done_us = now_us + self.links[link_id].delay_us
                    self.event_queue.push(propagation_done_us, "arrival", frame)
                elif event.kind == "arrival":
                    frame = event.item
                    assert isinstance(frame, Frame)
                    if frame.finished_route:
                        if frame.release_time_us >= warmup_us - EPS:
                            self.records.append(
                                FrameRecord(
                                    frame_uid=frame.uid,
                                    stream_id=frame.stream_id,
                                    sequence_number=frame.sequence_number,
                                    release_time_us=frame.release_time_us,
                                    arrival_time_us=now_us,
                                    response_time_us=now_us - frame.release_time_us,
                                )
                            )
                    else:
                        self.ports[frame.current_link_id].enqueue(frame, now_us)
                elif event.kind == "credit_wakeup":
                    # The port will be retried below. The token is diagnostic only.
                    pass
                else:
                    raise RuntimeError(f"Unknown event kind: {event.kind}")

            # A store-and-forward completion can make a downstream port non-empty.
            # Mini-project instances are small, so retrying all ports is clearer than
            # maintaining a touched-port set.
            for port in self.ports.values():
                port.try_start_transmission(now_us)

    def _schedule_critical_instant_releases(self, sim_time_us: float) -> None:
        """Release all streams at t=0, then periodically until sim_time_us."""

        for stream in self.streams.values():
            sequence = 0
            t = 0.0
            while t <= sim_time_us + EPS:
                frame = Frame(
                    uid=self._frame_uid,
                    stream_id=stream.id,
                    sequence_number=sequence,
                    pcp=stream.pcp,
                    size_bytes=stream.size_bytes,
                    release_time_us=t,
                    route_link_ids=stream.route_link_ids,
                )
                self._frame_uid += 1
                self.generated_frames += 1
                self.event_queue.push(t, "release", frame)
                sequence += 1
                t = sequence * stream.period_us

    def per_stream_rows(self) -> List[dict]:
        by_stream: Dict[int, List[FrameRecord]] = defaultdict(list)
        for record in self.records:
            by_stream[record.stream_id].append(record)

        rows: List[dict] = []
        for stream_id in sorted(self.streams):
            stream = self.streams[stream_id]
            records = by_stream.get(stream_id, [])
            response_times = [record.response_time_us for record in records]
            rows.append(
                {
                    "stream_id": stream_id,
                    "name": stream.name,
                    "pcp": stream.pcp,
                    "class": {2: "A", 1: "B", 0: "BE"}[stream.pcp],
                    "size_bytes": stream.size_bytes,
                    "period_us": stream.period_us,
                    "deadline_us": "" if stream.deadline_us is None else stream.deadline_us,
                    "route_links": "->".join(stream.route_link_ids),
                    "frames_observed": len(records),
                    "min_rt_us": min(response_times) if response_times else "",
                    "avg_rt_us": sum(response_times) / len(response_times) if response_times else "",
                    "max_rt_us": max(response_times) if response_times else "",
                    "deadline_misses": sum(
                        1 for value in response_times if stream.deadline_us is not None and value > stream.deadline_us + EPS
                    ),
                }
            )
        return rows

    def per_port_rows(self, simulated_until_us: float) -> List[dict]:
        rows: List[dict] = []
        for link_id in sorted(self.ports):
            port = self.ports[link_id]
            rows.append(
                {
                    "link_id": link_id,
                    "source": port.link.source,
                    "source_port": port.link.source_port,
                    "destination": port.link.destination,
                    "bandwidth_mbps": port.link.bandwidth_mbps,
                    "utilization_busy_fraction": port.busy_time_us / simulated_until_us if simulated_until_us > 0 else 0.0,
                    "tx_pcp2": port.tx_count[2],
                    "tx_pcp1": port.tx_count[1],
                    "tx_pcp0": port.tx_count[0],
                    "max_q_pcp2": port.max_queue_len[2],
                    "max_q_pcp1": port.max_queue_len[1],
                    "max_q_pcp0": port.max_queue_len[0],
                    "final_credit_bits_pcp2": port.credit_bits[2],
                    "final_credit_bits_pcp1": port.credit_bits[1],
                }
            )
        return rows
