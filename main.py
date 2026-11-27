#!/usr/bin/env python3
"""Deterministic, stdlib-only renderer of the 27 November 2026 front page.

The only external input is OUT_DIR (default /output).  The sole output is
$OUT_DIR/entry.png.  No clock, randomness, network access or third-party
modules are used, so repeated runs are byte-identical.
"""

import math
import os
import re
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------------------
# Embedded 5x7 bitmap font.  Every glyph is a tuple of seven 5-bit rows.
# The digit zero is slashed; it is deliberately different from the letter O.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10011", "10101", "10101", "10101", "11001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000",) * 7,
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00110", "00100"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    ";": ("00000", "00110", "00110", "00000", "00110", "00110", "00100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "'": ("00100", "00100", "00010", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "\u00b7": ("00000", "00000", "00000", "00110", "00000", "00000", "00000"),
}

assert FONT["0"] != FONT["O"], "zero and O must be visually distinct"
assert set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") <= set(FONT)


def text_width(s, scale):
    """Exact pixel width of a string in this fixed-pitch font."""
    return (len(s) * 6 - 1) * scale


# ---------------------------------------------------------------------------
# Newspaper palette.
# ---------------------------------------------------------------------------

PAPER = (244, 241, 232)
CARD = (255, 253, 247)
INK = (22, 27, 31)
MUTED = (83, 90, 97)
LIGHT_RULE = (207, 203, 191)
RED = (163, 43, 42)
GOLD = (201, 150, 53)
TICKER_BG = (25, 31, 37)
WHITE = (255, 253, 247)
ICON_BG = (232, 234, 228)

DATE_TEXT = "27 NOVEMBER 2026"
DRAWN_STRINGS = []


# ---------------------------------------------------------------------------
# Canvas primitives and hand-rolled PNG encoding.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        run = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(run)] = run

    def border(self, x, y, w, h, color, t=1):
        self.rect(x, y, w, t, color)
        self.rect(x, y + h - t, w, t, color)
        self.rect(x, y, t, h, color)
        self.rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            self.rect(x0 - t // 2, y0 - t // 2, t, t, color)
            return
        for i in range(steps + 1):
            xx = round(x0 + dx * i / steps)
            yy = round(y0 + dy * i / steps)
            self.rect(xx - t // 2, yy - t // 2, t, t, color)

    def poly(self, points, color):
        ys = [p[1] for p in points]
        y0, y1 = max(0, math.ceil(min(ys))), min(self.h, math.floor(max(ys)) + 1)
        for yy in range(y0, y1):
            xs = []
            for i, (ax, ay) in enumerate(points):
                bx, by = points[(i + 1) % len(points)]
                if ay == by:
                    continue
                if min(ay, by) <= yy < max(ay, by):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                left, right = math.ceil(xs[j]), math.floor(xs[j + 1])
                if right > left:
                    self.rect(left, yy, right - left, 1, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, color)

    def ring(self, cx, cy, r, color, t=3):
        lo, hi = (r - t / 2) ** 2, (r + t / 2) ** 2
        for y in range(cy - r - t, cy + r + t + 1):
            for x in range(cx - r - t, cx + r + t + 1):
                d = (x - cx) ** 2 + (y - cy) ** 2
                if lo <= d <= hi:
                    self.set(x, y, color)

    def text(self, s, x, y, scale, color, max_w=None, tag="text"):
        s = s.upper()
        missing = set(s) - set(FONT)
        if missing:
            raise ValueError("unsupported glyphs %r in %r" % (missing, s))
        width = text_width(s, scale)
        if max_w is not None and width > max_w:
            raise ValueError("%s overflow: %d > %d px: %r" % (tag, width, max_w, s))
        if x < 0 or y < 0 or x + width > self.w or y + 7 * scale > self.h:
            raise ValueError("%s outside canvas: %r at (%d,%d)" % (tag, s, x, y))
        for i, ch in enumerate(s):
            glyph = FONT[ch]
            px = x + i * 6 * scale
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(px + col * scale, y + row * scale,
                                  scale, scale, color)
        DRAWN_STRINGS.append(s)

    def center_text(self, s, y, scale, color, x0=0, x1=None, tag="center"):
        if x1 is None:
            x1 = self.w
        width = text_width(s, scale)
        self.text(s, x0 + (x1 - x0 - width) // 2, y, scale, color,
                  max_w=x1 - x0, tag=tag)

    def to_png(self):
        stride = self.w * 3
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)  # filter type: none
            raw.extend(self.buf[y * stride:(y + 1) * stride])

        def chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Copy.  Headlines are <=19 characters; sub-lines are <=30 characters so that
# they fit their measured containers without clipping or manual shortening.
# ---------------------------------------------------------------------------

STORIES = [
    {
        "cat": "MIDEAST / GULF", "color": (151, 57, 46), "icon": "gulf",
        "head": ["DRONE STRIKE KILLS", "TWO ITALIAN TECHS"],
        "sub": [
            "RHEINMETALL STAFF AT SITE",
            "KUWAIT AIR-DEFENCE POST HIT",
            "ITALY, KUWAIT BLAME IRAN",
            "IRAN DENIES, OFFERS A JOINT",
            "INQUIRY; ATTACKS ON KUWAIT",
            "AND BAHRAIN ESCALATE",
        ],
    },
    {
        "cat": "IRAN-US WAR", "color": (96, 47, 51), "icon": "ship",
        "head": ["150 MISSILES FIRED", "TO DEFEND SHIPPING"],
        "sub": [
            "HORMUZ FIGHTING GOES ON",
            "TRUMP, ON THANKSGIVING",
            "CALL TO TROOPS: US GIVES",
            "IRAN 'EVERY OPPORTUNITY'",
            "TO DEAL; DOUBTS TEHRAN",
            "WILL TAKE IT",
        ],
    },
    {
        "cat": "RUSSIA / UKRAINE", "color": (49, 79, 118), "icon": "grid",
        "head": ["RUSSIA READIES NEW", "MASS GRID STRIKE"],
        "sub": [
            "ZELENSKIY WARNS OF A",
            "STRIKE 'IN COMING DAYS'",
            "MISSILES WOUND SEVEN IN",
            "KYIV; SHOPPING CENTRE HIT",
            "DRONES HIT OIL: KRASNODAR",
            "BASHKORTOSTAN, VOLGOGRAD",
        ],
    },
    {
        "cat": "TRUMP / PUTIN", "color": (58, 88, 73), "icon": "talks",
        "head": ["TRUMP URGES PUTIN", "TO PULL BACK"],
        "sub": [
            "CHINA TALKS; RUTTE URGES",
            "END ALL MILITARY AGGRESSION",
            "IN EUROPE; WAR IS A",
            "'COMPLETE BLOODBATH'",
            "KUSHNER: PUTIN PLEDGED NOT",
            "TO USE NUCLEAR WEAPONS",
        ],
    },
    {
        "cat": "MARKETS", "color": (45, 99, 92), "icon": "market",
        "head": ["BRENT TOPS $96", "ASIAN STOCKS RISE"],
        "sub": [
            "AI BUYERS RETURN FOR A",
            "SECOND DAY OF GAINS",
            "HOUTHIS HIT A SAUDI",
            "REFINERY, LIFTING OIL",
            "WALL ST OPENS A SHORT",
            "BLACK FRIDAY SESSION",
        ],
    },
    {
        "cat": "JAPAN ECONOMY", "color": (126, 85, 43), "icon": "bank",
        "head": ["TOKYO PRICES", "CLIMB 2.9%"],
        "sub": [
            "CORE INFLATION AT A",
            "16-MONTH HIGH, CEMENTING",
            "THE CASE FOR A BOJ HIKE",
            "AS SOON AS NEXT MONTH;",
            "POLICY RATE: 1.25%",
        ],
        "sub_dy": 4, "min_gap": 12,
    },
    {
        "cat": "TECH / AI", "color": (72, 66, 116), "icon": "chip",
        "head": ["SAP PLANS AT LEAST", "10,000 JOB CUTS"],
        "sub": [
            "RETOOL FOR THE AI ERA;",
            "TRUMP PROPOSES 20-40% MAX",
            "TARIFFS ON 14 PARTNERS,",
            "INCLUDING CHINA; HUAWEI PREPS",
            "NEW HIGH-BANDWIDTH MEMORY CHIP",
        ],
        "sub_dy": 4, "min_gap": 12,
    },
    {
        "cat": "CLIMATE", "color": (52, 104, 65), "icon": "climate",
        "head": ["UN TALKS DEADLOCKED", "ON FOSSIL FUELS"],
        "sub": [
            "TREATY NEGOTIATORS AT",
            "AN IMPASSE AS A DRAFT",
            "OMITS FOSSIL-FUEL WORDS",
            "EU REFUSES TO ENDORSE",
            "THE TEXT",
        ],
    },
]

TICKER_LINES = [
    "BLACK FRIDAY RUSH  \u00b7  NBA: 11 GAMES TONIGHT",
    "ALTRIA AND JAPAN TOBACCO EYE IMPERIAL BRANDS BID",
    "RUSSIA DIPLOMAT WARNS NUCLEAR RISK  \u00b7  GOLD $3,572",
]

# Each 5x7 glyph drawn at 2x occupies 14 rows.  A 17 px pitch leaves 3 clear
# rows between consecutive ticker lines; the 50 px strip (rows 968..1017)
# keeps one row of padding above the first glyph and below the last one.
TICKER_SCALE = 2
TICKER_GLYPH_H = 7 * TICKER_SCALE            # 14 px
TICKER_CLEAR_ROWS = 3
TICKER_PITCH = TICKER_GLYPH_H + TICKER_CLEAR_ROWS  # 17 px, not 14 or 15
TICKER_STRIP_TOP = 968
TICKER_STRIP_H = 50
TICKER_STRIP_END = TICKER_STRIP_TOP + TICKER_STRIP_H  # exclusive: 1018
TICKER_TOP = TICKER_STRIP_TOP + 1            # 969


# ---------------------------------------------------------------------------
# Flat pictograms, drawn in an 86x86 local box over a pale anchor disc.
# ---------------------------------------------------------------------------

def draw_icon(cv, kind, ox, oy, accent):
    def box(x, y, w, h, c):
        cv.rect(ox + x, oy + y, w, h, c)

    def ln(x0, y0, x1, y1, c, t=2):
        cv.line(ox + x0, oy + y0, ox + x1, oy + y1, c, t)

    def poly(pts, c):
        cv.poly([(ox + x, oy + y) for x, y in pts], c)

    def dot(cx, cy, r, c):
        cv.disc(ox + cx, oy + cy, r, c)

    cv.disc(ox + 43, oy + 43, 41, ICON_BG)

    if kind == "gulf":
        ln(32, 33, 20, 17, INK, 2)
        ln(54, 33, 66, 17, INK, 2)
        ln(32, 37, 20, 50, INK, 2)
        ln(54, 37, 66, 50, INK, 2)
        box(12, 16, 16, 3, INK)
        box(58, 16, 16, 3, INK)
        box(12, 49, 16, 3, INK)
        box(58, 49, 16, 3, INK)
        box(32, 27, 22, 14, INK)
        dot(43, 34, 3, WHITE)
        # Air-defence radar under attack: a burst behind the dish plus an
        # incoming projectile with a pointed nose and swept tail fins.
        poly([(22, 52), (26, 61), (35, 64), (26, 67), (22, 78),
              (18, 67), (9, 64), (18, 61)], RED)
        cv.ring(ox + 22, oy + 64, 9, INK, 2)
        ln(22, 76, 22, 84, INK, 2)
        ln(14, 84, 30, 84, INK, 2)
        poly([(38, 72), (47, 79), (79, 59), (71, 51)], accent)
        poly([(72, 58), (83, 61), (77, 51)], INK)
        poly([(47, 79), (46, 71), (54, 75)], INK)

    elif kind == "ship":
        poly([(0, 10), (16, 10), (11, 60), (0, 60)], MUTED)
        poly([(86, 10), (70, 10), (75, 60), (86, 60)], MUTED)
        poly([(14, 58), (72, 58), (64, 76), (22, 76)], INK)
        box(30, 46, 26, 12, INK)
        box(38, 38, 10, 8, INK)
        ln(43, 38, 43, 18, INK, 2)
        ln(43, 20, 63, 32, RED, 2)
        poly([(66, 34), (73, 38), (62, 41)], RED)
        ln(6, 81, 26, 81, accent, 2)
        ln(30, 81, 50, 81, accent, 2)
        ln(54, 81, 74, 81, accent, 2)

    elif kind == "grid":
        ln(20, 80, 39, 12, INK, 3)
        ln(66, 80, 47, 12, INK, 3)
        ln(24, 62, 62, 62, INK, 3)
        ln(29, 44, 57, 44, INK, 3)
        ln(34, 26, 52, 26, INK, 3)
        ln(2, 26, 34, 26, MUTED, 2)
        ln(52, 26, 84, 26, MUTED, 2)
        poly([(66, 6), (55, 44), (65, 44), (58, 80),
              (82, 38), (71, 38), (79, 6)], GOLD)

    elif kind == "talks":
        dot(24, 22, 10, INK)
        dot(62, 22, 10, accent)
        poly([(4, 72), (10, 42), (38, 42), (44, 72)], INK)
        poly([(42, 72), (48, 42), (76, 42), (82, 72)], accent)
        box(18, 62, 50, 7, INK)
        ln(36, 18, 52, 18, MUTED, 2)
        dot(31, 18, 2, MUTED)
        dot(57, 18, 2, MUTED)
        ln(6, 80, 80, 80, MUTED, 2)

    elif kind == "market":
        ln(8, 76, 80, 76, INK, 3)
        ln(8, 10, 8, 76, INK, 3)
        box(14, 56, 12, 19, accent)
        box(30, 46, 12, 29, accent)
        box(46, 34, 12, 41, accent)
        box(62, 22, 12, 53, accent)
        ln(12, 60, 32, 48, INK, 3)
        ln(32, 48, 52, 36, INK, 3)
        ln(52, 36, 80, 12, INK, 3)
        poly([(80, 6), (86, 20), (72, 16)], INK)

    elif kind == "bank":
        poly([(10, 30), (43, 8), (76, 30)], INK)
        box(8, 30, 70, 6, INK)
        for x in (14, 26, 38, 50, 62):
            box(x, 36, 6, 30, accent)
        box(6, 66, 74, 6, INK)
        ln(78, 68, 84, 22, INK, 3)
        poly([(84, 12), (86, 27), (76, 23)], RED)
        box(72, 24, 10, 3, RED)

    elif kind == "chip":
        cv.border(ox + 20, oy + 16, 48, 52, INK, 3)
        box(30, 26, 28, 32, accent)
        box(37, 33, 14, 18, INK)
        for x in (26, 38, 50, 62):
            box(x, 9, 5, 7, INK)
            box(x, 68, 5, 7, INK)
        for y in (24, 36, 48, 60):
            box(12, y, 8, 5, INK)
            box(68, y, 8, 5, INK)
        ln(4, 28, 12, 28, MUTED, 2)
        ln(4, 28, 4, 58, MUTED, 2)
        ln(4, 58, 12, 58, MUTED, 2)
        ln(76, 38, 84, 38, MUTED, 2)
        ln(84, 38, 84, 12, MUTED, 2)
        dot(4, 58, 2, accent)
        dot(84, 12, 2, accent)

    elif kind == "climate":
        cv.ring(ox + 38, oy + 43, 31, INK, 3)
        ln(38, 12, 38, 74, MUTED, 2)
        ln(7, 43, 69, 43, MUTED, 2)
        poly([(58, 72), (61, 28), (75, 28), (78, 72)], INK)
        dot(64, 20, 5, MUTED)
        dot(72, 12, 5, MUTED)
        dot(80, 6, 4, MUTED)
        ln(48, 80, 86, 24, RED, 3)

    else:
        raise ValueError("unknown icon %r" % kind)


# ---------------------------------------------------------------------------
# Page composition.
# ---------------------------------------------------------------------------

def draw_masthead(cv):
    cv.rect(16, 10, 992, 2, INK)
    cv.rect(16, 14, 992, 1, LIGHT_RULE)
    cv.text("THE WORLD IN ONE PAGE", 16, 16, 2, MUTED,
            max_w=360, tag="mast-kicker-left")
    right = "EIGHT STORIES"
    cv.text(right, 1008 - text_width(right, 2), 16, 2, MUTED,
            max_w=240, tag="mast-kicker-right")

    cv.center_text("WORLD NEWS", 30, 9, INK, 16, 1008, tag="masthead-title")

    cv.rect(16, 100, 992, 46, RED)
    cv.border(16, 100, 992, 46, GOLD, 2)
    cv.center_text(DATE_TEXT, 106, 5, WHITE, 16, 1008, tag="contest-date")
    for cx in (242, 782):
        cv.poly([(cx, 122), (cx + 7, 123), (cx, 125), (cx - 7, 123)], GOLD)

    beats = "WAR  \u00b7  DIPLOMACY  \u00b7  MARKETS  \u00b7  ECONOMY  \u00b7  TECH  \u00b7  CLIMATE"
    cv.center_text(beats, 152, 2, MUTED, 16, 1008, tag="beats")
    cv.rect(16, 170, 992, 2, INK)


def draw_card(cv, story, cx, cy):
    cw, ch = 490, 194
    accent = story["color"]

    cv.rect(cx, cy, cw, ch, CARD)
    cv.border(cx, cy, cw, ch, LIGHT_RULE, 1)
    cv.rect(cx + 1, cy + 1, cw - 2, 26, accent)
    cv.text(story["cat"], cx + 10, cy + 3, 3, WHITE,
            max_w=cw - 20, tag="category")

    for i, line in enumerate(story["head"]):
        cv.text(line, cx + 12, cy + 30 + 30 * i, 4, INK,
                max_w=cw - 24, tag="headline")
    assert 30 + 30 * (len(story["head"]) - 1) + 28 <= 89, "headline collides with rule"
    cv.rect(cx + 12, cy + 91, cw - 24, 1, LIGHT_RULE)

    draw_icon(cv, story["icon"], cx + 12, cy + 96, accent)
    cv.rect(cx + 105, cy + 96, 1, 86, LIGHT_RULE)

    sub_top = 95 + story.get("sub_dy", 0)
    for i, line in enumerate(story["sub"]):
        cv.text(line, cx + 118, cy + sub_top + 16 * i, 2, MUTED,
                max_w=cw - 130, tag="sub-line")
    last_bottom = sub_top + 16 * (len(story["sub"]) - 1) + 14
    min_gap = story.get("min_gap", 5)
    assert ch - last_bottom >= min_gap, "sub-line too close to card bottom"


def draw_ticker(cv):
    line_ys = [TICKER_TOP + TICKER_PITCH * i
               for i in range(len(TICKER_LINES))]
    # Check glyph rows, not just the nominal pitch, so a future edit cannot
    # silently double-print the three lines on top of each other.
    assert TICKER_PITCH - TICKER_GLYPH_H >= TICKER_CLEAR_ROWS, \
        "ticker lines would touch"
    for top, nxt in zip(line_ys, line_ys[1:]):
        assert nxt - (top + TICKER_GLYPH_H) >= TICKER_CLEAR_ROWS, \
            "ticker glyph rows overlap"
    assert line_ys[0] >= TICKER_STRIP_TOP, "ticker line above strip"
    assert line_ys[-1] + TICKER_GLYPH_H <= TICKER_STRIP_END - 1, \
        "ticker line clipped at strip"

    cv.rect(16, TICKER_STRIP_TOP, 992, TICKER_STRIP_H, TICKER_BG)
    cv.rect(16, TICKER_STRIP_TOP, 78, TICKER_STRIP_H, RED)
    # Align the label with the middle line of the three.
    cv.text("LATEST", 20, line_ys[len(line_ys) // 2], TICKER_SCALE, WHITE,
            max_w=74, tag="ticker-label")
    cv.rect(96, TICKER_STRIP_TOP + 4, 2, TICKER_STRIP_H - 10, GOLD)
    for line, ty in zip(TICKER_LINES, line_ys):
        cv.text(line, 106, ty, TICKER_SCALE, WHITE,
                max_w=1024 - 16 - 106, tag="ticker-line")


def sweep_dates():
    """Only the single masthead date may contain a month name or a year."""
    forbidden = (r"JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|"
                 r"SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|20\d\d")
    for s in DRAWN_STRINGS:
        if s != DATE_TEXT and re.search(forbidden, s):
            raise ValueError("unexpected date-like text: %r" % s)


def render():
    DRAWN_STRINGS.clear()
    cv = Canvas(WIDTH, HEIGHT)
    cv.rect(0, 0, WIDTH, HEIGHT, PAPER)
    draw_masthead(cv)
    for idx, story in enumerate(STORIES):
        col, row = idx % 2, idx // 2
        draw_card(cv, story, 16 + col * 502, 178 + row * 198)
    draw_ticker(cv)
    sweep_dates()

    png = cv.to_png()
    if len(png) > 1024 * 1024:
        raise ValueError("PNG exceeds 1 MiB: %d bytes" % len(png))
    if WIDTH > 1024 or HEIGHT > 1024:
        raise ValueError("PNG dimensions exceed 1024x1024")

    out_dir = os.environ.get("OUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as fh:
        fh.write(png)
    return out_path, len(png)


if __name__ == "__main__":
    path, size = render()
    print("wrote %s (%d bytes)" % (path, size))
