import base64
from nacl.public import Box, PrivateKey, PublicKey
from urllib.parse import urlencode
import requests
import time
import webbrowser
import json
import websockets

class AccessCLILogin:
    """
    Direct reimplementation of the cloudflared Access CLI login flow
    (reconstructed from token/transfer.go and token/encrypt.go).

    WARNING: Unofficial, undocumented protocol. Cloudflare can change it
    at any time without notice. Reconstructed from the state of
    cloudflared 'master' at the time of this research.
    """

    TRANSFER_BASE = "https://login.cloudflareaccess.org/"
    POLL_ATTEMPTS = 10
    POLL_TIMEOUT = 60  # seconds per long-poll attempt (matches cloudflared's clientTimeout)

    def __init__(self, app_url: str, audience_tag: str):
        self.app_url = app_url.rstrip("/")
        self.aud = audience_tag
        self._private_key = PrivateKey.generate()
        self._public_key_b64 = base64.urlsafe_b64encode(
            bytes(self._private_key.public_key)
        ).decode()

    def _build_login_url(self) -> str:
        base_params = {
            "token": self._public_key_b64,
            "aud": self.aud,
        }
        redirect_url = f"{self.app_url}?{urlencode(base_params)}"

        params = {
            **base_params,
            "redirect_url": redirect_url,
            "send_org_token": "true",
            "edge_token_transfer": "true",
        }
        return f"{self.app_url}/cdn-cgi/access/cli?{urlencode(params)}"

    def _poll_for_token(self) -> bytes:
        url = self.TRANSFER_BASE + "transfer/" + self._public_key_b64

        for attempt in range(1, self.POLL_ATTEMPTS + 1):
            print(f"[*] Waiting for login... (attempt {attempt}/{self.POLL_ATTEMPTS})")
            try:
                resp = requests.get(url, timeout=self.POLL_TIMEOUT)
            except requests.RequestException as e:
                print(f"[-] Poll request failed: {e}")
                time.sleep(2)
                continue

            if resp.status_code >= 500:
                raise RuntimeError(
                    f"Transfer service returned an error: HTTP {resp.status_code}"
                )

            if resp.status_code != 200:
                # Resource doesn't exist yet -> user hasn't finished the
                # login. Wait a bit and try again.
                time.sleep(1.5)
                continue

            server_pubkey_b64 = resp.headers.get("service-public-key")
            if not server_pubkey_b64:
                raise RuntimeError(
                    "Response was missing the 'service-public-key' header -- "
                    "the protocol has likely changed."
                )

            encrypted = base64.b64decode(resp.content)
            return self._decrypt(encrypted, server_pubkey_b64)

        raise TimeoutError(
            "Did not receive a token within the poll attempts. "
            "Was the login completed in the browser?"
        )

    def _decrypt(self, encrypted: bytes, server_pubkey_b64: str) -> bytes:
        # Our own key is transmitted as base64.URLEncoding; we assume the
        # server key is encoded the same way. If not, fall back to
        # standard base64.
        padded = server_pubkey_b64 + "=" * (-len(server_pubkey_b64) % 4)
        try:
            server_pubkey_raw = base64.urlsafe_b64decode(padded)
        except Exception:
            server_pubkey_raw = base64.b64decode(padded)

        box = Box(self._private_key, PublicKey(server_pubkey_raw))
        # Without an explicit nonce argument, PyNaCl expects: nonce (24 bytes)
        # directly in front of the ciphertext -- matches box.Seal(nonce[:], ...) in Go.
        return box.decrypt(encrypted)

    def login(self) -> dict:
        login_url = self._build_login_url()
        print(f"[*] Opening browser for login:\n{login_url}\n")
        if not webbrowser.open(login_url):
            print("[!] Browser could not be opened automatically, please open the URL manually.")

        raw = self._poll_for_token()

        try:
            data = json.loads(raw)
            print("[+] Decrypted payload (JSON):")
            print(json.dumps(data, indent=2))
            return data
        except json.JSONDecodeError:
            # If the format isn't (pure) JSON, print the raw data so you
            # can see the actual format and adjust the code accordingly.
            print("[!] Payload was not valid JSON, raw data:")
            print(raw)
            return {"raw": raw}
