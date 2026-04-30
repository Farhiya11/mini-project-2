"""Data models for the TSN/CBS simulator.

All internal times are microseconds. Stream sizes are payload bytes. Link
bandwidth is Mbps, which is numerically bits per microsecond, so a frame
serialization time is ``size_bytes * 8 / bandwidth_mbps`` microseconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

AVB_PCPS = (2, 1)
ALL_PCPS = (2, 1, 0)
EPS = 1e-9


@dataclass(frozen=True)
class Link:
    """A directed topology link and the output port that feeds it."""

    id: str
    source: str
    destination: str
    source_port: int
    destination_port: int
    delay_us: float
    bandwidth_mbps: float

    def serialization_time_us(self, size_bytes: int, l2_overhead_bytes: int = 0) -> float:
        """Return transmission time in microseconds.

        Mbps = 10^6 bits/s = bits/us, therefore bytes*8/Mbps gives us.
        """

        return ((size_bytes + l2_overhead_bytes) * 8.0) / self.bandwidth_mbps


@dataclass(frozen=True)
class Stream:
    id: int
    name: str
    source: str
    destination: str
    pcp: int
    size_bytes: int
    period_us: float
    deadline_us: Optional[float]
    route_link_ids: Tuple[str, ...]


@dataclass
class Frame:
    uid: int
    stream_id: int
    sequence_number: int
    pcp: int
    size_bytes: int
    release_time_us: float
    route_link_ids: Tuple[str, ...]
    hop_index: int = 0
    enqueue_time_us: float = 0.0

    @property
    def current_link_id(self) -> str:
        return self.route_link_ids[self.hop_index]

    @property
    def finished_route(self) -> bool:
        return self.hop_index >= len(self.route_link_ids)


@dataclass(frozen=True)
class FrameRecord:
    frame_uid: int
    stream_id: int
    sequence_number: int
    release_time_us: float
    arrival_time_us: float
    response_time_us: float
