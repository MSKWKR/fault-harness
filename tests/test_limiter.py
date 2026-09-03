from fault_harness.limiter import RateLimiter
from fault_harness.client import Client

def test_same_window_same_key():
    a = RateLimiter(client=None, window_seconds=60, clock=lambda: 70.0)
    b = RateLimiter(client=None, window_seconds=60, clock=lambda: 110.0)
    assert a._window_key("bob") == "rl:bob:1"
    assert b._window_key("bob") == "rl:bob:1"

def test_diff_window_diff_key():
    a = RateLimiter(client=None, window_seconds=60, clock=lambda: 70.0)
    b = RateLimiter(client=None, window_seconds=60, clock=lambda: 130.0)
    assert a._window_key("bob") == "rl:bob:1"
    assert b._window_key("bob") == "rl:bob:2"

def test_diff_user_diff_key():
    a = RateLimiter(client=None, window_seconds=60, clock=lambda: 70.0)
    assert a._window_key("bob") == "rl:bob:1"
    assert a._window_key("alice") == "rl:alice:1"

def test_exact_window_boundary():
    a = RateLimiter(client=None, window_seconds=60, clock=lambda: 59.9)
    b = RateLimiter(client=None, window_seconds=60, clock=lambda: 60.0)
    assert a._window_key("bob") == "rl:bob:0"
    assert b._window_key("bob") == "rl:bob:1"

def test_allow_under_limit(limiter):
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert limiter.allow("bob")

def test_allow_over_limit(limiter):
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert not limiter.allow("bob")

def test_allow_reset_counter(limiter):
    limiter.clock.t = 59.9
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert not limiter.allow("bob")
    limiter.clock.t = 60.0
    assert limiter.allow("bob")
    

def test_allow_diff_user(limiter):
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert limiter.allow("bob")
    assert not limiter.allow("bob")
    assert limiter.allow("alice")

def test_allow_ttl_key(limiter, client):
    limiter.allow("bob")
    key = limiter._window_key("bob")
    assert client.command("TTL", key) > 0

def test_allow_window_is_fixed(limiter, client):
    limiter.allow("bob")
    key = limiter._window_key("bob")
    client.command("EXPIRE", key, 10)
    limiter.allow("bob")
    assert 0 < client.command("TTL", key) <= 10

def test_allow_when_redis_down():
    c = Client(port=6378)
    r = RateLimiter(client=c)
    assert r.allow("bob")