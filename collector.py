#!/usr/bin/env python3
"""Tiny localhost sink for extract.js output.

Run it, then from each EduRev result page POST the extractor's JSON to
http://localhost:8787/save. One file per test lands in raw/.
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(ROOT, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/extract.js"):
            src = open(os.path.join(os.path.dirname(ROOT), "extract.js"), "rb").read()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(src))); self.end_headers()
            self.wfile.write(src); return
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(b"collector up")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n))
            slug = "".join(c if c.isalnum() or c in "-_" else "_"
                           for c in payload.get("slug", "test"))
            path = os.path.join(ROOT, slug + ".json")
            with open(path, "w") as f:
                json.dump(payload.get("data", payload), f, indent=1)
            msg = {"ok": True, "saved": os.path.basename(path),
                   "questions": len(payload.get("data", {}).get("questions", []))}
        except Exception as e:
            msg = {"ok": False, "error": str(e)}
        body = json.dumps(msg).encode()
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        sys.stderr.write("%s - %s\n" % (self.address_string(), a[0] % a[1:]))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print("collector listening on http://localhost:%d  ->  %s" % (port, ROOT), flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
