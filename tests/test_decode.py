from pytest import raises
from pytest import mark
from io import BytesIO
from fault_harness.client import decode_reply, RedisError, ConnectionClosedError

def test_decode_simple_strings():
    assert decode_reply(BytesIO(b"+PONG\r\n")) == "PONG"

def test_decode_integers():
    assert decode_reply(BytesIO(b":42\r\n")) == 42

def test_decode_bulk_strings():
    assert decode_reply(BytesIO(b"$5\r\nHello\r\n")) == "Hello"

def test_decode_arrays():
    assert decode_reply(BytesIO(b"*2\r\n$5\r\nHello\r\n$5\r\nWorld\r\n")) == ["Hello", "World"]

def test_decode_null_bulk_strings():
    assert decode_reply(BytesIO(b"$-1\r\n")) is None

def test_decode_null_arrays():
    assert decode_reply(BytesIO(b"*-1\r\n")) is None

def test_decode_simple_errors():
    with raises(RedisError):
        decode_reply(BytesIO(b"-ERR nope\r\n"))

def test_decode_empty_strings():
    assert decode_reply(BytesIO(b"$0\r\n\r\n")) == ""

def test_decode_empty_arrays():
    assert decode_reply(BytesIO(b"*0\r\n")) == []

def test_decode_safe_string_length():
    assert decode_reply(BytesIO(b"$6\r\nte\r\nst\r\n")) == "te\r\nst"

def test_decode_non_ascii_using_byte_length():
    assert decode_reply(BytesIO(b"$5\r\nCaf\xc3\xa9\r\n")) == "Café"

def test_decode_nested_arrays():
    assert decode_reply(BytesIO(b"*1\r\n*2\r\n:1\r\n:2\r\n")) == [[1, 2]]

def test_decode_nested_multitype_arrays():
    assert decode_reply(BytesIO(b"*2\r\n*2\r\n$3\r\nabc\r\n:123\r\n*1\r\n$3\r\ncde\r\n")) == [["abc", 123], ["cde"]]

def test_decode_closed_connection():
    with raises(ConnectionClosedError):
        decode_reply(BytesIO(b""))

def test_decode_reject_resp3_reply_types():
    with raises(RedisError):
        decode_reply(BytesIO(b"%1\r\n"))

def test_decode_cursor_advancement():
    stream = BytesIO(b"$5\r\nHello\r\n:42\r\n")
    assert decode_reply(stream) == "Hello"
    assert decode_reply(stream) == 42

@mark.parametrize("raw", [b"$5\r\nhel", b"$5\r\nHello", b"$5\r\nHello\r"])
def test_decode_reject_truncated_reply(raw):
    with raises(ConnectionClosedError):
        decode_reply(BytesIO(raw))