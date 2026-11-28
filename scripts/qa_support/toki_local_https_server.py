#!/usr/bin/env python3
"""Shared local HTTPS server for static-site browser QA.

The production pages enforce upgrade-insecure-requests. Serving them over HTTP
causes WebKit to upgrade same-origin CSS/JS URLs to HTTPS, which an HTTP-only
test server cannot satisfy. This helper gives Playwright a self-signed local
HTTPS origin; test contexts should set ignore_https_errors=True.
"""
from __future__ import annotations

import ssl
import subprocess
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Callable


def start_https_server(
    handler: type[SimpleHTTPRequestHandler] | Callable,
) -> tuple[ThreadingHTTPServer, Thread, tempfile.TemporaryDirectory, str]:
    certificate_dir = tempfile.TemporaryDirectory(prefix="toki-qa-tls-")
    cert_path = Path(certificate_dir.name) / "localhost-cert.pem"
    key_path = Path(certificate_dir.name) / "localhost-key.pem"

    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key_path),
            "-out", str(cert_path),
            "-days", "1",
            "-subj", "/CN=127.0.0.1",
            "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"https://127.0.0.1:{server.server_port}"
    return server, thread, certificate_dir, base_url
