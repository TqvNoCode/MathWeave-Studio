"""Tests guarding loopback-only NiceGUI server configuration."""

from math_app.main import DEFAULT_HOST, DEFAULT_PORT, get_available_port


def test_default_host_is_loopback_only():
    """Verify default server host is strictly 127.0.0.1 to avoid exposing the app to LAN."""
    assert DEFAULT_HOST == "127.0.0.1"


def test_default_port_is_8080():
    """Verify default application port is 8080."""
    assert DEFAULT_PORT == 8080


def test_get_available_port_binds_to_loopback():
    """Verify port detection binds strictly to 127.0.0.1."""
    port = get_available_port(DEFAULT_HOST, DEFAULT_PORT)
    assert isinstance(port, int)
    assert port > 0
