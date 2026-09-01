from fault_harness.limiter import RateLimiter

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