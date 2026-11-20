#!/usr/bin/env python3
"""One-day broadsheet poster for Friday 20 November 2026.

Reads the stories in news.json (next to this file) and draws them into
a 1024x1024 PNG at /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Pure Python 3.13 standard library only: a hand-made 5x7 bitmap font, a
small rasteriser that paints rectangles, lines, circles and triangles
onto an RGB buffer, and a PNG writer built on zlib and struct. There is
no network access and no randomness, so the same news.json always
produces the same PNG bytes.

Layout, top to bottom: a dark masthead band with the date, a full-width
lead story with a drawn calendar scene, two half-width stories, three
third-width stories, a by-the-numbers strip, an also-today strip and a
sources footer.
"""

import json
import math
import os
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Page geometry
# ---------------------------------------------------------------------------
PAGE_W = 1024
PAGE_H = 1024
MARGIN = 24
GUTTER = 20

# ---------------------------------------------------------------------------
# Palette: newsprint cream, deep navy, signal red, gold, slate blue.
# ---------------------------------------------------------------------------
PAPER = (247, 243, 232)
PAPER_DIM = (238, 231, 210)
CARD = (255, 255, 255)
INK = (24, 28, 38)
NAVY = (18, 32, 58)
NAVY_SOFT = (38, 58, 96)
SLATE = (96, 104, 122)
FAINT = (118, 112, 98)
RED = (178, 34, 28)
RED_SOFT = (232, 190, 186)
GOLD = (198, 156, 34)
GOLD_SOFT = (246, 214, 96)
SKY = (214, 231, 244)
SKY_DEEP = (52, 96, 142)
SEA = (34, 68, 110)
TEAL = (32, 120, 110)
LEAF = (58, 124, 58)
SAND = (216, 196, 138)

# ---------------------------------------------------------------------------
# 5x7 bitmap font. One glyph is seven rows of five bits; the leftmost
# pixel is the most significant bit. Text is upper-cased before drawing,
# so only capitals, digits and the punctuation below are needed.
# ---------------------------------------------------------------------------
ROWS = 7
COLS = 5
STEP = 6  # pixels per character advance, including one blank column

FONT = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11100, 0b10010, 0b10001, 0b10001, 0b10001, 0b10010, 0b11100),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b01100, 0b01100),
    ",": (0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ":": (0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    ";": (0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100),
    "-": (0, 0, 0, 0b01110, 0, 0, 0),
    "'": (0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "+": (0, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "#": (0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
    "=": (0, 0, 0b11111, 0, 0b11111, 0, 0),
    "*": (0, 0b10101, 0b01110, 0b11111, 0b01110, 0b10101, 0),
    '"': (0b01010, 0b01010, 0, 0, 0, 0, 0),
    "_": (0, 0, 0, 0, 0, 0, 0b11111),
    "|": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    ">": (0b10000, 0b01000, 0b00100, 0b00010, 0b00100, 0b01000, 0b10000),
    "<": (0b00001, 0b00010, 0b00100, 0b01000, 0b00100, 0b00010, 0b00001),
}
FALLBACK = FONT["?"]


def text_width(text, size):
    """Pixel width of `text` at `size`, without a trailing advance."""
    if not text:
        return 0
    return len(text) * STEP * size - size


def wrap_words(text, max_width, size):
    """Greedy word wrap; a lone over-long word is split to fit."""
    words = text.upper().split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        joined = current + " " + word
        if text_width(joined, size) <= max_width:
            current = joined
            continue
        lines.append(current)
        current = word
        while text_width(current, size) > max_width:
            take = max(1, max_width // (STEP * size))
            lines.append(current[:take])
            current = current[take:]
    lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Canvas: a flat RGB buffer with filled shapes and bitmap text.
# ---------------------------------------------------------------------------
class Canvas:
    """A 24-bit RGB page backed by one bytearray."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.buf = bytearray(width * height * 3)
        self.rect(0, 0, width, height, background)

    def dot(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            off = (y * self.width + x) * 3
            self.buf[off:off + 3] = bytes(colour)

    def rect(self, x, y, w, h, colour):
        left = max(x, 0)
        top = max(y, 0)
        right = min(x + w, self.width)
        bottom = min(y + h, self.height)
        if right <= left or bottom <= top:
            return
        row = bytes(colour) * (right - left)
        for yy in range(top, bottom):
            start = (yy * self.width + left) * 3
            self.buf[start:start + len(row)] = row

    def border(self, x, y, w, h, colour, thick=2):
        self.rect(x, y, w, thick, colour)
        self.rect(x, y + h - thick, w, thick, colour)
        self.rect(x, y, thick, h, colour)
        self.rect(x + w - thick, y, thick, h, colour)

    def hline(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.rect(x, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham line stamped with a square brush."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.rect(x0 - half, y0 - half, thick, thick, colour)
            if x0 == x1 and y0 == y1:
                return
            twice = 2 * err
            if twice >= dy:
                err += dy
                x0 += sx
            if twice <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, radius, colour):
        """Filled circle."""
        for yy in range(cy - radius, cy + radius + 1):
            dy = yy - cy
            if abs(dy) > radius:
                continue
            half = int((radius * radius - dy * dy) ** 0.5)
            self.rect(cx - half, yy, 2 * half + 1, 1, colour)

    def ring(self, cx, cy, radius, colour, thick=2):
        """Circle outline `thick` pixels wide."""
        inner = radius - thick
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if inner * inner <= d2 <= radius * radius:
                    self.dot(xx, yy, colour)

    def triangle(self, ax, ay, bx, by, cx, cy, colour):
        """Filled triangle, scanline by scanline."""
        (tx, ty), (mx, my), (bx2, by2) = sorted(
            ((ax, ay), (bx, by), (cx, cy)), key=lambda p: p[1])

        def edge_x(y, p, q):
            if q[1] == p[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])

        for y in range(ty, by2 + 1):
            if y < my:
                left = edge_x(y, (tx, ty), (mx, my))
            else:
                left = edge_x(y, (mx, my), (bx2, by2))
            right = edge_x(y, (tx, ty), (bx2, by2))
            lo, hi = sorted((int(round(left)), int(round(right))))
            self.rect(lo, y, hi - lo + 1, 1, colour)

    def arc(self, cx, cy, radius, start_deg, end_deg, colour, thick=2):
        """Arc of a circle, drawn degree by degree."""
        steps = max(1, int(abs(end_deg - start_deg)))
        for k in range(steps + 1):
            ang = math.radians(start_deg + (end_deg - start_deg) * k / steps)
            px = cx + int(radius * math.cos(ang))
            py = cy + int(radius * math.sin(ang))
            self.rect(px - thick // 2, py - thick // 2, thick, thick, colour)

    # -- text ---------------------------------------------------------------
    def glyph(self, x, y, size, colour, char):
        rows = FONT.get(char, FALLBACK)
        for row_idx, bits in enumerate(rows):
            for col in range(COLS):
                if bits >> (COLS - 1 - col) & 1:
                    self.rect(x + col * size, y + row_idx * size,
                              size, size, colour)

    def text(self, x, y, size, colour, string, align="left"):
        string = string.upper()
        if align == "center":
            x -= text_width(string, size) // 2
        elif align == "right":
            x -= text_width(string, size)
        for i, char in enumerate(string):
            self.glyph(x + i * STEP * size, y, size, colour, char)

    def paragraph(self, x, y, width, size, colour, string,
                  leading=None, limit=None):
        """Wrapped block; returns the y just below the last line."""
        if leading is None:
            leading = ROWS * size + 3
        lines = wrap_words(string, width, size)
        if limit is not None:
            lines = lines[:limit]
        for i, line in enumerate(lines):
            self.text(x, y + i * leading, size, colour, line)
        return y + len(lines) * leading


# ---------------------------------------------------------------------------
# Story illustrations. Each paints inside the box (x, y, w, h).
# ---------------------------------------------------------------------------
def paint_calendar(page, x, y, w, h):
    """The Iran decision, pushed to 2027: a calendar page for the 20th
    with a red arrow pointing on to a 2027 tag."""
    page.rect(x, y, w, h, SKY)
    # The calendar page, slightly tilted by its shadow.
    page.rect(x + 18, y + 16, w - 36, h - 28, (0, 0, 0))
    page.rect(x + 14, y + 12, w - 36, h - 28, CARD)
    page.border(x + 14, y + 12, w - 36, h - 28, INK, thick=2)
    # Red header band with two binder rings.
    page.rect(x + 14, y + 12, w - 36, 34, RED)
    page.disc(x + 44, y + 12, 6, GOLD)
    page.disc(x + w - 58, y + 12, 6, GOLD)
    page.text(x + w // 2, y + 20, 2, CARD, "NOV", align="center")
    # The big day number.
    page.text(x + w // 2, y + 62, 9, INK, "20", align="center")
    page.hline(x + 44, y + 128, w - 102, SLATE, thick=2)
    # A small clock: the decision is on hold. It sits on the left,
    # clear of the arrow pointing on to 2027 on the right.
    cx, cy = x + 88, y + 172
    page.ring(cx, cy, 24, NAVY, thick=4)
    page.disc(cx, cy, 4, RED)
    page.line(cx, cy, cx, cy - 15, NAVY, thick=3)
    page.line(cx, cy, cx + 11, cy + 5, NAVY, thick=3)
    # Arrow to 2027.
    page.text(x + 245, y + 158, 3, RED, "-> 2027", align="center")
    page.text(x + w // 2, y + 210, 2, FAINT, "DECISION IN 2027",
              align="center")


def paint_storm(page, x, y, w, h):
    """Cyclone Akvan: a spiral of rings and sweeping arms over the sea,
    with rain streaks and a sliver of coast."""
    page.rect(x, y, w, h, SKY)
    # Coastline creeping in from the lower right.
    page.triangle(x + w, y + h, x + w - 46, y + h, x + w, y + h - 64, SAND)
    page.rect(x + w - 38, y + h - 24, 38, 24, SAND)
    # The storm: nested rings with a solid eye. Every radius stays
    # inside the box so the spiral never crosses its frame.
    cx, cy = x + w // 2 - 6, y + h // 2 - 6
    page.ring(cx, cy, 28, CARD, thick=5)
    page.ring(cx, cy, 19, SKY_DEEP, thick=4)
    page.ring(cx, cy, 10, CARD, thick=3)
    page.disc(cx, cy, 5, SEA)
    # Two curved arms sweeping out of the spiral.
    page.arc(cx, cy, 34, 200, 320, CARD, thick=4)
    page.arc(cx, cy, 34, 20, 140, SKY_DEEP, thick=4)
    page.arc(cx, cy, 40, 230, 300, CARD, thick=3)
    # Slanted rain in the corners.
    for rx, ry in ((10, 10), (w - 18, 12), (12, h - 20), (w - 14, h - 28)):
        page.line(x + rx, y + ry, x + rx - 5, y + ry + 12, SKY_DEEP, thick=2)
    # Wind barbs along the bottom.
    for i in range(4):
        bx = x + 12 + i * 18
        page.line(bx, y + h - 8, bx + 8, y + h - 14, SEA, thick=2)


def paint_flags(page, x, y, w, h):
    """Europe ready for talks: the EU ring of stars beside the Russian
    tricolour, with a speech bubble between them."""
    page.rect(x, y, w, h, PAPER_DIM)
    # EU flag: blue field, a ring of twelve gold stars. Small enough
    # to sit beside the tricolour without touching it.
    fx, fy, fw, fh = x + 6, y + 6, 30, 22
    page.rect(fx, fy, fw, fh, NAVY_SOFT)
    page.border(fx, fy, fw, fh, INK, thick=1)
    for k in range(12):
        ang = 2 * math.pi * k / 12 - math.pi / 2
        sx = fx + fw // 2 + int(9 * math.cos(ang))
        sy = fy + fh // 2 + int(7 * math.sin(ang))
        page.disc(sx, sy, 1, GOLD)
    # Russian tricolour.
    rx, ry, rw, rh = x + 40, y + 6, 30, 22
    page.rect(rx, ry, rw, 7, CARD)
    page.rect(rx, ry + 7, rw, 8, SKY_DEEP)
    page.rect(rx, ry + 15, rw, 7, RED)
    page.border(rx, ry, rw, rh, INK, thick=1)
    # Speech bubble: talks are on. It ends well above the table.
    bx, by, bw, bh = x + 18, y + 34, 40, 18
    page.rect(bx, by, bw, bh, CARD)
    page.border(bx, by, bw, bh, INK, thick=2)
    page.triangle(bx + 8, by + bh, bx + 20, by + bh, bx + 12, by + bh + 6,
                  CARD)
    page.line(bx + 8, by + bh, bx + 12, by + bh + 6, INK, thick=2)
    page.line(bx + 20, by + bh, bx + 12, by + bh + 6, INK, thick=2)
    page.text(x + w // 2, by + 6, 2, RED, "?", align="center")
    # A table line and two chairs: both sides sit down.
    page.hline(x + 8, y + h - 8, w - 16, INK, thick=3)
    page.rect(x + 8, y + h - 18, 12, 10, NAVY_SOFT)
    page.rect(x + w - 20, y + h - 18, 12, 10, RED)


def paint_ballot(page, x, y, w, h):
    """The Senate vote: a ballot box with two tally bars, 51 to 48."""
    page.rect(x, y, w, h, PAPER_DIM)
    # Ballot box, kept inside the small frame: no tally bars here,
    # the 51-48 vote is in the headline and summary instead.
    page.rect(x + 10, y + 28, w - 20, h - 38, NAVY)
    page.rect(x + 13, y + 24, w - 26, 6, NAVY)
    page.rect(x + w // 2 - 10, y + 25, 20, 3, CARD)
    # Paper sliding through the slot.
    page.line(x + w // 2 - 4, y + 8, x + w // 2 + 4, y + 24, INK, thick=2)
    page.rect(x + w // 2 - 7, y + 6, 11, 16, CARD)
    page.border(x + w // 2 - 7, y + 6, 11, 16, INK, thick=1)
    # Gold tick for the winning side.
    page.line(x + 16, y + h - 16, x + 22, y + h - 10, GOLD, thick=3)
    page.line(x + 22, y + h - 10, x + 36, y + h - 24, GOLD, thick=3)


def paint_embassy(page, x, y, w, h):
    """Kyiv: a diplomatic building with a flag, a crack through its
    facade and smoke rising from the roof."""
    page.rect(x, y, w, h, SKY)
    # Smoke puffs above the roof.
    page.disc(x + w - 14, y + 8, 5, SLATE)
    page.disc(x + w - 22, y + 12, 4, SLATE)
    # The building, sized to the small frame.
    bx, by, bw, bh = x + 12, y + 28, w - 24, h - 34
    page.rect(bx, by, bw, bh, CARD)
    page.border(bx, by, bw, bh, INK, thick=2)
    page.rect(bx, by, bw, 6, NAVY)
    # Two columns of windows, both inside the facade.
    for row in range(2):
        for col in range(2):
            wx = bx + 5 + col * 14
            wy = by + 8 + row * 8
            page.rect(wx, wy, 7, 5, SKY_DEEP)
    # A crack zig-zagging down the facade.
    page.line(bx + 16, by + 6, bx + 13, by + 12, INK, thick=1)
    page.line(bx + 13, by + 12, bx + 18, by + 18, INK, thick=1)
    # Flag on a pole above the door.
    page.vline(bx + bw // 2, by - 10, 10, INK, thick=1)
    page.rect(bx + bw // 2 + 1, by - 10, 11, 4, RED)
    page.rect(bx + bw // 2 + 1, by - 6, 11, 3, CARD)
    # Door.
    page.rect(bx + bw // 2 - 4, by + bh - 8, 8, 8, NAVY)


def paint_game(page, x, y, w, h):
    """GTA VI's record day: a game controller on a neon dusk skyline."""
    page.rect(x, y, w, h, NAVY)
    # Dusk band and a low sun.
    page.rect(x, y + h // 2, w, h // 2, (64, 32, 88))
    page.disc(x + w // 2, y + 10, 7, GOLD)
    page.disc(x + w // 2, y + 10, 4, GOLD_SOFT)
    # Tiny skyline silhouettes along the bottom.
    for bx, bw, bh in ((4, 8, 10), (16, 6, 14), (w - 24, 8, 12),
                       (w - 12, 6, 10)):
        page.rect(x + bx, y + h - 4 - bh, bw, bh, INK)
    # The controller, sized to the small frame. No price text here:
    # the $1.84bn figure is already in the headline beside it.
    cx, cy = x + w // 2, y + h // 2 + 8
    page.rect(cx - 18, cy - 8, 36, 16, CARD)
    page.disc(cx - 18, cy, 8, CARD)
    page.disc(cx + 18, cy, 8, CARD)
    page.border(cx - 26, cy - 8, 52, 16, INK, thick=2)
    # D-pad on the left, four buttons on the right.
    page.rect(cx - 16, cy - 2, 10, 4, NAVY)
    page.rect(cx - 13, cy - 5, 4, 10, NAVY)
    for dx, dy, col in ((9, -4, RED), (14, 1, GOLD),
                        (9, 5, TEAL), (4, 1, LEAF)):
        page.disc(cx + dx, cy + dy, 3, col)


ILLUSTRATIONS = {
    "calendar": paint_calendar,
    "storm": paint_storm,
    "flags": paint_flags,
    "ballot": paint_ballot,
    "embassy": paint_embassy,
    "game": paint_game,
}


# ---------------------------------------------------------------------------
# PNG encoding: truecolour, 8 bit, no interlace, filter type 0 per row.
# ---------------------------------------------------------------------------
def make_chunk(kind, payload):
    size = struct.pack(">I", len(payload))
    crc = struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return size + kind + payload + crc


def encode_png(page):
    header = struct.pack(">IIBBBBB", page.width, page.height, 8, 2, 0, 0, 0)
    stride = page.width * 3
    scanlines = bytearray()
    for row in range(page.height):
        scanlines.append(0)  # filter: none
        scanlines += page.buf[row * stride:(row + 1) * stride]
    return (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", header)
        + make_chunk(b"IDAT", zlib.compress(bytes(scanlines), 9))
        + make_chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Page composition
# ---------------------------------------------------------------------------
def draw_header(page, data):
    """Dark navy band: masthead, gold rule, date and the day's tag."""
    page.rect(0, 0, PAGE_W, 118, NAVY)
    page.text(PAGE_W // 2, 20, 5, CARD, data["masthead"], align="center")
    page.hline(MARGIN, 72, PAGE_W - 2 * MARGIN, GOLD, thick=4)
    page.text(PAGE_W // 2, 84, 3, GOLD_SOFT, data["date_label"],
              align="center")
    tag = data.get("date_tag", "")
    if tag:
        page.text(PAGE_W - MARGIN, 84, 2, CARD, tag, align="right")


def draw_lead(page, story):
    top, height = 134, 266
    page.rect(MARGIN, top, PAGE_W - 2 * MARGIN, height, CARD)
    page.border(MARGIN, top, PAGE_W - 2 * MARGIN, height, INK, thick=3)
    ILLUSTRATIONS[story["icon"]](page, MARGIN + 4, top + 4, 360, height - 8)
    page.border(MARGIN + 4, top + 4, 360, height - 8, INK, thick=2)
    text_x = 412
    page.text(text_x, top + 22, 2, RED, story["kicker"])
    page.paragraph(text_x, top + 50, 576, 4, INK, story["headline"],
                   leading=34)
    page.paragraph(text_x, top + 150, 576, 2, INK, story["summary"],
                   leading=17)


def draw_card(page, story, x, y, w, h, icon, head_size, head_lead):
    page.rect(x, y, w, h, CARD)
    page.border(x, y, w, h, INK, thick=2)
    pad = 10 if icon <= 76 else 12
    ILLUSTRATIONS[story["icon"]](page, x + pad, y + pad, icon, icon)
    page.border(x + pad, y + pad, icon, icon, INK, thick=1)
    text_x = x + pad + icon + 10
    text_w = x + w - pad - text_x
    page.text(text_x, y + 14, 2, RED, story["kicker"])
    bottom = page.paragraph(text_x, y + 36, text_w, head_size, INK,
                            story["headline"], leading=head_lead)
    summary_y = min(bottom + 10, y + h - 84)
    page.paragraph(x + pad, summary_y, w - 2 * pad, 2, INK,
                   story["summary"], leading=17)


def draw_tail(page, data):
    """Numbers strip, also-today strip and the sources footer."""
    page.hline(MARGIN, 844, PAGE_W - 2 * MARGIN, INK, thick=3)
    page.text(PAGE_W // 2, 856, 2, NAVY, data["numbers"], align="center")
    page.text(MARGIN, 888, 2, RED, "ALSO TODAY")
    for i, item in enumerate(data["also"]):
        ix = MARGIN + (i % 2) * 500
        iy = 912 + (i // 2) * 22
        page.rect(ix, iy + 3, 8, 8, RED)
        page.text(ix + 14, iy, 2, INK, item)
    page.text(PAGE_W // 2, 962, 2, FAINT, data["footer_note"],
              align="center")
    page.text(PAGE_W // 2, 986, 2, FAINT, data["sources"], align="center")


def compose(data):
    page = Canvas(PAGE_W, PAGE_H, PAPER)
    draw_header(page, data)
    draw_lead(page, data["lead"])

    # Second row: two half-width cards.
    card_w = (PAGE_W - 2 * MARGIN - GUTTER) // 2
    for i, story in enumerate(data["row2"]):
        draw_card(page, story, MARGIN + i * (card_w + GUTTER),
                  416, card_w, 196, 76, 3, 24)

    # Third row: three third-width cards.
    card_w = (PAGE_W - 2 * MARGIN - 2 * GUTTER) // 3
    for i, story in enumerate(data["row3"]):
        draw_card(page, story, MARGIN + i * (card_w + GUTTER),
                  628, card_w, 196, 56, 2, 17)
    draw_tail(page, data)
    return page


def main():
    here = Path(__file__).resolve().parent
    with (here / "news.json").open(encoding="utf-8") as fh:
        data = json.load(fh)
    page = compose(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entry.png").write_bytes(encode_png(page))


if __name__ == "__main__":
    main()
