
# Cloudflare Access TCP/UDP Proxy Client

An unofficial Python client that mimics the authentication and tunneling flow of Cloudflare Access (inspired by the official `cloudflared` CLI). The package allows you to reach protected endpoints locally via a TCP or UDP proxy by automating the browser-based login flow and tunneling the connection over WebSockets.

## ⚠️ Warning

This is an unofficial and undocumented protocol. Cloudflare may change this flow at any time without notice. Use at your own risk.

## Features

* **Automated Login:** Emulates the Cloudflare Access CLI OAuth/token transfer flow (including cryptographic decryption via `PyNaCl`).
* **TCP & UDP Tunneling:** Seamlessly routes local TCP connections or UDP packets through a WebSocket tunnel (`wss://`).
* **Service Token Support:** Optional support for hardcoded Cloudflare Access service tokens (`service_token` / `service_secret`) to bypass the interactive browser login.
* **Modern CLI:** Built with `cyclopts` for a clean, type-safe command-line interface.

## Installation

You can install the package locally in editable mode from your project directory:

```bash
pip install -e .

```

This will automatically install all required dependencies (`pynacl`, `requests`, `websockets`, `cyclopts`) and register the `pycloudflared` command in your terminal.

## Usage

Once installed, you can use the `pycloudflared` command directly from anywhere in your terminal:

```bash
pycloudflared <url> --aud <you-aud-token> --login --contype <connection type tcp/udp>

```

### CLI Arguments & Options

* `url` (Position-Argument): The target Cloudflare Access app URL.
* `--aud` (Required): The Audience Tag (AUD) of your Cloudflare Application.
* `--host` (Optional): The local host to bind to (default: `127.0.0.1`).
* `--port` (Optional): The local port to bind to (default: `2233`).
* `--login` (Flag): Triggers the interactive browser-based login flow.
* `--service-token` / `--service-secret` (Optional): Alternative authentication via Cloudflare Access Service Tokens.
* `--contype` (Optional): The connection type, either `tcp` or `udp` (default: `tcp`).

You can view the built-in help at any time using:

```bash
pycloudflared --help

```

## License

This project is licensed under the [MIT License](LICENSE).
