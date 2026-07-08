from ..traces import AccessEvent


class NoPrefetchPolicy:
    def plan(self, current: AccessEvent, future_window: list[AccessEvent]) -> list[str]:
        return []
