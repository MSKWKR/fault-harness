import time
from fault_harness.client import Client
from fault_harness.client import ConnectionClosedError

class RateLimiter:
    def __init__(self, client: Client, limit: int = 5, window_seconds: int = 60, clock=time.time, prefix: str = "rl"):
        self.client = client
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.prefix = prefix

    def _window_key(self, identity: str) -> str:
        t = int(self.clock() // self.window_seconds)
        return f"{self.prefix}:{identity}:{t}"

    def allow(self, identity: str) -> bool:
        key = self._window_key(identity)
        try:
            count = self.client.command("INCR", key)
            if count == 1:
                self.client.command("EXPIRE", key, self.window_seconds)
        except ConnectionClosedError:
            return True
        return count <= self.limit