#!/usr/bin/env python3
"""Serve the packaged TOKI site over HTTPS for Lighthouse CI.

The production CSP intentionally upgrades insecure requests. Lighthouse must
therefore audit the built site over HTTPS too, rather than the HTTP-only
temporary server used by Lighthouse CI's staticDistDir mode.
"""
from __future__ import annotations

import os
import ssl
import subprocess
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "dist"
HOST = "127.0.0.1"
PORT = int(os.getenv("TOKI_LHCI_PORT", "8443"))


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Packaged site directory is missing: {SITE}")

    with tempfile.TemporaryDirectory(prefix="toki-lhci-tls-") as temporary:
        cert_path = Path(temporary) / "localhost-cert.pem"
        key_path = Path(temporary) / "localhost-key.pem"
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-days", "1",
                "-subj", f"/CN={HOST}",
                "-addext", f"subjectAltName=IP:{HOST},DNS:localhost",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        server = ThreadingHTTPServer((HOST, PORT), QuietHandler)
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
        tls_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        server.socket = tls_context.wrap_socket(server.socket, server_side=True)
        print(f"TOKI_LHCI_SERVER_READY https://{HOST}:{PORT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
