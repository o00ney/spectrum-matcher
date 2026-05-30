#!/usr/bin/env python3
"""Generate demo Bruker spectrum zip files for testing and demonstrations."""

import os
import struct
import zipfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

DEMOS = {
    "demo_chamomile_flavor": {
        "description": "Roman Chamomile dominant — single strong peak pattern",
        "solvent": "MeOD",
        "frequency": 600,
        "scans": 128,
        "td": 65536,
        "fid_scale": 1.0,
        "noise": 0.02,
    },
    "demo_fig_extract": {
        "description": "Fig extract profile — mid-field emphasis",
        "solvent": "MeOD",
        "frequency": 600,
        "scans": 64,
        "td": 65536,
        "fid_scale": 0.8,
        "noise": 0.03,
    },
    "demo_citrus_blend": {
        "description": "Citrus blend — multiple aromatic peaks",
        "solvent": "DMSO",
        "frequency": 400,
        "scans": 256,
        "td": 32768,
        "fid_scale": 1.2,
        "noise": 0.01,
    },
    "demo_tobacco_sample": {
        "description": "Tobacco-derived sample — broad hump baseline",
        "solvent": "MeOD",
        "frequency": 600,
        "scans": 512,
        "td": 131072,
        "fid_scale": 0.9,
        "noise": 0.04,
    },
    "demo_unknown_mixture": {
        "description": "Unknown mixture — complex overlapping signals",
        "solvent": "CDCl3",
        "frequency": 500,
        "scans": 200,
        "td": 65536,
        "fid_scale": 1.1,
        "noise": 0.05,
    },
    "demo_quick_scan": {
        "description": "Quick scan — low resolution, few scans",
        "solvent": "MeOD",
        "frequency": 400,
        "scans": 16,
        "td": 16384,
        "fid_scale": 0.5,
        "noise": 0.08,
    },
}


def generate_fid_data(n_points, scale=1.0, noise=0.02, seed=0):
    """Generate synthetic FID-like binary data."""
    import random as rng
    rng.seed(seed)
    data = bytearray()
    for i in range(n_points):
        t = i / n_points
        # decaying sine + noise
        real = int(scale * 5000 * (1 - t) * (
            0.3 * _sinc(i * 0.01) +
            0.5 * _sinc((i - n_points * 0.3) * 0.02) +
            0.4 * _sinc((i - n_points * 0.6) * 0.015)
        ) + rng.gauss(0, noise * 1000))
        imag = int(scale * 5000 * (1 - t) * (
            0.3 * _sinc(i * 0.01 + 1.57) +
            0.5 * _sinc((i - n_points * 0.3) * 0.02 + 1.57) +
            0.4 * _sinc((i - n_points * 0.6) * 0.015 + 1.57)
        ) + rng.gauss(0, noise * 1000))
        data.extend(struct.pack("<i", real))
        data.extend(struct.pack("<i", imag))
    return bytes(data)


def _sinc(x):
    import math
    return math.sin(x) / x if abs(x) > 1e-10 else 1.0


def build_acqu(solvent, frequency, scans, td):
    return (
        f"##TITLE= Demo Spectrum\n"
        f"##JCAMPDX= 5.00\n"
        f"##DATATYPE= NMR Data\n"
        f"##OWNER= demo\n"
        f"$$ {solvent}\n"
        f"##$SOLVENT= {solvent}\n"
        f"##$BF1= {frequency}.15\n"
        f"##$NS= {scans}\n"
        f"##$TD= {td}\n"
        f"##$SW_h= 20.83\n"
        f"##$O1= 2350.0\n"
    ).encode()


def build_proc():
    return (
        f"##TITLE= Processed\n"
        f"##$SI= 32768\n"
        f"##$OFFSET= 0\n"
        f"##$SF= 600.15\n"
        f"##$SW_p= 20.83\n"
    ).encode()


def build_title(text):
    return text.encode()


def build_pdata_1r():
    """Generate synthetic processed 1r (real) data — 262144 bytes."""
    data = bytearray()
    import random as rng
    rng.seed(42)
    for i in range(65536):
        val = int(10000 * (1 - i / 65536) * (
            0.4 * _sinc(i * 0.005) +
            0.6 * _sinc((i - 20000) * 0.008)
        ) + rng.gauss(0, 200))
        data.extend(struct.pack("<i", val))
    return bytes(data)


def create_demo_zip(name, config):
    """Create a demo Bruker spectrum zip file."""
    zip_path = TESTS_DIR / f"{name}.zip"
    td = config["td"]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Top-level name directory
        sample_dir = name

        # Bruker acqu file
        zf.writestr(
            f"{name}/acqu",
            build_acqu(config["solvent"], config["frequency"],
                        config["scans"], config["td"]),
        )
        # acqus (raw acquisition parameters)
        zf.writestr(
            f"{name}/acqus",
            build_acqu(config["solvent"], config["frequency"],
                        config["scans"], config["td"]),
        )

        # FID (raw time-domain data)
        fid_data = generate_fid_data(
            td, scale=config["fid_scale"], noise=config["noise"],
            seed=hash(name) % 1000,
        )
        zf.writestr(f"{name}/fid", fid_data)

        # pdata directory
        zf.writestr(f"{name}/pdata/1/proc", build_proc())
        zf.writestr(f"{name}/pdata/1/procs", build_proc())
        zf.writestr(f"{name}/pdata/1/1r", build_pdata_1r())
        zf.writestr(f"{name}/pdata/1/title", build_title(config["description"]))
        zf.writestr(f"{name}/pdata/1/auditp.txt",
                    f"{config['description']}\nGenerated for demo.\n".encode())

        # Additional Bruker metadata files
        zf.writestr(f"{name}/format.temp", b"##TITLE=Temperature format\n")
        zf.writestr(f"{name}/uxnmr.info",
                    f"##TITLE=Demo {config['frequency']} MHz\n"
                    f"##ORIGIN= Bruker BioSpin\n"
                    f"##OWNER= demo\n".encode())

        # Thumbnail PNG
        thumb = _make_thumb_png()
        zf.writestr(f"{name}/pdata/1/thumb.png", thumb)

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"  Created {name}.zip ({size_kb:.0f} KB) — {config['description']}")


def _make_thumb_png(width=240, height=120):
    """Generate a minimal spectrum-like thumbnail PNG."""
    import struct as st
    import zlib

    pixels = bytearray([255] * width * height * 3)
    for x in range(width):
        y = int(height / 2 - 30 * (1 - x / width) * (
            0.3 + 0.4 * (_sinc(x * 0.05) if abs(x * 0.05) > 1e-10 else 1) +
            0.3 * (_sinc((x - width * 0.4) * 0.08) if abs((x - width * 0.4) * 0.08) > 1e-10 else 1)
        ))
        if 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset:offset + 3] = b'\x1e\x1e\x2e'

    raw_rows = []
    for y in range(height):
        start = y * width * 3
        raw_rows.append(b'\x00' + bytes(pixels[start:start + width * 3]))

    compressed = zlib.compress(b''.join(raw_rows), level=9)
    ihdr = st.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    def chunk(ctype, data):
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return st.pack(">I", len(data)) + ctype + data + st.pack(">I", crc)

    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + \
           chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def main():
    print("Generating demo Bruker spectrum zips...\n")
    for name, config in DEMOS.items():
        zip_path = TESTS_DIR / f"{name}.zip"
        if zip_path.exists():
            print(f"  Skip {name}.zip (already exists)")
            continue
        create_demo_zip(name, config)
    print(f"\nDone. {len(DEMOS)} demo zips in tests/")
    print("Use with mock server: python client/tools/mock_server.py")


if __name__ == "__main__":
    main()
