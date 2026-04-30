"""Small event queue wrapper for deterministic event ordering."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import List, Tuple

from .models import EPS


@dataclass(order=True)
class Event:
    time_us: float
    sequence: int
    kind: str = field(compare=False)
    item: object = field(compare=False)


class EventQueue:
    def __init__(self) -> None:
        self._heap: List[Event] = []
        self._sequence = 0

    def push(self, time_us: float, kind: str, item: object) -> None:
        if time_us < -EPS:
            raise ValueError(f"Cannot schedule negative event time: {time_us}")
        heapq.heappush(self._heap, Event(float(time_us), self._sequence, kind, item))
        self._sequence += 1

    def pop_batch(self) -> Tuple[float, List[Event]]:
        if not self._heap:
            raise IndexError("pop from empty EventQueue")
        time_us = self._heap[0].time_us
        batch: List[Event] = []
        while self._heap and abs(self._heap[0].time_us - time_us) <= EPS:
            batch.append(heapq.heappop(self._heap))
        return time_us, batch

    def __bool__(self) -> bool:
        return bool(self._heap)
