from pytest import raises
from pytest import fixture
from fault_harness.client import Client
from fault_harness.client import RedisError

@fixture
def client():
    c = Client().connect()
    c.command("SELECT", 15)
    c.command("FLUSHDB")
    yield c
    c.close()

def test_client_ping_returns_pong(client):
    assert client.command("PING") == "PONG"

def test_client_close_when_not_connected():
    c = Client()
    c.close()

def test_client_close_twice(client):
    client.close()
    client.close()
    assert client._sock is None

def test_client_close_release_connection():
    c = Client().connect()
    c.close()
    assert c._sock is None

def test_client_close_on_exit():
    with Client() as c:
        pass
    assert c._sock is None
    

def test_client_connect_live_client(client):
    old = client._sock
    client.connect()
    assert old.fileno() == -1

def test_client_server_error(client):
    client.command("SET", "K", "HELLO")
    with raises(RedisError):
        client.command("INCR", "K")