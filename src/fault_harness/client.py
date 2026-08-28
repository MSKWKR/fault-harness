from typing import BinaryIO

class RedisError(Exception):
    pass

class ConnectionClosedError(Exception):
    pass

def encode_command(*args: str | int) -> bytes:
    n = len(args)
    if n == 0:
        raise ValueError("No argument was given")
    message = [f"*{n}\r\n"]
    for a in args:
        if isinstance(a, (str, int)):
            message.append(f"${len(bytes(str(a), 'utf-8'))}\r\n{a}\r\n")
        else:
            raise TypeError(f"Invalid argument for encoding, expected str or int, got: {a}")
    return bytes("".join(message), "utf-8")


def decode_reply(stream: BinaryIO) -> str | int | list | None:
    d = stream.readline()
    if not d:
        raise ConnectionClosedError("Connection closed by peer")
    match d[0:1]:
        
        case b"+":
            return str(d[1:-2], encoding="utf-8")
        
        case b"$":
            ch = int(d[1:-2])
            if ch == -1:
                return None
            s = str(stream.read(ch), encoding="utf-8")
            stream.read(2)
            return s
        
        case b":":
            return int(d[1:-2])
        
        case b"*":
            args = int(d[1:-2])
            if args == -1:
                return None
            output = []
            for i in range(args):
                output.append(decode_reply(stream))
            return output
        
        case b"-":
            raise RedisError(f"{str(d[1:-2], encoding="utf-8")}")

        case _:
            raise RedisError(f"Unknown reply type: {d[0:1]!r}")