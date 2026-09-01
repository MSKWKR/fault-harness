from pytest import fixture
from fault_harness.client import Client

@fixture
def client():
    c = Client().connect()
    c.command("SELECT", 15)
    c.command("FLUSHDB")
    yield c
    c.close()
