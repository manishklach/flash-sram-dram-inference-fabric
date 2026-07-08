def _extract_block_id(object_id: str) -> int | None:
    marker = ".block_"
    if marker not in object_id:
        return None
    suffix = object_id.split(marker, maxsplit=1)[1]
    try:
        return int(suffix)
    except ValueError:
        return None


class FixedWindowPrefetchPolicy:
    def __init__(self, lookahead_steps: int = 12, locality_threshold: int = 4):
        self.lookahead_steps = lookahead_steps
        self.locality_threshold = locality_threshold

    def plan(self, current, future_window: list) -> list[str]:
        results: list[str] = []
        current_block = _extract_block_id(current.object_id)
        for future in future_window:
            if current_block is None:
                continue
            future_block = _extract_block_id(future.object_id)
            if future_block is None:
                continue
            if abs(future_block - current_block) <= self.locality_threshold:
                results.append(future.object_id)
        return results
