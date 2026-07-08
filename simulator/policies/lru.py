from ..traces import AccessEvent


class LRUPolicy:
    def __init__(self, history_size: int = 256):
        self.history: list[str] = []
        self.history_size = history_size

    def record_access(self, object_id: str) -> None:
        self.history.append(object_id)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def plan(self, current: AccessEvent, future_window: list[AccessEvent]) -> list[str]:
        candidates = set(f.object_id for f in future_window)
        recent = set(self.history[-self.history_size:])
        return [oid for oid in candidates if oid in recent]
