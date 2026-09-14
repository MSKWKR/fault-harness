# fault-harness

A test harness for a Redis-backed fixed-window rate limiter, built on a
hand-rolled RESP2 client.

**The harness is the deliverable.** The rate limiter exists to be tested — it is
deliberately small, and deliberately contains the kinds of failure modes that
only show up when the infrastructure underneath it misbehaves.

## Quick start

```sh
uv sync
uv run pytest
```

Requires Docker — the fault tests create and destroy a container named
`fh-redis`. The suite manages that container's lifecycle itself, so nothing
needs to be running beforehand.

```sh
uv run pytest -m "not fault"    # skip the destructive tests
```

All tests run against Redis database 15 and flush it on setup, so the suite is
re-runnable and will not touch anything in db 0.

## Design decisions

### Failure policy: fail open on connection loss, propagate server errors

`allow()` catches `ConnectionClosedError` and returns `True`. It does **not**
catch `RedisError`, which propagates to the caller.

The asymmetry is intentional. A dropped connection is plausibly transient — a
restart, a blip — and a rate limiter is a protective control, not a feature, so
degrading open keeps the service up. `-OOM` is different: Redis is alive,
reachable, and structurally broken, and it will stay broken until a human
intervenes. Swallowing that would mean running with no rate limiting
indefinitely and no signal that it happened.

Both behaviours are asserted by tests, so the policy cannot be quietly widened
into `except Exception` later.

### `Client` is not thread-safe

One socket, and `command()` does `sendall` then `decode_reply` with no lock.
Two threads sharing a client will interleave and corrupt the stream. Use one
connection per thread — which is what the concurrency test does, and what most
Redis clients require anyway.

### Socket timeout defaults to 1 second

A rate limiter must never be the slowest thing in a request path. Against a
hung Redis the caller's latency is then bounded by a number this project
controls, not by how long the dependency stays unwell. `test_allow_fails_open_when_redis_hangs`
asserts that bound directly.

### Fixed window, not sliding

A fixed window admits up to 2× the limit across a boundary — the last requests
of one window and the first of the next. That is a known property of the
algorithm, accepted for its simplicity and its single-round-trip cost, not an
oversight.

### Atomicity via Lua

`allow()` runs `INCR` and a conditional `EXPIRE` inside a single `EVAL`.

The obvious implementation issues them as two commands, and a connection that
dies in between leaves a key with a count and no TTL — permanently locking out
that identity, since nothing ever expires the key and every subsequent request
increments past the limit. The harness found this bug by injecting a failure
between the two calls.

Moving both operations into one script eliminated the failure window rather
than handling it: Redis is single-threaded, and script effects propagate to the
AOF and to replicas wrapped in `MULTI`/`EXEC`, so no observer anywhere can see
the intermediate state.

### Threat model: Redis is trusted

Redis is assumed to be a healthy server on a private network. The client
therefore does not defend against a hostile or corrupted peer — there is no
ceiling on a declared bulk-string length, and a negative length other than `-1`
is not rejected before being passed to `read()`. These are reachable only from
a server that is broken or malicious, and are deliberately out of scope.

## What the harness demonstrates

| Fault | Injection | Asserted |
|---|---|---|
| Redis dies mid-operation | `docker kill` | `allow()` fails open |
| Redis restarts | kill, then restart | client reconnects lazily; limits enforced again |
| Redis refuses commands | `CONFIG SET maxmemory 1` | `RedisError` propagates rather than failing open |
| Redis hangs | `CLIENT PAUSE 2000` | fails open **within the socket timeout**, not when Redis recovers |

Two more tests carry most of the weight without touching the container:

- **Concurrency** — 50 threads, each with its own client and its own limiter
  instance, released simultaneously by a `threading.Barrier` against one shared
  counter. Exactly 3 are allowed. Against a non-atomic read-modify-write
  implementation, all 50 are.
- **Truncated replies** — a reply that ends mid-payload or mid-terminator must
  raise, not return a short string.

Every destructive fixture restores what it changed in teardown, including after
a failing assertion: `maxmemory` is reset, the container is brought back, and
the pause is waited out. A fault test that leaves shared state dirty breaks
every test after it, with a traceback pointing somewhere else entirely.

## Test layout

| File | Tests | Scope |
|---|---|---|
| `test_encode.py` | 6 | RESP2 command encoding, byte-length framing, type rejection |
| `test_decode.py` | 19 | All five reply types, nil/empty boundaries, nesting, truncation |
| `test_client.py` | 7 | Connection lifecycle, reconnection, error propagation |
| `test_limiter.py` | 12 | Window keys, limits, TTL behaviour, concurrency |
| `test_fault_injection.py` | 4 | Container kill, OOM, hang, recovery |

Destructive tests are marked `fault`. `--strict-markers` is enabled.

## CI

GitHub Actions runs the full suite on every push, including the fault tests —
the runner has Docker, and the harness creates its own container. On failure,
the workflow captures the Redis container log, the container list, and a JUnit
report, and uploads them as artifacts.