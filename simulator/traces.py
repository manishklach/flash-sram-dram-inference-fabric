from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AccessEvent:
    step: int
    token_id: int
    layer_id: int
    object_id: str
    object_type: str
    size_bytes: int
    deadline_step: int
    is_critical: bool
    session_id: str = "session_0"
    op_type: str = "ATTENTION"


def iter_steps(events: Iterable[AccessEvent]) -> Iterable[AccessEvent]:
    for event in sorted(events, key=lambda item: item.step):
        yield event
