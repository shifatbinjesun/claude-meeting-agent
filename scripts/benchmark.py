"""Offline micro-benchmarks (no network, no AI calls). Usage: python scripts/benchmark.py"""
import json
import os
import platform
import statistics
import tempfile
import time

os.environ.setdefault("CLAUDE_AGENT_HOME", tempfile.mkdtemp())

from claude_agent.audio import pcm  # noqa: E402
from claude_agent.audio.vad import EnergyVAD  # noqa: E402
from claude_agent.memory.db import Brain, Scope  # noqa: E402
from claude_agent.brain.arbiter import TurnArbiter  # noqa: E402
from claude_agent.authority.policy import ActionProposal, Channel, Policy  # noqa: E402


def timeit(fn, n):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return {"p50_ms": round(statistics.median(ts), 3), "p95_ms": round(sorted(ts)[int(0.95 * (n - 1))], 3), "n": n}


res = {"python": platform.python_version(), "machine": platform.machine(), "processor": platform.processor()}
sec = pcm.tone(300, 1.0, 16000, 0.2)
v = EnergyVAD()
res["vad_per_1s_audio"] = timeit(lambda: v.feed(sec), 200)
out24 = pcm.tone(300, 1.0, 24000, 0.2)
res["resample_24k_to_16k_per_1s"] = timeit(lambda: pcm.resample(out24, 24000, 16000), 200)
chunk = pcm.tone(300, 0.128, 16000)
res["envelope_per_128ms_chunk"] = timeit(lambda: pcm.envelope(chunk, 12), 500)

d = tempfile.mkdtemp()
b = Brain(os.path.join(d, "bench.sqlite3"))
words = "meeting project deadline course pricing python deploy latency quota রিফাত ক্লাস আড্ডা বাজেট".split()
t0 = time.perf_counter()
for i in range(10000):
    b.remember("public" if i % 2 else "owner_private", " ".join(words[(i + k) % len(words)] for k in range(12)) + f" item{i}",
               title=f"note {i}")
res["memory_insert_10k_s"] = round(time.perf_counter() - t0, 2)
res["memory_search_10k_public"] = timeit(lambda: b.search("deadline pricing", Scope("public")), 200)
res["memory_search_10k_bangla"] = timeit(lambda: b.search("ক্লাস বাজেট", Scope("owner")), 200)
res["db_size_mb_10k"] = round(os.path.getsize(os.path.join(d, "bench.sqlite3")) / 2**20, 2)

a = TurnArbiter()
res["arbiter_heard_plus_decide"] = timeit(lambda: (a.heard("এই Claumeet, এইটা কী বলতো?"), a.decide()), 2000)
pol = Policy()
res["policy_decide"] = timeit(lambda: pol.decide(ActionProposal("speak", Channel.MODEL, payload={"t": time.time()})), 2000)
print(json.dumps(res, indent=2, ensure_ascii=False))
