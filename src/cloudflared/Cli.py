from cyclopts import App
from .CloudflaredClient import CloudflaredClient
import asyncio
from .helpers import *

app = App(version="0.1.0")

@app.default
def main(
    url: str,
    *,
    aud: str,
    host: str = "127.0.0.1",
    port: int = 2233,
    login: bool = False,
    service_token: str = None,
    service_secret: str = None,
    contype: ConnectionTypes = ConnectionTypes.TCP,
):
    """Cloudflare Access TCP/UDP Proxy Client"""
    print(f"[*] Starte für URL: {url}")
    print(f"[*] Host/Port: {host}:{port}")
    print(f"[*] Audience Tag: {aud}")
    print(f"[*] Interactiv Login: {login}")
    print(f"[*] Login Token: {service_token}")
    print(f"[*] Login Secret: {service_secret}")
    print(f"[*] Modus: {contype}")
    
    client = CloudflaredClient(
        url,
        contype,
        aud,
        service_token,
        service_secret
    )

    if login:
        client.login()
    try:
        asyncio.run(client.serve(host, port))
    except KeyboardInterrupt:
        print("\n[-] Proxy-Server Closed By User.")


def cli():
    app()

if __name__ == "__main__":
    app()
