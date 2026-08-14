"""Render the existing VaultKey SVG into a multi-resolution Windows ICO."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "assets" / "icons" / "vaultkey.svg"
DESTINATION = PROJECT_ROOT / "assets" / "icons" / "vaultkey.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    payload = QByteArray()
    buffer = QBuffer(payload)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, "PNG"):
        raise RuntimeError(f"Unable to encode the {size}px icon.")
    buffer.close()
    return bytes(payload)


def generate_icon() -> Path:
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError(f"Unable to read the source icon: {SOURCE}")

    images = [(size, _render_png(renderer, size)) for size in SIZES]
    header_size = 6 + 16 * len(images)
    offset = header_size
    directory = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    payloads: list[bytes] = []
    for size, payload in images:
        encoded_size = 0 if size == 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                encoded_size,
                encoded_size,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    temporary = DESTINATION.with_suffix(".ico.tmp")
    temporary.write_bytes(bytes(directory) + b"".join(payloads))
    temporary.replace(DESTINATION)
    return DESTINATION


if __name__ == "__main__":
    print(generate_icon())
