from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
import websockets
from .helpers import make_url


if TYPE_CHECKING:
    from .CloudflaredClient import CloudflaredClient


class _UDPProxyProtocol(asyncio.DatagramProtocol):
    """
    Simple single-session UDP bridge: all incoming packets are piped into
    the same WebSocket tunnel, and responses are sent back to the most
    recently seen sender.

    WARNING: no multi-client multiplexing -- if multiple UDP peers send
    at the same time, they all end up in the same tunnel and responses
    only go to the last known address. Real multi-session UDP would need
    a separate tunnel per peer plus a session identifier.
    """
    def __init__(self, client: "CloudflaredClient"):
        self.client_ref = client
        self.transport = None
        self.client_addr = None
        self.websocket = None
        self._ws_lock = asyncio.Lock()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        self.client_addr = addr
        asyncio.create_task(self._forward_to_ws(data))

    async def _ensure_ws(self):
        if self.websocket is not None:
            return

        target_url = make_url(self.client_ref.url, "wss://")
        headers = self.client_ref.getHeader()

        try:
            ws_conn = websockets.connect(target_url, additional_headers=headers)
        except TypeError:
            ws_conn = websockets.connect(target_url, extra_headers=headers)

        self.websocket = await ws_conn
        print("[+] UDP<->WS tunnel established!")
        asyncio.create_task(self._ws_to_udp())

    async def _forward_to_ws(self, data: bytes):
        try:
            async with self._ws_lock:
                await self._ensure_ws()
            await self.websocket.send(data)
        except Exception as e:
            print(f"[-] Error sending into WS: {e}")

    async def _ws_to_udp(self):
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    message = message.encode("utf-8")
                if self.transport and self.client_addr:
                    self.transport.sendto(message, self.client_addr)
        except Exception as e:
            print(f"[-] Error in WS->UDP path: {e}")

    def error_received(self, exc):
        print(f"[-] UDP socket error: {exc}")

    def connection_lost(self, exc):
        print("[-] UDP socket closed.")
