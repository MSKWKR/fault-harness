import pytest
from fault_harness.client import ConnectionClosedError

class FailAfter:
    def __init__(self, client, n):
        self.client, self.n, self.calls = client, n, 0

    def command(self, *args: str):
        self.calls += 1
        if self.calls > self.n:
            raise ConnectionClosedError("Injected failure")
        return self.client.command(*args)

@pytest.mark.fault
def test_limiter_when_redis_dies(limiter, redis_control):
    assert limiter.allow("bob")
    redis_control.kill()
    assert limiter.allow("bob")

@pytest.mark.fault
def test_limiter_recovers(limiter, redis_control, client):
    assert limiter.allow("bob")
    redis_control.kill()
    with pytest.raises(ConnectionClosedError):
        client.command("PING")
    redis_control.ensure_running()
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert not limiter.allow("bob")
    
@pytest.mark.fault
def test_fail_between_INCR_EXPIRE(limiter, client):
    limiter.client = FailAfter(client, 1)
    limiter.allow("bob")
    key = limiter._window_key("bob")
    assert client.command("TTL", key) == -2