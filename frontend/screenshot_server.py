#!/usr/bin/env python3
"""
Static frontend server with an extra /__delay endpoint.

Purpose:
- Enable reproducible headless screenshots where the page needs time to autostart
  a stream and render feed rows/alerts before Chrome captures the screenshot.

Usage:
  python3 frontend/screenshot_server.py --port 8090

Then open:
  http://127.0.0.1:8090/index.html?autostart=1&mode=real&speedMs=500&delayMs=8000
"""

from __future__ import annotations

import argparse
import time
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ONE_BY_ONE_GIF = (
    b"GIF89a"
    b"\x01\x00\x01\x00"  # width=1, height=1
    b"\x80"  # GCT follows for 2 colors
    b"\x00"
    b"\x00"
    b"\x00\x00\x00"  # black
    b"\xff\xff\xff"  # white
    b"!\xf9\x04\x01\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/__delay":
            qs = parse_qs(parsed.query or "")
            ms_str = (qs.get("ms") or ["0"])[0]
            try:
                ms = int(ms_str)
            except ValueError:
                ms = 0

            if ms > 0:
                time.sleep(min(ms, 60000) / 1000.0)

            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(ONE_BY_ONE_GIF)))
            self.end_headers()
            self.wfile.write(ONE_BY_ONE_GIF)
            return

        super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    frontend_dir = Path(__file__).resolve().parent
    # Serve frontend/ as the web root so relative assets resolve.
    handler = functools.partial(Handler, directory=str(frontend_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving {frontend_dir} on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
