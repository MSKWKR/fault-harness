from pytest import fixture
from fault_harness.client import Client
from fault_harness.limiter import RateLimiter

class FakeClock:
    def __init__(self, t: float):
        self.t = t

    def __call__(self):
        return self.t

@fixture
def client():
    c = Client().connect()
    c.command("SELECT", 15)
    c.command("FLUSHDB")
    yield c
    c.close()

@fixture
def limiter(client):
    return RateLimiter(client=client, limit=3, window_seconds=60, clock=FakeClock(70.0))
