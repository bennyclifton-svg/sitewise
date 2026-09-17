"""Isolated Docker delivery checks; never contacts the application or production DB."""
import gzip
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True).strip()


def main() -> None:
    web_image, api_image = sys.argv[1:3]
    name = "sitewise-smoke-" + uuid.uuid4().hex[:12]
    api_name, web_name = name + "-api", name + "-web"
    stub = '''
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b"data: first\\n\\n"); self.wfile.flush()
        time.sleep(3)
        self.wfile.write(b"data: last\\n\\n"); self.wfile.flush()
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
'''
    docker("network", "create", name)
    try:
        docker("run", "-d", "--name", api_name, "--network", name,
               "--network-alias", "sitewise-api", "--entrypoint", "python", api_image, "-u", "-c", stub)
        docker("run", "-d", "--name", web_name, "--network", name,
               "-p", "127.0.0.1::80", web_image)
        port = docker("port", web_name, "80/tcp").rsplit(":", 1)[1]
        base = "http://127.0.0.1:" + port
        for attempt in range(30):
            try:
                with urllib.request.urlopen(base, timeout=2) as response:
                    html = response.read().decode()
                    assert response.headers["Cache-Control"] == "no-cache"
                # Static HTML can be ready before the fake upstream is listening.
                with urllib.request.urlopen(base + "/api/health", timeout=2) as response:
                    assert response.read() == b"ok"
                break
            except (OSError, urllib.error.URLError):
                if attempt == 29:
                    raise
                time.sleep(1)
        asset = re.search(r'/assets/[^"\s]+\.js', html).group()
        request = urllib.request.Request(base + asset, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers["Content-Encoding"] == "gzip"
            assert "immutable" in response.headers["Cache-Control"]
            assert "Accept-Encoding" in response.headers["Vary"]
            assert gzip.decompress(response.read())
        try:
            urllib.request.urlopen(base + "/assets/missing-release.js", timeout=5)
            raise AssertionError("Missing asset returned SPA HTML")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
            assert "immutable" not in exc.headers.get("Cache-Control", "")
        started = time.monotonic()
        request = urllib.request.Request(base + "/api/smoke", headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.headers.get("Content-Encoding") is None
            assert response.readline() == b"data: first\n"
            assert time.monotonic() - started < 2, "SSE first event was buffered"
            assert b"data: last" in response.read()
        print("PASS: HTML revalidation, compressed immutable JS, missing asset 404, unbuffered SSE")
    except Exception:
        for container in (api_name, web_name):
            subprocess.run(["docker", "logs", container], check=False)
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", web_name, api_name], check=False)
        docker("network", "rm", name)


if __name__ == "__main__":
    main()
