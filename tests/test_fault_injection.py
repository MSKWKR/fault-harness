import pytest
import time
from fault_harness.client import ConnectionClosedError
from fault_harness.client import RedisError

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
def test_allow_propagate_server_errors(limiter, redis_out_of_memory):
    with pytest.raises(RedisError):
        limiter.allow("bob")

@pytest.mark.fault
def test_allow_fails_open_when_redis_hangs(limiter, redis_paused):
    start = time.monotonic()
    result = limiter.allow("bob")
    elapsed = time.monotonic() - start
    assert result is True
    assert 1.0 <= elapsed < 1.5