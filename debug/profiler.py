"""Bounded rolling frame profiler with JSON export."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import json, math, time
from pathlib import Path

@dataclass(frozen=True, slots=True)
class FrameSpike:
    frame: int
    milliseconds: float
    context: str

class DebugProfiler:
    def __init__(self, window: int = 120) -> None:
        self.window = max(10, window); self.samples: dict[str, deque[float]] = {}; self.spikes: deque[FrameSpike] = deque(maxlen=20); self.frame = 0
    def record(self, name: str, milliseconds: float, context: str = "") -> None:
        self.samples.setdefault(name, deque(maxlen=self.window)).append(max(0.0, float(milliseconds)))
        if name == "frame":
            self.frame += 1
            if milliseconds > 16.67: self.spikes.append(FrameSpike(self.frame, milliseconds, context))
    def summary(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, values in self.samples.items():
            ordered = sorted(values); count = len(ordered)
            result[name] = {"current": round(ordered[-1] if values else 0, 3), "mean": round(sum(values)/count, 3) if count else 0, "p95": round(ordered[min(count-1, math.ceil(count*.95)-1)], 3) if count else 0, "max": round(ordered[-1], 3) if count else 0}
        result["spike_counts"] = {"16.67": sum(x.milliseconds > 16.67 for x in self.spikes), "25": sum(x.milliseconds > 25 for x in self.spikes), "33.3": sum(x.milliseconds > 33.3 for x in self.spikes)}
        result["last_spike"] = None if not self.spikes else {"frame": self.spikes[-1].frame, "milliseconds": round(self.spikes[-1].milliseconds, 3), "context": self.spikes[-1].context}
        return result
    def export(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True); stamp=time.strftime("%Y%m%d_%H%M%S"); path=root/f"perf_{stamp}_{time.time_ns()%1_000_000:06d}.json"
        path.write_text(json.dumps(self.summary(), indent=2, sort_keys=True)+"\n", encoding="utf-8"); return path
