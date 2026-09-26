import asyncio
from .AccessCLILogin import AccessCLILogin
import websockets
from ._UDPProxyProtocol import _UDPProxyProtocol
from .helpers import *


class CloudflaredClient:


    def __init__(
        self,
        url: str,
        socket_type: "ConnectionTypes",
        audience_tag: str,
        service_token_id: str = None,
        service_token_secret: str = None,
    ):
        self.url = url
        self.socket_type = socket_type
        self.audience_tag = audience_tag
        self.jwt_token = None

        self.service_token_id = service_token_id
        self.service_token_secret = service_token_secret


    def login(self) -> str:
        app_url = make_url(self.url, "https://")
        auth = AccessCLILogin(app_url, self.audience_tag)
        payload = auth.login()

        app_token = payload.get("app_token")
        if not app_token:
            raise RuntimeError(
                "Could not find 'app_token' in the decrypted payload. "
                "Take a look at the JSON output above."
            )
        self.jwt_token = app_token

        print("[+] JWT token successfully retrieved via the direct Access CLI flow!")
        return self.jwt_token

    def getHeader(self) -> dict:
        """
        Returns the auth headers.

        Priority: Service token (if specified during initialization) > interactive
        JWT from `login()` as a cookie.
        """
        if self.service_token_id and self.service_token_secret:
            return {
                "CF-Access-Client-Id": self.service_token_id,
                "CF-Access-Client-Secret": self.service_token_secret,
            }
        if self.jwt_token:
            return {"Cookie": f"CF_Authorization={self.jwt_token}"}
        return {}

    async def _handle_tcp_client(self, reader, writer):
        """
        Forwards the local TCP stream bidirectionally through the WebSocket tunnel.
        """
        print("[+] New TCP client connected, opening WebSocket tunnel...")

        target_url = make_url(self.url, "wss://")
        headers = self.getHeader()

        try:
            try:
                websocket_conn = websockets.connect(target_url, additional_headers=headers)
            except TypeError:
                websocket_conn = websockets.connect(target_url, extra_headers=headers)

            async with websocket_conn as websocket:
                print("[+] Tunnel connected! Starting piping...")

                async def tcp_to_ws():
                    try:
                        while True:
                            data = await reader.read(4096)
                            if not data:
                                break
                            await websocket.send(data)
                    except Exception:
                        pass
                    finally:
                        await websocket.close()

                async def ws_to_tcp():
                    try:
                        async for message in websocket:
                            if isinstance(message, str):
                                message = message.encode("utf-8")
                            writer.write(message)
                            await writer.drain()
                    except Exception:
                        pass
                    finally:
                        writer.close()

                t1 = asyncio.create_task(tcp_to_ws())
                t2 = asyncio.create_task(ws_to_tcp())
                await asyncio.gather(t1, t2)

        except Exception as e:
            print(f"[-] Error in tunnel: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            print("[-] TCP connection closed.")

    async def serve(self, host: str = "127.0.0.1", port: int = 2233):
        """
        Starts the listener for the configured connection type.

        Login (interactively via login(), or via a service token passed
        at construction time) must already be done beforehand -- serve()
        does not do this automatically anymore.

        Args:
            host: The host to bind to. Default is '127.0.0.1'.
            port: The port to bind to. Default is 2233.
        """
        if not self.getHeader():
            raise RuntimeError(
                "No auth header available. Either call client.login() "
                "beforehand, or pass service_token_id/service_token_secret "
                "at construction time."
            )

        if self.socket_type == ConnectionTypes.TCP:
            server = await asyncio.start_server(self._handle_tcp_client, host, port)
            print(f"[*] Cloudflared TCP proxy running on {host}:{port}")
            async with server:
                await server.serve_forever()
        elif self.socket_type == ConnectionTypes.UDP:
            loop = asyncio.get_running_loop()
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: _UDPProxyProtocol(self),
                local_addr=(host, port),
            )
            print(f"[*] Cloudflared UDP proxy running on {host}:{port}")
            try:
                await asyncio.Future()
            finally:
                transport.close()


