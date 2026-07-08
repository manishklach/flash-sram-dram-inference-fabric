class PredictivePolicy:
    def __init__(self, lookahead_steps: int = 12):
        self.lookahead_steps = lookahead_steps

    def plan(self, current, future_window: list) -> list[str]:
        scored: list[tuple[str, float]] = []
        for future in future_window:
            score = self._score(current, future)
            if score > 0:
                scored.append((future.object_id, score))
        scored.sort(key=lambda x: -x[1])
        return [oid for oid, _ in scored]

    def _score(self, current, future) -> float:
        return 1.0 / max(1, future.step - current.step)
