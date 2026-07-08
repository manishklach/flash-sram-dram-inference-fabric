from dataclasses import dataclass
from typing import Any

from .interface_modes import InterfaceMode


@dataclass
class TraceGuidedStreamingPolicy:
    """Minimal policy shell for trace-guided streaming experiments."""

    interface_mode: InterfaceMode = InterfaceMode.STREAM_TO_SCRATCHPAD
    lookahead_steps: int = 12

    def plan(self, trace_event: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "prefetch_if_within_lookahead",
            "reason": "Trace-guided lookahead scheduling",
            "interface_mode": self.interface_mode.value,
            "lookahead_steps": self.lookahead_steps,
            "trace_event": trace_event,
        }
