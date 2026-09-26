from unittest.mock import MagicMock, patch
import pytest
from . import AccessCLILogin, CloudflaredClient


def test_make_url():
    """Testet die URL-Präfix-Normalisierung."""
    client = CloudflaredClient(
        url="https://example.com",
        socket_type=CloudflaredClient.ConnectionTypes.TCP,
        audience_tag="dummy_aud",
    )
    
    assert client.make_url("https://test.de", "wss://") == "wss://test.de"
    assert client.make_url("http://test.de", "wss://") == "wss://test.de"
    assert client.make_url("wss://test.de", "wss://") == "wss://test.de"
    assert client.make_url("test.de", "wss://") == "wss://test.de"


def test_get_header_with_service_token():
    """Testet, ob Service Tokens bevorzugt als Header zurückgegeben werden."""
    client = CloudflaredClient(
        url="https://example.com",
        socket_type=CloudflaredClient.ConnectionTypes.TCP,
        audience_tag="dummy_aud",
        service_token_id="my-client-id",
        service_token_secret="my-client-secret",
    )
    
    headers = client.getHeader()
    assert headers == {
        "CF-Access-Client-Id": "my-client-id",
        "CF-Access-Client-Secret": "my-client-secret",
    }


def test_get_header_with_jwt():
    """Testet, ob das JWT-Token als Cookie übergeben wird, wenn kein Service Token da ist."""
    client = CloudflaredClient(
        url="https://example.com",
        socket_type=CloudflaredClient.ConnectionTypes.TCP,
        audience_tag="dummy_aud",
    )
    client.jwt_token = "mocked-jwt-token-123"
    
    headers = client.getHeader()
    assert headers == {"Cookie": "CF_Authorization=mocked-jwt-token-123"}


def test_build_login_url():
    """Testet den Aufbau der Login-URL für den Access CLI Flow."""
    login = AccessCLILogin("https://example.com", "test-audience-tag")
    url = login._build_login_url()
    
    assert "https://example.com/cdn-cgi/access/cli?" in url
    assert "aud=test-audience-tag" in url
    assert "token=" in url
    assert "redirect_url=" in url


@patch("webbrowser.open", return_value=True)
@patch("requests.get")
def test_access_cli_login_success(mock_requests_get, mock_webbrowser):
    """Simuliert einen erfolgreichen Login-Polling-Vorgang und das Entschlüsseln."""
    # Mock den Response der Polling-Schnittstelle
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"service-public-key": "A" * 44}  # Basis64 key dummy
    # Da das echte Entschlüsseln echte NaCl-Schlüsselpaare erfordert,
    # mocken wir hier _decrypt direkt ab, um den JSON-Parse-Teil zu testen.
    mock_response.content = b'encrypted-data'
    
    mock_requests_get.return_value = mock_response

    login = AccessCLILogin("https://example.com", "test-audience-tag")
    
    # Wir patchen die _decrypt Methode, da echte NaCl-Pakete hier fehlschlagen würden
    with patch.object(login, "_decrypt", return_value=b'{"app_token": "secret-jwt-123"}'):
        data = login.login()
        
        assert data == {"app_token": "secret-jwt-123"}
        mock_webbrowser.assert_called_once()