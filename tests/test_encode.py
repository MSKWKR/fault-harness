from pytest import raises
from fault_harness.client import encode_command

def test_encode_single_argument_command():
    assert encode_command("PING") == b"*1\r\n$4\r\nPING\r\n"

def test_encode_multiple_arguments():
    assert encode_command("EXPIRE", "K", 60) == b"*3\r\n$6\r\nEXPIRE\r\n$1\r\nK\r\n$2\r\n60\r\n"

def test_encode_non_ascii_using_byte_length():
    assert encode_command("SET", "Café") == b"*2\r\n$3\r\nSET\r\n$5\r\nCaf\xc3\xa9\r\n"

def test_encode_zero_argument():
    with raises(ValueError):
        encode_command()

def test_encode_empty_argument():
    assert encode_command("SET", "K", "") == b"*3\r\n$3\r\nSET\r\n$1\r\nK\r\n$0\r\n\r\n"

def test_encode_rejects_unsupported_argument_type():
    with raises(TypeError):
        encode_command("SET", "K", None)