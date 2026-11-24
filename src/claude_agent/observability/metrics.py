"""Latency histograms, counters and process-tree resource sampling."""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque

import psutil


class Latency:
    def __init__(self, keep: int = 500):
        self.samples: dict[str, deque] = defaultdict(lambda: deque(maxlen=keep))

    def record(self, name: str, ms: float) -> None:
        self.samples[name].append(ms)

    def pct(self, name: str, p: float) -> float | None:
        s = sorted(self.samples.get(name, ()))
        if not s:
            return None
        k = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
        return round(s[k], 1)

    def report(self) -> dict:
        return {n: {"n": len(v), "p50": self.pct(n, 50), "p95": self.pct(n, 95)} for n, v in self.samples.items()}


class Counters(defaultdict):
    def __init__(self):
        super().__init__(int)

    def inc(self, name: str, n: int = 1) -> None:
        self[name] += n


def process_tree_usage(pid: int | None = None) -> dict:
    """RAM/CPU for this process and all children (includes the dedicated Chrome)."""
    try:
        me = psutil.Process(pid or os.getpid())
        procs = [me] + me.children(recursive=True)
    except psutil.Error:
        return {}
    rss = 0
    cpu = 0.0
    for p in procs:
        try:
            rss += p.memory_info().rss
            cpu += p.cpu_percent(interval=None)
        except psutil.Error:
            continue
    vm = psutil.virtual_memory()
    return {"processes": len(procs), "rss_mb": round(rss / 2**20, 1), "cpu_percent": round(cpu, 1),
            "system_available_mb": round(vm.available / 2**20), "system_total_mb": round(vm.total / 2**20),
            "system_cpu_percent": psutil.cpu_percent(interval=None), "ts": time.time()}


latency = Latency()
counters = Counters()
