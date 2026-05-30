import base64
import json
import math
import struct
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8000

MOCK_MODEL = {
    "name": "DeepMID",
    "arch": "Siamese CNN + Spatial Pyramid Pooling",
    "params": "470K",
    "task": "NMR mixture component identification",
}


def downsample(arr, target_points=3000):
    """Uniformly subsample a 1D array to approximately target_points points."""
    n = len(arr)
    if n <= target_points:
        return list(arr)
    stride = n / target_points
    result = []
    i = 0.0
    while i < n:
        result.append(arr[int(i)])
        i += stride
    return result


def generate_mock_spectrum(n_points=32724, seed=0):
    """Generate synthetic NMR ppm/fid arrays."""
    ppm = [10.7 - 10.4 * i / (n_points - 1) for i in range(n_points)]
    fid = []
    peaks = [
        (0.9, 0.02, 1.0), (1.3, 0.03, 0.7), (2.1, 0.01, 0.5),
        (3.5, 0.04, 0.6), (5.2, 0.02, 0.8), (7.1, 0.03, 0.4),
        (8.5, 0.02, 0.3), (9.3, 0.01, 0.55),
    ]
    for i, p in enumerate(ppm):
        v = 0.0
        base = math.sin(i * 0.003) * 0.1 + 0.5 if seed == 0 else 0.3
        for center, width, amp in peaks:
            v += amp * math.exp(-((p - center * (1 + seed * 0.03)) ** 2) / (2 * width * width))
        v += base * (0.5 + 0.5 * math.sin(p * 3.7 + seed))
        fid.append(max(0.0, v))
    return ppm, fid


class MockHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path == "/docs":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"OK")
            return
        self._send_json({"detail": "Not found"}, status=404)

    def do_POST(self):
        if self.path != "/api/upload":
            self._send_json({"detail": "Not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)

        query_ppm, query_fid = generate_mock_spectrum(seed=-1)
        ds_query_ppm = downsample(query_ppm)
        ds_query_fid = downsample(query_fid)

        mock_results = [
            {"name": "Roman Chamomile Extraction-A", "probability": 0.9903, "seed": 0},
            {"name": "Fig Extraction",              "probability": 0.9240, "seed": 1},
            {"name": "Chicory Extraction",          "probability": 0.8639, "seed": 2},
            {"name": "Plum Extraction",             "probability": 0.8137, "seed": 3},
            {"name": "Carob Extraction",            "probability": 0.7098, "seed": 4},
            {"name": "Alfalfa Extraction",          "probability": 0.6523, "seed": 5},
            {"name": "Galbanum Extraction",         "probability": 0.5812, "seed": 6},
            {"name": "Hops Extraction",             "probability": 0.5201, "seed": 7},
            {"name": "Raisin Extraction",           "probability": 0.4689, "seed": 8},
            {"name": "Roman Chamomile Extraction-B","probability": 0.4012, "seed": 9},
            {"name": "Tobacco Maillard Reactants",  "probability": 0.3540, "seed": 10},
            {"name": "Valerian Root Extraction",    "probability": 0.3011, "seed": 11},
            {"name": "Yunnan Tobacco Extraction",   "probability": 0.2534, "seed": 12},
        ]

        for i, r in enumerate(mock_results):
            if i < 3:
                _, ref_fid = generate_mock_spectrum(seed=r["seed"])
                r["ppm_ds"] = downsample(query_ppm)
                r["fid_ds"] = downsample(ref_fid)
            del r["seed"]

        payload = {
            "query_name": "mock_B1_sample",
            "query_ppm": ds_query_ppm,
            "query_fid": ds_query_fid,
            "results": mock_results,
            "plot_base64": base64.b64encode(build_mock_png()).decode("ascii"),
            "model": MOCK_MODEL,
        }
        self._send_json(payload)

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
