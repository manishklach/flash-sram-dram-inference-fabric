from dataclasses import dataclass
from typing import Any

from .interface_modes import InterfaceMode


@dataclass
class TraceGuidedStreamingPolicy:
    """Stub policy for future trace-guided streaming experiments."""

    interface_mode: InterfaceMode = InterfaceMode.STREAM_TO_SCRATCHPAD

    def plan(self, trace_event: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "TODO",
            "reason": "Implement trace-guided bundle scheduling",
            "interface_mode": self.interface_mode.value,
            "trace_event": trace_event,
        }
