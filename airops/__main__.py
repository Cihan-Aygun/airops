import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .engine import schedule, recover


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenario":
            try:
                params = parse_qs(parsed.query)
                result = recover(schedule(), params.get("flight", ["AO001"])[0],
                                 int(params.get("delay", ["90"])[0]))
                payload = json.dumps(result).encode()
                status, mime = 200, "application/json"
            except (ValueError, TypeError) as exc:
                payload = json.dumps({"error": str(exc)}).encode()
                status, mime = 400, "application/json"
        elif parsed.path == "/":
            payload = Path(__file__).with_name("dashboard.html").read_bytes()
            status, mime = 200, "text/html; charset=utf-8"
        else:
            payload, status, mime = b"Not found", 404, "text/plain"
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description="AirOps local dashboard")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"AirOps running at http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
