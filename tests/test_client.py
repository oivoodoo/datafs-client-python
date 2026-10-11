import json
import sys
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datafs import Client, DatafsError, ServerEvent


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/v1/sites/site-1/timeseries":
            self.send_response(404)
            self.end_headers()
            return
        query = parse_qs(parsed.query)
        assert query["from"] == ["2026-09-12"]
        assert self.headers["Authorization"] == "Bearer secret"
        body = json.dumps(
            {
                "from": "2026-09-12",
                "to": "2026-10-11",
                "interval": "day",
                "totals": {"visitors": 1, "pageviews": 2, "visits": 1, "bounce_rate": 0, "visit_duration_seconds": 0},
                "points": [],
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        assert json.loads(raw)["name"] == "signup"
        body = b'{"error":"bad_range","message":"from > to"}'
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class ClientTest(unittest.TestCase):
    def test_timeseries_and_error(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = Client(f"http://127.0.0.1:{server.server_address[1]}", "secret")
            series = client.timeseries("site-1", "2026-09-12", "2026-10-11")
            self.assertEqual(series.totals["visitors"], 1)
            with self.assertRaises(DatafsError) as caught:
                client.server_event(ServerEvent(domain="example.com", name="signup"))
            self.assertEqual(caught.exception.code, "bad_range")
            self.assertEqual(caught.exception.status, 400)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
