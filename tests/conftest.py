import subprocess
import time
from pytest import fixture
from fault_harness.client import Client
from fault_harness.client import ConnectionClosedError
from fault_harness.limiter import RateLimiter

class FakeClock:
    def __init__(self, t: float):
        self.t = t

    def __call__(self):
        return self.t

class RedisControl:
    def kill(self, timeout: float = 10.0):
        subprocess.run(['docker', 'kill', 'fh-redis'], capture_output=True, check=False)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            p = subprocess.run(['docker', 'ps', '-aq', '-f', 'name=fh-redis'], capture_output=True, text=True, check=True)
            if not p.stdout:
                return
            time.sleep(0.05)
        raise RuntimeError(f"Redis not ready after {timeout}s")

    def start(self, timeout: float = 10.0):
        subprocess.run(['docker', 'run', '-d', '--rm', '--name', 'fh-redis', '-p', '6379:6379', 'redis:7-alpine'], capture_output=True, check=True)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                Client().command("PING")
                return
            except ConnectionClosedError:
                time.sleep(0.05)
        raise RuntimeError(f"Redis not ready after {timeout}s")


    def ensure_running(self):
        p = subprocess.run(['docker', 'ps', '-q', '-f', 'name=fh-redis'], capture_output=True, text=True, check=True)
        if not p.stdout:
            self.start()

@fixture
def client(redis_control):
    c = Client(db=15).connect()
    c.command("FLUSHDB")
    yield c
    c.close()

@fixture
def limiter(client):
    return RateLimiter(client=client, limit=3, window_seconds=60, clock=FakeClock(70.0))

@fixture
def redis_control():
    ctl = RedisControl()
    ctl.ensure_running()
    yield ctl
    ctl.ensure_running()

@fixture
def redis_out_of_memory(client):
    client.command("CONFIG", "SET", "maxmemory-policy", "noeviction")
    client.command("CONFIG", "SET", "maxmemory", 1)
    yield
    client.command("CONFIG", "SET", "maxmemory", 0)