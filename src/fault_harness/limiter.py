import time
from fault_harness.client import Client
from fault_harness.client import ConnectionClosedError

class RateLimiter:
    _SCRIPT = """
        local c = redis.call('INCR', KEYS[1])
        if c == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return c
        """

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
        try:
            count = self.client.command("EVAL", self._SCRIPT, 1, self._window_key(identity), self.window_seconds)
        except ConnectionClosedError:
            return True
        return count <= self.limit