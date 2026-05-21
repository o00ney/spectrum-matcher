import json
import math
import struct
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8000
PLOT_ID = "mock-plot"


class MockHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        if self.path != "/api/upload":
            self._send_json({"detail": "Not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)

        payload = {
            "query_name": "mock_query",
            "results": [
                {"name": "Linalool", "probability": 0.9321},
                {"name": "Geraniol", "probability": 0.8174},
                {"name": "Citral", "probability": 0.7648},
            ],
            "plot_id": PLOT_ID,
        }
        self._send_json(payload)

    def do_GET(self):
        if self.path != f"/api/plot/{PLOT_ID}":
            self._send_json({"detail": "Plot not found"}, status=404)
            return

        self._send_bytes(build_mock_png(), "image/png")

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self._send_bytes(body, "application/json", status=status)

    def _send_bytes(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_mock_png(width=900, height=360):
    pixels = bytearray([255] * width * height * 3)

    def set_pixel(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset : offset + 3] = bytes(color)

    def draw_line(x1, y1, x2, y2, color):
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy

        while True:
            set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    left = 60
    right = width - 30
    top = 35
    axis_y = height - 55
    black = (30, 30, 30)

    draw_line(left, top, left, axis_y, black)
    draw_line(left, axis_y, right, axis_y, black)

    peaks = [
        (0.14, 110, 0.010),
        (0.28, 170, 0.018),
        (0.42, 90, 0.014),
        (0.61, 145, 0.020),
        (0.78, 70, 0.016),
    ]
    colors = [(18, 18, 18), (196, 54, 54), (48, 96, 190)]
    offsets = [0, 22, 42]

    for color, offset in zip(colors, offsets):
        previous = None
        for x in range(left + 1, right):
            t = (x - left) / (right - left)
            signal = 0
            for center, amplitude, width_factor in peaks:
                signal += amplitude * math.exp(-((t - center) ** 2) / width_factor)
            signal += 12 * math.sin(t * math.pi * 18)
            y = axis_y - int(signal) + offset
            if previous:
                draw_line(previous[0], previous[1], x, y, color)
            previous = (x, y)

    raw_rows = []
    row_length = width * 3
    for y in range(height):
        start = y * row_length
        raw_rows.append(b"\x00" + bytes(pixels[start : start + row_length]))

    compressed = zlib.compress(b"".join(raw_rows), level=9)
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        signature
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )


def png_chunk(chunk_type, data):
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def main():
    server = ThreadingHTTPServer((HOST, PORT), MockHandler)
    print(f"Mock server running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
