"""Deterministic queue laboratory. Offline: no sockets, URLs or traffic.

One worker spends service_ticks waiting for a simulated dependency.
Ticks represent model time, not elapsed wall time or CPU utilization.
"""
from collections import deque
from dataclasses import dataclass
from math import ceil

TICKS_PER_SECOND = 100


@dataclass(frozen=True)
class Config:
    name: str
    arrival_rate: int = 30
    workers: int = 4
    service_ticks: int = 20
    queue_limit: int = 100_000
    admission_rate: int | None = None
    deadline_ticks: int | None = None

    def __post_init__(self):
        if min(self.arrival_rate, self.workers, self.service_ticks) <= 0:
            raise ValueError('Rates, workers and service time must be positive')
        if self.queue_limit < 0:
            raise ValueError('Queue limit cannot be negative')
        if self.admission_rate is not None and self.admission_rate <= 0:
            raise ValueError('Admission rate must be positive')


CASES = [
    Config('NORMAL', arrival_rate=10),
    Config('OVERLOAD'),
    Config('BOUNDED', queue_limit=10, deadline_ticks=100),
    Config('LIMITED', queue_limit=10, admission_rate=18, deadline_ticks=100),
]


class QueueLab:
    def __init__(self, config: Config):
        self.config = config
        self.tick = 0
        self.queue = deque()  # creation ticks, FIFO
        self.active = []      # pairs: completion tick, creation tick
        self.generated = 0
        self.rejected = 0
        self.expired = 0
        self.completed = 0
        self.response_ticks = []
        self.arrival_credit = 0
        self.tokens = 1.0     # burst capacity is exactly one task

    def step(self):
        self.tick += 1
        cfg = self.config

        # 1. Complete work before admitting new tasks at the same tick.
        pending = []
        for finish, born in self.active:
            if finish <= self.tick:
                self.completed += 1
                self.response_ticks.append(self.tick - born)
            else:
                pending.append((finish, born))
        self.active = pending

        # 2. Expire only queued tasks. Running tasks are not cancelled.
        if cfg.deadline_ticks is not None:
            while self.queue and self.tick - self.queue[0] >= cfg.deadline_ticks:
                self.queue.popleft()
                self.expired += 1

        # 3. Token bucket is refilled using MODEL time.
        if cfg.admission_rate is not None:
            self.tokens = min(1.0, self.tokens + cfg.admission_rate / TICKS_PER_SECOND)

        # Integer credit generates exactly rate * seconds arrivals.
        self.arrival_credit += cfg.arrival_rate
        while self.arrival_credit >= TICKS_PER_SECOND:
            self.arrival_credit -= TICKS_PER_SECOND
            self.generated += 1
            if cfg.admission_rate is not None:
                if self.tokens < 1.0 - 1e-9:
                    self.rejected += 1
                    continue
                self.tokens -= 1.0
            if len(self.queue) >= cfg.queue_limit:
                self.rejected += 1
                continue
            self.queue.append(self.tick)

        # 4. At most four jobs may wait on the simulated dependency.
        while self.queue and len(self.active) < cfg.workers:
            born = self.queue.popleft()
            self.active.append((self.tick + cfg.service_ticks, born))
        self.assert_accounting()

    def assert_accounting(self):
        accounted = (self.completed + self.rejected + self.expired
                     + len(self.queue) + len(self.active))
        assert self.generated == accounted, 'A task was lost or counted twice'
        assert len(self.active) <= self.config.workers
        assert len(self.queue) <= self.config.queue_limit

    def snapshot(self):
        values = sorted(self.response_ticks)
        p95 = values[max(0, ceil(.95 * len(values)) - 1)] if values else 0
        return dict(time=self.tick / TICKS_PER_SECOND,
                    generated=self.generated, completed=self.completed,
                    rejected=self.rejected, expired=self.expired,
                    queued=len(self.queue), active=len(self.active),
                    p95_ms=p95 * 1000 / TICKS_PER_SECOND)


def run_case(config, seconds=30):
    lab = QueueLab(config)
    trace = [lab.snapshot()]
    for _ in range(round(seconds * TICKS_PER_SECOND)):
        lab.step()
        if lab.tick % 10 == 0:
            trace.append(lab.snapshot())
    return trace


if __name__ == '__main__':
    import json
    for case in CASES:
        print(case.name, json.dumps(run_case(case)[-1]))
