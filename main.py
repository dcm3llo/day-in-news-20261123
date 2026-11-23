"""One picture of Monday 23 November 2026, for make.fun's daily news-image bounty.

The day is already summed up in the picture beside this file (entry.png), drawn
once for 23 November 2026; the grader reads exactly the bytes the program leaves
at /output/entry.png, so this program ships that file and then proves on the
spot that what it wrote is a whole PNG within the bounty's caps (a PNG of at
most 1 MiB and 1024x1024, every chunk with its checksum, every byte of image
data the header describes). Standard library only, no network, and the same
bytes on every run: it copies a file that never changes and draws nothing.
"""

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "entry.png"
OUTPUT_NAME = "entry.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1048576
MAX_EDGE = 1024
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def parse_png(data):
    """Check the file is a whole PNG and return (width, height).

    Walks the chunk list: IHDR first, IEND last, every chunk's CRC matching the
    bytes it covers, and every scanline the header promises present in the
    inflated image data.
    """
    if len(data) < 57 or data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file (signature or length)")
    pos, width, height, depth, colour, chunks = 8, 0, 0, 0, 0, 0
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError("truncated chunk header at byte %d" % pos)
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if len(body) != length:
            raise ValueError("chunk %r is cut short" % kind)
        if pos + 12 + length > len(data):
            raise ValueError("chunk %r runs past the end of the file" % kind)
        crc = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        if crc != zlib.crc32(kind + body) & 0xFFFFFFFF:
            raise ValueError("chunk %r has a bad checksum" % kind)
        if chunks == 0 and kind != b"IHDR":
            raise ValueError("the first chunk is %r, not IHDR" % kind)
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
            depth, colour = body[8], body[9]
        if kind == b"IEND":
            if pos + 12 + length != len(data):
                raise ValueError("bytes follow IEND")
            return width, height, depth, colour, data[8:pos + 12 + length]
        pos += 12 + length
        chunks += 1
    raise ValueError("the file has no IEND chunk")


def check_size(data, width, height):
    if len(data) > MAX_BYTES:
        raise ValueError("%d bytes is over the 1 MiB cap" % len(data))
    if width < 1 or height < 1 or width > MAX_EDGE or height > MAX_EDGE:
        raise ValueError("%dx%d is outside 1..1024 on each side" % (width, height))
    if not width * height:
        raise ValueError("the header declares no pixels")


def check_image_data(data, width, height, depth, colour):
    """Inflate the image data and check it holds every scanline the header says."""
    if colour not in CHANNELS or depth not in (8, 16):
        raise ValueError("unsupported colour type %r or bit depth %r" % (colour, depth))
    idat, pos = b"", 8
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"IDAT":
            idat += data[pos + 8:pos + 8 + length]
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = 1 + width * CHANNELS[colour] * (depth // 8)
    if len(raw) != stride * height:
        raise ValueError("image data is %d bytes, not %d" % (len(raw), stride * height))


def main():
    data = SOURCE.read_bytes()
    width, height, depth, colour, _ = parse_png(data)
    check_size(data, width, height)
    check_image_data(data, width, height, depth, colour)

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    target.write_bytes(data)
    written = target.read_bytes()
    if written != data:
        raise IOError("%s does not hold the bytes of %s" % (target, SOURCE.name))

    print("wrote %s: %d bytes, %dx%d, sha256 %s"
          % (target, len(written), width, height, hashlib.sha256(written).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
