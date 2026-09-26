from enum import Enum

def make_url(url: str, start: str = "wss://") -> str:
    for prefix in ("https://", "wss://", "ws://", "http://"):
        if url.startswith(prefix):
            return url.replace(prefix, start, 1)
    return f"{start}{url}"


class ConnectionTypes(Enum):
    TCP = "tcp"
    UDP = "udp"