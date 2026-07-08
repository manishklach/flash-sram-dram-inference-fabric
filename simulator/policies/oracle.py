class OraclePolicy:
    def plan(self, current, future_window: list) -> list[str]:
        return [f.object_id for f in future_window]
