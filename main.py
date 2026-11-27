#!/usr/bin/env python3
"""Front page of 27 November 2026 - deterministic, stdlib-only PNG renderer.

No network, no randomness, no timestamps. Output: $OUT_DIR/entry.png
"""

import os
import re
import struct
import zlib

# ---------------------------------------------------------------------------
# Embedded 5x7 bitmap font.  Uppercase only, monospace with a one-column gap.
# The zero is slashed so it can never be confused with the letter O.
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
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
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
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "\u00b7": ("00000", "00000", "00000", "00110", "00000", "00000", "00000"),
}

# ASCII dot acts as the middle dot used in the ticker.
FONT["\u00b7"] = FONT["\u00b7"]


def text_width(s, scale):
    """Pixel width of a string in the 5x7 font at the given integer scale."""
    return (len(s) * 6 - 1) * scale


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

PAPER = (245, 242, 233)
CARD = (255, 253, 247)
INK = (24, 28, 32)
MUTED = (85, 92, 99)
RULE = (58, 64, 68)
LIGHT_RULE = (206, 202, 190)
RED = (166, 40, 40)
GOLD = (203, 151, 55)
TICKER_BG = (26, 32, 38)
WHITE = (255, 253, 247)
ICON_BG = (232, 234, 228)

DATE_TEXT = "27 NOVEMBER 2026"
DRAWN_STRINGS = []


# ---------------------------------------------------------------------------
# Canvas primitives
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
        y0 = max(0, int(min(ys)))
        y1 = min(self.h, int(max(ys)) + 1)
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
                left = int(-(-xs[j] // 1))   # ceil
                right = int(xs[j + 1] // 1)  # floor
                if right > left:
                    self.rect(left, yy, right - left, 1, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, color)

    def ring(self, cx, cy, r, color, t=2):
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
            raise ValueError("%s outside canvas: %r at (%d,%d) w=%d" % (tag, s, x, y, width))
        for i, ch in enumerate(s):
            glyph = FONT[ch]
            px = x + i * 6 * scale
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(px + col * scale, y + row * scale, scale, scale, color)
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
            raw.append(0)
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
# Story copy.  Every line is preselected to fit its measured container.
# ---------------------------------------------------------------------------

STORIES = [
    {
        "cat": "MIDEAST / GULF", "color": (151, 57, 46), "icon": "gulf",
        "head": ["DRONE STRIKE KILLS TWO", "ITALIAN TECHNICIANS"],
        "sub": ["KUWAIT AIR-DEFENCE SITE HIT", "ITALY, KUWAIT BLAME IRAN",
                "IRAN DENIES, OFFERS A JOINT", "INQUIRY; ATTACKS ON KUWAIT",
                "AND BAHRAIN ESCALATE"],
    },
    {
        "cat": "IRAN-US WAR", "color": (96, 47, 51), "icon": "ship",
        "head": ["150 MISSILES FIRED", "DEFEND COMMERCIAL SHIPS"],
        "sub": ["HORMUZ FIGHTING CONTINUES", "TRUMP, ON THANKSGIVING CALL,",
                "TELLS TROOPS: US GIVES IRAN", "'EVERY OPPORTUNITY' TO DEAL;",
                "DOUBTS TEHRAN WILL TAKE IT"],
    },
    {
        "cat": "RUSSIA / UKRAINE", "color": (51, 80, 118), "icon": "grid",
        "head": ["RUSSIA READIES NEW", "MASS GRID STRIKE"],
        "sub": ["ZELENSKIY WARNS OF AN", "ATTACK 'IN THE COMING DAYS'",
                "MISSILES WOUND SEVEN IN KYIV", "AND HIT A SHOPPING CENTRE;",
                "DRONES STRIKE RUSSIAN OIL", "SITES IN THREE REGIONS"],
    },
    {
        "cat": "TRUMP / PUTIN", "color": (58, 88, 73), "icon": "talks",
        "head": ["TRUMP URGES PUTIN TO", "PULL BACK AGGRESSION"],
        "sub": ["ACROSS EUROPE, AFTER TALKS", "IN CHINA; WAR IS A 'COMPLETE",
                "BLOODBATH'. KUSHNER SAYS", "PUTIN PLEDGED NOT TO USE",
                "NUCLEAR WEAPONS; TRUMP AND", "RUTTE URGE NO WAR EXPANSION"],
    },
    {
        "cat": "MARKETS", "color": (47, 100, 93), "icon": "market",
        "head": ["ASIAN STOCKS RISE AGAIN", "BRENT CRUDE TOPS $96"],
        "sub": ["BUYERS RETURN TO AI NAMES", "FOR A SECOND DAY; HOUTHIS",
                "STRIKE A SAUDI REFINERY,", "SENDING OIL HIGHER;",
                "WALL ST. OPENS A SHORTENED", "BLACK FRIDAY SESSION"],
    },
    {
        "cat": "JAPAN ECONOMY", "color": (127, 85, 43), "icon": "bank",
        "head": ["TOKYO INFLATION HITS", "16-MONTH HIGH: 2.9%"],
        "sub": ["CORE PRICES ACCELERATE TO", "A 16-MONTH HIGH, CEMENTING",
                "THE CASE FOR A BOJ HIKE AS", "EARLY AS NEXT MONTH; POLICY",
                "RATE STANDS AT 1.25%"],
    },
    {
        "cat": "TECH / AI", "color": (72, 66, 116), "icon": "chip",
        "head": ["SAP TO CUT AT LEAST", "10,000 JOBS FOR AI"],
        "sub": ["TRUMP PROPOSES MAX TARIFFS", "OF 20-40% ON 14 MAJOR",
                "TRADING PARTNERS, WITH", "CHINA; HUAWEI PREPS A NEW",
                "HIGH-BANDWIDTH MEMORY CHIP"],
    },
    {
        "cat": "CLIMATE", "color": (52, 104, 65), "icon": "climate",
        "head": ["UN TALKS DEADLOCKED", "ON FOSSIL FUELS"],
        "sub": ["AT UN TREATY TALKS, A DRAFT", "OMITS FOSSIL-FUEL LANGUAGE;",
                "NEGOTIATORS ARE AT AN", "IMPASSE AND THE EU REFUSES",
                "TO ENDORSE THE TEXT"],
    },
]

TICKER_LINES = [
    "BLACK FRIDAY RUSH  \u00b7  NBA: 11 GAMES TONIGHT",
    "ALTRIA AND JAPAN TOBACCO EYE IMPERIAL BRANDS BID",
    "RUSSIA DIPLOMAT WARNS NUCLEAR RISK  \u00b7  GOLD $3,572",
]


# ---------------------------------------------------------------------------
# Pictograms: flat shapes drawn in local coordinates (0..92, 0..84).
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

    # Pale disc keeps each pictogram anchored and fills the icon area.
    cv.disc(ox + 46, oy + 42, 41, ICON_BG)

    if kind == "gulf":
        # Reconnaissance drone above, incoming missile and impact below.
        ln(46, 24, 22, 12, INK, 3)
        ln(46, 24, 70, 12, INK, 3)
        ln(46, 24, 22, 38, INK, 3)
        ln(46, 24, 70, 38, INK, 3)
        box(35, 17, 22, 14, INK)
        box(14, 9, 16, 3, INK)
        box(62, 9, 16, 3, INK)
        box(14, 38, 16, 3, INK)
        box(62, 38, 16, 3, INK)
        dot(46, 31, 3, WHITE)
        poly([(70, 47), (77, 50), (61, 72), (56, 64)], accent)
        poly([(56, 64), (61, 72), (49, 71), (52, 65)], INK)
        ln(46, 70, 37, 78, RED, 3)
        ln(60, 56, 69, 51, RED, 3)
        box(43, 76, 7, 3, RED)

    elif kind == "ship":
        # Two shorelines frame a strait; a missile crosses above a warship.
        poly([(0, 8), (11, 8), (8, 60), (0, 60)], MUTED)
        poly([(92, 8), (81, 8), (84, 60), (92, 60)], MUTED)
        poly([(17, 58), (75, 58), (67, 74), (25, 74)], INK)
        box(31, 47, 30, 11, INK)
        ln(46, 47, 46, 21, INK, 3)
        ln(46, 23, 58, 31, accent, 3)
        poly([(82, 16), (86, 29), (73, 22)], RED)
        ln(78, 24, 57, 39, RED, 2)
        ln(14, 79, 30, 79, accent, 2)
        ln(34, 79, 50, 79, accent, 2)
        ln(54, 79, 70, 79, accent, 2)
        ln(74, 79, 90, 79, accent, 2)

    elif kind == "grid":
        # Transmission pylon with a lightning strike on the power grid.
        ln(26, 80, 41, 14, INK, 3)
        ln(62, 80, 47, 14, INK, 3)
        ln(32, 56, 56, 56, INK, 3)
        ln(28, 40, 60, 40, INK, 3)
        ln(36, 25, 52, 25, INK, 3)
        ln(30, 66, 58, 66, accent, 3)
        ln(2, 25, 36, 25, MUTED, 2)
        ln(52, 25, 90, 25, MUTED, 2)
        poly([(66, 8), (57, 43), (66, 43), (59, 80),
              (80, 38), (70, 38), (77, 8)], GOLD)

    elif kind == "talks":
        # Two delegations facing each other across a table.
        dot(27, 25, 10, INK)
        dot(65, 25, 10, accent)
        poly([(6, 72), (13, 43), (35, 43), (43, 72)], INK)
        poly([(48, 72), (56, 43), (78, 43), (86, 72)], accent)
        box(32, 62, 28, 6, INK)
        ln(35, 20, 58, 20, MUTED, 2)
        dot(34, 20, 2, MUTED)
        dot(59, 20, 2, MUTED)
        ln(18, 79, 74, 79, MUTED, 2)

    elif kind == "market":
        # Rising bars and an unmistakable up-arrow.
        ln(8, 76, 88, 76, INK, 3)
        box(12, 54, 14, 21, accent)
        box(32, 43, 14, 32, accent)
        box(52, 31, 14, 44, accent)
        box(72, 19, 14, 56, accent)
        ln(10, 58, 33, 46, INK, 3)
        ln(33, 46, 55, 34, INK, 3)
        ln(55, 34, 84, 10, INK, 3)
        poly([(84, 4), (92, 18), (76, 15)], INK)

    elif kind == "bank":
        # Central bank facade and an upward policy arrow.
        poly([(14, 31), (42, 10), (70, 31)], INK)
        box(12, 31, 60, 6, INK)
        for x in (17, 29, 41, 53, 65):
            box(x, 37, 5, 30, accent)
        box(10, 67, 64, 6, INK)
        ln(78, 70, 88, 20, INK, 3)
        poly([(88, 12), (93, 28), (80, 24)], RED)
        box(75, 26, 10, 3, RED)

    elif kind == "chip":
        # Processor with pins and circuit traces.
        cv.border(ox + 24, oy + 18, 46, 48, INK, 3)
        box(34, 28, 26, 28, accent)
        box(40, 34, 14, 16, INK)
        for x in (30, 42, 54, 66):
            box(x, 12, 5, 6, INK)
            box(x, 66, 5, 6, INK)
        for y in (26, 38, 50, 62):
            box(16, y, 8, 5, INK)
            box(70, y, 8, 5, INK)
        ln(8, 28, 16, 28, MUTED, 2)
        ln(8, 28, 8, 56, MUTED, 2)
        ln(8, 56, 16, 56, MUTED, 2)
        ln(78, 38, 86, 38, MUTED, 2)
        ln(86, 38, 86, 14, MUTED, 2)
        dot(8, 56, 2, accent)
        dot(86, 14, 2, accent)

    elif kind == "climate":
        # Globe, smokestack and the red slash of a deadlocked draft.
        cv.ring(ox + 41, oy + 45, 32, INK, 3)
        ln(41, 13, 41, 77, MUTED, 2)
        ln(9, 45, 73, 45, MUTED, 2)
        poly([(64, 72), (67, 30), (79, 30), (82, 72)], INK)
        dot(70, 22, 5, MUTED)
        dot(78, 14, 6, MUTED)
        dot(88, 8, 4, MUTED)
        ln(57, 80, 91, 26, RED, 3)


# ---------------------------------------------------------------------------
# Page composition
# ---------------------------------------------------------------------------

def draw_masthead(cv):
    cv.rect(18, 10, 988, 2, INK)
    cv.text("GLOBAL EDITION", 18, 15, 2, MUTED, max_w=300, tag="mast-kicker-l")
    right = "EIGHT STORIES"
    cv.text(right, 1006 - text_width(right, 2), 15, 2, MUTED,
            max_w=300, tag="mast-kicker-r")
    cv.center_text("WORLD NEWS", 34, 9, INK, tag="masthead-title")

    cv.rect(18, 104, 988, 46, RED)
    cv.rect(21, 107, 982, 40, RED)
    cv.border(18, 104, 988, 46, GOLD, 2)
    cv.center_text(DATE_TEXT, 109, 5, WHITE, tag="contest-date")
    for cx in (247, 777):
        cv.poly([(cx, 121), (cx + 6, 127), (cx, 133), (cx - 6, 127)], GOLD)
    cv.center_text("WAR  \u00b7  DIPLOMACY  \u00b7  MARKETS  \u00b7  ECONOMY  \u00b7  TECH  \u00b7  CLIMATE",
                   157, 2, MUTED, x0=18, x1=1006, tag="beats")


def draw_card(cv, story, cx, cy):
    cw, ch = 488, 176
    accent = story["color"]
    cv.rect(cx, cy, cw, ch, CARD)
    cv.border(cx, cy, cw, ch, LIGHT_RULE, 1)
    cv.rect(cx + 1, cy + 1, cw - 2, 23, accent)
    cv.text(story["cat"], cx + 11, cy + 5, 2, WHITE,
            max_w=cw - 22, tag="card-category")

    for i, line in enumerate(story["head"]):
        cv.text(line, cx + 14, cy + 30 + 24 * i, 3, INK,
                max_w=cw - 28, tag="card-headline")
    cv.rect(cx + 12, cy + 77, cw - 24, 1, LIGHT_RULE)

    draw_icon(cv, story["icon"], cx + 14, cy + 82, accent)
    for i, line in enumerate(story["sub"]):
        cv.text(line, cx + 120, cy + 82 + 15 * i, 2, MUTED,
                max_w=cw - 132, tag="card-sub")


def draw_ticker(cv):
    cv.rect(18, 924, 988, 82, TICKER_BG)
    cv.rect(18, 932, 80, 66, RED)
    cv.text("LATEST", 23, 958, 2, WHITE, max_w=70, tag="ticker-label")
    cv.rect(104, 932, 2, 66, GOLD)
    for i, line in enumerate(TICKER_LINES):
        cv.text(line, 112, 934 + 24 * i, 2, WHITE,
                max_w=882, tag="ticker-line")


def render():
    cv = Canvas(1024, 1024)
    cv.rect(0, 0, 1024, 1024, PAPER)
    draw_masthead(cv)
    for idx, story in enumerate(STORIES):
        col, row = idx % 2, idx // 2
        draw_card(cv, story, 18 + col * 500, 180 + row * 186)
    draw_ticker(cv)

    # Date sweep: the only month or year in the entire image is the masthead.
    for s in DRAWN_STRINGS:
        if s != DATE_TEXT and re.search(r"NOVEMBER|DECEMBER|20\d\d|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER", s):
            raise ValueError("unexpected date-like text: %r" % s)

    png = cv.to_png()
    if len(png) > 1024 * 1024:
        raise ValueError("PNG exceeds 1 MiB")
    out_dir = os.environ.get("OUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as fh:
        fh.write(png)
    return out_path, len(png)


if __name__ == "__main__":
    path, size = render()
    print("wrote %s (%d bytes)" % (path, size))
