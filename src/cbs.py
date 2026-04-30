"""Credit-Based Shaper output-port model."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Optional

from .events import EventQueue
from .models import ALL_PCPS, AVB_PCPS, EPS, Frame, Link


class OutputPort:
    """One FIFO-per-PCP output port feeding one directed link.

    PCP 2 and PCP 1 are AVB/CBS queues. PCP 0 is best effort. Transmission
    selection is strict priority among eligible queues; AVB queues are eligible
    only when their credit is non-negative.
    """

    def __init__(
        self,
        link: Link,
        event_queue: EventQueue,
        idle_slope_fraction: Dict[int, float],
        l2_overhead_bytes: int = 0,
    ) -> None:
        self.link = link
        self.event_queue = event_queue
        self.l2_overhead_bytes = l2_overhead_bytes

        # Credit is in bits. Since Mbps = bits/us, slopes are bits/us.
        self.idle_slope_bits_per_us = {
            pcp: idle_slope_fraction[pcp] * link.bandwidth_mbps for pcp in AVB_PCPS
        }
        self.send_slope_bits_per_us = {
            pcp: self.idle_slope_bits_per_us[pcp] - link.bandwidth_mbps for pcp in AVB_PCPS
        }

        self.queues: Dict[int, Deque[Frame]] = {pcp: deque() for pcp in ALL_PCPS}
        self.credit_bits: Dict[int, float] = {pcp: 0.0 for pcp in AVB_PCPS}

        self.transmitting: Optional[Frame] = None
        self.transmitting_pcp: Optional[int] = None
        self.last_update_us = 0.0
        self._wake_token = 0

        self.busy_time_us = 0.0
        self.tx_count = {pcp: 0 for pcp in ALL_PCPS}
        self.max_queue_len = {pcp: 0 for pcp in ALL_PCPS}

    def enqueue(self, frame: Frame, now_us: float) -> None:
        self.update_credit(now_us)
        frame.enqueue_time_us = now_us
        self.queues[frame.pcp].append(frame)
        self.max_queue_len[frame.pcp] = max(self.max_queue_len[frame.pcp], len(self.queues[frame.pcp]))

    def update_credit(self, now_us: float) -> None:
        dt = now_us - self.last_update_us
        if dt < -EPS:
            raise ValueError(f"Time moved backwards on {self.link.id}: {now_us} < {self.last_update_us}")
        if dt <= EPS:
            self.last_update_us = now_us
            return

        for pcp in AVB_PCPS:
            queue_has_frames = bool(self.queues[pcp])
            if self.transmitting_pcp == pcp:
                self.credit_bits[pcp] += self.send_slope_bits_per_us[pcp] * dt
            elif queue_has_frames:
                self.credit_bits[pcp] += self.idle_slope_bits_per_us[pcp] * dt
            else:
                # No waiting frame. Negative credit recovers to zero; positive credit is reset.
                if self.credit_bits[pcp] < -EPS:
                    self.credit_bits[pcp] = min(
                        0.0, self.credit_bits[pcp] + self.idle_slope_bits_per_us[pcp] * dt
                    )
                else:
                    self.credit_bits[pcp] = 0.0
        self.last_update_us = now_us

    def try_start_transmission(self, now_us: float) -> None:
        self.update_credit(now_us)
        if self.transmitting is not None:
            return

        selected_pcp = self._select_eligible_pcp()
        if selected_pcp is None:
            self._schedule_credit_wakeup(now_us)
            return

        frame = self.queues[selected_pcp].popleft()
        self.transmitting = frame
        self.transmitting_pcp = selected_pcp
        tx_time_us = self.link.serialization_time_us(frame.size_bytes, self.l2_overhead_bytes)
        self.busy_time_us += tx_time_us
        self.tx_count[selected_pcp] += 1
        self.event_queue.push(now_us + tx_time_us, "tx_complete", self.link.id)

    def complete_transmission(self, now_us: float) -> Frame:
        self.update_credit(now_us)
        if self.transmitting is None:
            raise RuntimeError(f"Transmission completion on idle port {self.link.id}.")
        frame = self.transmitting
        self.transmitting = None
        self.transmitting_pcp = None
        self.update_credit(now_us)
        return frame

    def _select_eligible_pcp(self) -> Optional[int]:
        for pcp in ALL_PCPS:
            if not self.queues[pcp]:
                continue
            if pcp in AVB_PCPS and self.credit_bits[pcp] < -EPS:
                continue
            return pcp
        return None

    def _schedule_credit_wakeup(self, now_us: float) -> None:
        waits = []
        for pcp in AVB_PCPS:
            if self.queues[pcp] and self.credit_bits[pcp] < -EPS:
                waits.append((-self.credit_bits[pcp]) / self.idle_slope_bits_per_us[pcp])
        if waits:
            self._wake_token += 1
            self.event_queue.push(now_us + min(waits), "credit_wakeup", (self.link.id, self._wake_token))
