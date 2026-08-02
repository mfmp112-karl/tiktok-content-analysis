"""A minimal PDF writer, standard library only.

This exists for one job: when no Chromium-family browser is available, the
report is captured as full-page PNGs by the stealth browser and those images
have to become a PDF. Firefox cannot print to PDF — Playwright's `page.pdf()`
is Chromium-only — so there is no browser-side route, and pulling in reportlab
or img2pdf would break the "two dependencies" promise that makes this tool
installable by people who are not developers.

The output is a page-per-image PDF. It is genuinely worse than the Chromium
path: raster instead of vector, no selectable text, a much larger file. It is
here so that nobody is left without a PDF, not because it is the good option.

PNG decoding is done properly — parsed, unfiltered, converted to RGB, then
recompressed — rather than trying to smuggle the original IDAT stream through
PDF's PNG predictor. The fast path only works for a narrow set of PNG variants,
and browser screenshots are usually RGBA, which is exactly the case it cannot
handle.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

# 72pt = 1 inch. A4 is 595.28 x 841.89 pt.
A4 = (595.28, 841.89)


class PngError(ValueError):
    pass


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    """Return (width, height, raw RGB bytes). Handles the colour types a
    browser screenshot actually produces: RGB, RGBA, grey and grey+alpha."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError("not a PNG")

    pos = 8
    width = height = depth = colour = interlace = 0
    idat = bytearray()
    palette = b""
    while pos < len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif ctype == b"PLTE":
            palette = chunk
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"IEND":
            break

    if depth != 8:
        raise PngError(f"only 8-bit PNGs are supported (got {depth}-bit)")
    if interlace:
        raise PngError("interlaced PNGs are not supported")

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour)
    if channels is None:
        raise PngError(f"unsupported colour type {colour}")

    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(height * stride)
    prev = bytearray(stride)
    src = 0
    for row in range(height):
        filt = raw[src]
        src += 1
        line = bytearray(raw[src:src + stride])
        src += stride
        if filt == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upleft = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        elif filt != 0:
            raise PngError(f"unknown row filter {filt}")
        out[row * stride:(row + 1) * stride] = line
        prev = line

    # Flatten to RGB, compositing any alpha onto white (the report's surface).
    if colour == 2:
        rgb = bytes(out)
    elif colour == 6:
        rgb = bytearray(width * height * 3)
        for i in range(width * height):
            r, g, b, a = out[i * 4:i * 4 + 4]
            if a == 255:
                rgb[i * 3:i * 3 + 3] = bytes((r, g, b))
            else:
                f = a / 255.0
                rgb[i * 3:i * 3 + 3] = bytes((
                    int(r * f + 255 * (1 - f)),
                    int(g * f + 255 * (1 - f)),
                    int(b * f + 255 * (1 - f))))
        rgb = bytes(rgb)
    elif colour == 0:
        rgb = bytes(b for v in out for b in (v, v, v))
    elif colour == 4:
        rgb = bytearray(width * height * 3)
        for i in range(width * height):
            v, a = out[i * 2:i * 2 + 2]
            f = a / 255.0
            g = int(v * f + 255 * (1 - f))
            rgb[i * 3:i * 3 + 3] = bytes((g, g, g))
        rgb = bytes(rgb)
    elif colour == 3:
        if not palette:
            raise PngError("indexed PNG without a palette")
        rgb = bytes(b for idx in out for b in palette[idx * 3:idx * 3 + 3])
    else:
        raise PngError(f"unsupported colour type {colour}")

    return width, height, rgb


def images_to_pdf(png_paths: list[Path], out_path: Path,
                  page_size: tuple[float, float] = A4) -> Path:
    """One image per page, scaled to fit while preserving aspect ratio."""
    if not png_paths:
        raise ValueError("no images to write")

    page_w, page_h = page_size
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)          # 1-based object numbers

    # Reserve 1 = catalogue, 2 = pages tree; fill them in once the count is known.
    objects.append(b"")
    objects.append(b"")

    page_ids: list[int] = []
    for path in png_paths:
        width, height, rgb = decode_png(Path(path).read_bytes())
        stream = zlib.compress(rgb, 6)
        img_id = add(
            b"<< /Type /XObject /Subtype /Image /Width " + str(width).encode() +
            b" /Height " + str(height).encode() +
            b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode"
            b" /Length " + str(len(stream)).encode() + b" >>\nstream\n" +
            stream + b"\nendstream")

        scale = min(page_w / width, page_h / height)
        draw_w, draw_h = width * scale, height * scale
        x, y = (page_w - draw_w) / 2, (page_h - draw_h) / 2
        content = (f"q {draw_w:.2f} 0 0 {draw_h:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q"
                   ).encode()
        content_id = add(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
                         + content + b"\nendstream")
        page_id = add(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " +
            f"{page_w:.2f} {page_h:.2f}".encode() + b"]"
            b" /Resources << /XObject << /Im0 " + str(img_id).encode() + b" 0 R >> >>"
            b" /Contents " + str(content_id).encode() + b" 0 R >>")
        page_ids.append(page_id)

    kids = b" ".join(f"{pid} 0 R".encode() for pid in page_ids)
    objects[1] = (b"<< /Type /Pages /Kids [" + kids + b"] /Count " +
                  str(len(page_ids)).encode() + b" >>")
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objects) + 1).encode() +
            b" /Root 1 0 R >>\nstartxref\n" + str(xref_at).encode() + b"\n%%EOF\n")

    out_path = Path(out_path)
    out_path.write_bytes(bytes(out))
    return out_path
