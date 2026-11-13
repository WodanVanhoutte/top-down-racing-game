"""
ma_trucks.py  -  de monstertrucks van MONSTER ARENA
Elke truck wordt volledig getekend met code, 4x te groot en daarna verkleind (= gladde randen).
Per truck maken we 5 aanzichten: bovenkant, onderkant, zijkant, voorkant en achterkant.
Tijdens een flip of barrel roll plakt TruckArt.proj() die aanzichten aan elkaar,
zodat je de truck echt ziet kantelen.
"""
import math
import random

import pygame

from ma_core import clamp, dark, dim, font, lite, mix

TL, TW, TH = 160, 116, 80          # lengte, breedte en hoogte van een truck (px in het spel)
AX = 42                            # afstand van het midden tot een as
TY = 44                            # afstand van het midden tot het midden van een band

BODIES = ["PICKUP", "MUSCLE", "SUV", "BUGGY", "HOT ROD"]
PAINTS = [("ROOD", (214, 36, 36)), ("ORANJE", (245, 126, 24)), ("GEEL", (246, 204, 36)), ("LIME", (150, 214, 40)),
          ("GROEN", (36, 150, 70)), ("TEAL", (26, 170, 160)), ("HEMEL", (70, 180, 240)), ("BLAUW", (40, 96, 220)),
          ("PAARS", (130, 64, 210)), ("ROZE", (240, 84, 170)), ("WIT", (236, 236, 240)), ("ZWART", (44, 46, 54)),
          ("ZILVER", (168, 176, 190)), ("BRONS", (150, 96, 50))]
ACCENTS = [("WIT", (245, 245, 245)), ("ZWART", (22, 22, 26)), ("GEEL", (255, 214, 40)), ("ROOD", (230, 40, 36)),
           ("BLAUW", (50, 120, 240)), ("ORANJE", (255, 140, 30)), ("GROEN", (60, 200, 80)), ("CHROOM", (190, 198, 212)),
           ("ROZE", (255, 100, 190)), ("CYAAN", (70, 230, 250))]
DECALS = ["GEEN", "VLAMMEN", "RACESTREPEN", "GEBLOKT", "BLIKSEM", "TIJGER", "HAAI", "SLIJM", "SCHEDEL", "CAMO",
          "TWEEKLEUR", "STERREN"]
WHEELS = ["GROOT", "ENORM", "GIGANTISCH"]
EXTRAS = ["GEEN", "LICHTBALK", "HAAIENVIN", "HOORNS", "STEKELS", "VLAGGEN", "SPOILER"]
STATS = ["TOPSNELHEID", "VERING (SPRONG)", "FLIP-SNELHEID", "NITRO"]

# kant-en-klare skins: (naam, body, lak, accent, sticker, wielen, extra, stats)
PRESETS = [
    ("INFERNO", 0, 11, 5, 1, 1, 1, [6, 6, 5, 6]),
    ("MEGA SHARK", 2, 7, 0, 6, 2, 2, [5, 7, 5, 5]),
    ("EL TORO", 1, 0, 0, 2, 1, 3, [8, 5, 5, 5]),
    ("TIGER CLAW", 0, 1, 1, 5, 2, 0, [6, 7, 6, 4]),
    ("TOXIC", 3, 3, 8, 7, 0, 6, [6, 5, 8, 5]),
    ("THUNDER", 4, 7, 2, 4, 1, 0, [7, 5, 6, 6]),
    ("BONE SHAKER", 2, 11, 8, 8, 2, 4, [5, 6, 7, 6]),
    ("SHERIFF", 2, 10, 1, 10, 1, 1, [6, 6, 6, 6]),
    ("STUNT STAR", 0, 7, 0, 11, 1, 5, [5, 6, 8, 5]),
    ("CAMO KING", 2, 4, 1, 9, 2, 0, [4, 9, 5, 5]),
    ("SPEED DEMON", 1, 2, 1, 2, 0, 6, [9, 4, 5, 6]),
    ("PINK PANIC", 3, 9, 0, 3, 0, 5, [6, 5, 7, 6]),
]

GLASS, GLASS_HI = (26, 38, 58), (120, 170, 220)
CHROME, CHROME_D, CHROME_L = (176, 184, 198), (92, 98, 112), (238, 242, 250)


def preset_cfg(i):
    n, body, paint, accent, decal, wheels, extra, stats = PRESETS[i % len(PRESETS)]
    return dict(body=body, paint=paint, accent=accent, decal=decal, wheels=wheels, extra=extra, stats=list(stats))


def truck_params(cfg):
    """Vertaal de instellingen van een truck naar rij-eigenschappen."""
    s, v, f, n = cfg["stats"]
    w = cfg["wheels"]
    return dict(vmax=330 + 24 * s + 10 * w, accel=340.0, nitro=60 + 8 * n, hop=380 + 32 * v + 22 * w, flip=6.0 + 0.45 * f)


class Pen:
    """Tekenblad met het nulpunt in het midden; alle maten zijn in 'spel-pixels' en worden K keer vergroot."""

    def __init__(self, w, h, K):
        self.K, self.w, self.h = K, w, h
        self.s = pygame.Surface((w * K, h * K), pygame.SRCALPHA)

    def pt(self, x, y):
        return ((self.w / 2 + x) * self.K, (self.h / 2 + y) * self.K)

    def rect(self, col, x0, y0, x1, y1, r=0.0, width=0.0):
        a, b = self.pt(min(x0, x1), min(y0, y1)), self.pt(max(x0, x1), max(y0, y1))
        pygame.draw.rect(self.s, col, (a[0], a[1], b[0] - a[0], b[1] - a[1]), int(width * self.K), border_radius=int(r * self.K))

    def poly(self, col, pts, width=0.0):
        pygame.draw.polygon(self.s, col, [self.pt(x, y) for x, y in pts], int(width * self.K))

    def circle(self, col, x, y, r, width=0.0):
        pygame.draw.circle(self.s, col, self.pt(x, y), r * self.K, int(width * self.K))

    def line(self, col, a, b, width=1.0):
        pygame.draw.line(self.s, col, self.pt(*a), self.pt(*b), max(1, int(width * self.K)))

    def lines(self, col, pts, width=1.0):
        pygame.draw.lines(self.s, col, False, [self.pt(x, y) for x, y in pts], max(1, int(width * self.K)))

    def tube(self, col, a, b, width):
        """Buis met ronde uiteinden en een lichtstreepje."""
        self.line(dark(col, 0.45), a, b, width + 1.2)
        self.line(col, a, b, width)
        self.line(lite(col, 0.5), a, b, width * 0.3)
        for q in (a, b):
            self.circle(col, q[0], q[1], width / 2)

    def both(self, fn):
        """Voert fn(zijde) uit voor de linker- en de rechterkant (zijde = -1 of 1)."""
        for sd in (-1, 1):
            fn(sd)


# ------------------------------------------------------------------ banden
def tire_size(cfg):
    return (50, 56, 62)[cfg["wheels"]], (25, 27, 30)[cfg["wheels"]]


def tire_top(p, x, y, L, Wd):
    """Band van bovenaf: je kijkt op het profiel. Lichter in het midden = rond."""
    p.rect((12, 12, 14), x - L / 2 - 1, y - Wd / 2 - 1, x + L / 2 + 1, y + Wd / 2 + 1, L * 0.3)
    p.rect((30, 30, 34), x - L / 2, y - Wd / 2, x + L / 2, y + Wd / 2, L * 0.29)
    n = int(L // 6)
    for k in range(n):
        lx = x - L / 2 + 4 + k * (L - 12) / (n - 1)
        sh = math.cos((lx - x) / (L / 2) * 1.35) ** 0.8
        col = mix((40, 40, 44), (104, 104, 112), clamp(sh, 0, 1))
        for sd in (-1, 1):                                   # V-vormige noppen
            p.poly(col, [(lx - 3.2, y + sd * (Wd / 2 - 1)), (lx - 0.4, y + sd * (Wd / 2 - 1)), (lx + 3.4, y + sd * 0.8), (lx + 0.6, y + sd * 0.8)])
    for sd in (-1, 1):                                       # zijwand
        p.rect((18, 18, 21), x - L / 2 + 5, y + sd * (Wd / 2 - 2.2), x + L / 2 - 5, y + sd * (Wd / 2 - 0.2), 1)


def tire_side(p, x, y, R, accent):
    """Wiel van opzij: band met noppen, velg in de accentkleur."""
    for k in range(18):
        a = math.tau * k / 18
        p.poly((20, 20, 23), [(x + math.cos(a + d) * (R + e), y + math.sin(a + d) * (R + e)) for d, e in ((-0.1, 0), (-0.07, 2.2), (0.07, 2.2), (0.1, 0))])
    p.circle((24, 24, 27), x, y, R)
    p.circle((44, 44, 49), x, y, R * 0.86)
    p.circle((28, 28, 32), x, y, R * 0.72)
    p.circle(CHROME_D, x, y, R * 0.56)
    p.circle(accent, x, y, R * 0.5)
    p.circle(dark(accent, 0.35), x, y, R * 0.5, 1.2)
    for k in range(5):
        a = math.tau * k / 5 - 0.3
        p.line(dark(accent, 0.55), (x, y), (x + math.cos(a) * R * 0.46, y + math.sin(a) * R * 0.46), 2.6)
    p.circle(CHROME, x, y, R * 0.16)
    p.circle(CHROME_L, x - R * 0.04, y - R * 0.04, R * 0.07)


def tire_front(p, x, y0, y1, Wd):
    """Band van voren: een rechthoek met dwarse noppen."""
    p.rect((14, 14, 16), x - Wd / 2 - 1, y0 - 1, x + Wd / 2 + 1, y1 + 1, 5)
    p.rect((34, 34, 38), x - Wd / 2, y0, x + Wd / 2, y1, 4.5)
    n = int((y1 - y0) // 6)
    for k in range(n):
        yy = y0 + 3 + k * (y1 - y0 - 6) / max(1, n - 1)
        sh = math.cos((yy - (y0 + y1) / 2) / ((y1 - y0) / 2) * 1.3)
        col = mix((44, 44, 48), (100, 100, 108), clamp(sh, 0, 1))
        for sd in (-1, 1):
            p.poly(col, [(x + sd * (Wd / 2 - 1), yy - 2.6), (x + sd * (Wd / 2 - 1), yy), (x + sd * 0.8, yy + 2.6), (x + sd * 0.8, yy)])


# ------------------------------------------------------------------ stickers (worden op de lak getekend)
def star(p, col, x, y, r):
    p.poly(col, [(x + math.cos(-math.pi / 2 + k * math.pi / 5) * (r if k % 2 == 0 else r * 0.42),
                  y + math.sin(-math.pi / 2 + k * math.pi / 5) * (r if k % 2 == 0 else r * 0.42)) for k in range(10)])


def decal(p, kind, paint, acc, hw, x0, x1):
    """Sticker op de carrosserie. hw = halve breedte, x0..x1 = van achter tot neus."""
    if kind == 1:                                            # vlammen vanaf de neus naar achter
        hot = mix(acc, (255, 244, 130), 0.7)
        for col, reach, wide in ((dark(acc, 0.35), 1.0, 1.0), (acc, 0.84, 0.74), (hot, 0.58, 0.42)):
            p.rect(col, x1 - 9 - 9 * reach, -hw - 2, x1 + 4, hw + 2)
            for k, (yy, ln) in enumerate(((-0.84, 58), (-0.5, 40), (-0.17, 70), (0.17, 46), (0.5, 76), (0.84, 52))):
                up, lo = [], []
                for i in range(9):
                    t = i / 8
                    x = x1 - 14 - (ln * reach + 6) * t
                    y = yy * hw + math.sin(t * 5.5 + k * 1.7) * 3.0 * t
                    w = hw * 0.25 * wide * (1 - t) ** 0.75 + 0.2
                    up.append((x, y - w))
                    lo.append((x, y + w))
                p.poly(col, up + lo[::-1])
    elif kind == 2:                                          # twee racestrepen
        for sd in (-1, 1):
            p.rect(dark(acc, 0.5), x0 - 4, sd * 2.2, x1 + 4, sd * 11.8)
            p.rect(acc, x0 - 4, sd * 3, x1 + 4, sd * 11)
    elif kind == 3:                                          # geblokte flanken en neus
        for sd in (-1, 1):
            for k in range(int((x1 - x0) // 6) + 2):
                for r in range(2):
                    col = (240, 240, 240) if (k + r) % 2 == 0 else (18, 18, 22)
                    p.rect(col, x0 + k * 6, sd * (hw - 12 + r * 6), x0 + k * 6 + 6, sd * (hw - 6 + r * 6))
        for k in range(int(2 * hw // 6) + 1):
            for r in range(2):
                col = (240, 240, 240) if (k + r) % 2 == 0 else (18, 18, 22)
                p.rect(col, x1 - 12 + r * 6, -hw + k * 6, x1 - 6 + r * 6, -hw + k * 6 + 6)
        p.rect(acc, x0 - 2, -hw + 12, x1 - 12, -hw + 14)
        p.rect(acc, x0 - 2, hw - 14, x1 - 12, hw - 12)
    elif kind == 4:                                          # bliksem
        bolt = [(1.0, -0.2), (0.62, 0.42), (0.7, 0.05), (0.3, 0.6), (0.4, 0.15), (-0.1, 0.8), (0.12, 0.2), (0.02, 0.2),
                (0.36, -0.3), (0.26, -0.3), (0.62, -0.75), (0.54, -0.25)]
        L = x1 - x0
        for col, g in ((dark(acc, 0.55), 1.12), (acc, 1.0), (lite(acc, 0.7), 0.5)):
            for sd in (-1, 1):
                p.poly(col, [(x0 + L * 0.42 + bx * L * 0.56, sd * (hw * 0.56 + by * hw * 0.42 * g)) for bx, by in bolt])
    elif kind == 5:                                          # tijgerstrepen
        n = int((x1 - x0) // 13)
        for k in range(n):
            x = x0 + 8 + k * 13
            for sd in (-1, 1):
                ln = hw * (0.95 if k % 2 == 0 else 0.6)
                p.poly(acc, [(x - 4, sd * (hw + 2)), (x + 4, sd * (hw + 2)), (x + 6, sd * (hw - ln * 0.5)), (x + 1 + (k % 3) * 2, sd * (hw - ln)),
                             (x - 1, sd * (hw - ln * 0.45))])
        p.poly(acc, [(x1 - 2, -3), (x1 - 16, 0), (x1 - 2, 3)])
    elif kind == 6:                                          # haaienbek: tanden, ogen en kieuwen
        p.rect(lite(paint, 0.75), x0 - 4, hw * 0.55, x1 + 4, hw + 3)
        p.rect(lite(paint, 0.75), x0 - 4, -hw - 3, x1 + 4, -hw * 0.55)
        p.rect((120, 14, 20), x1 - 15, -hw - 2, x1 + 4, hw + 2)
        for k in range(int(2 * hw // 6) + 2):
            y = -hw - 2 + k * 6
            p.poly((250, 250, 250), [(x1 - 15, y), (x1 - 15, y + 6), (x1 - 6, y + 3)])
            p.poly((250, 250, 250), [(x1 + 3, y - 3), (x1 + 3, y + 3), (x1 - 4, y)])
        for sd in (-1, 1):
            p.circle((250, 250, 250), x1 - 26, sd * hw * 0.5, 5.2)
            p.circle((10, 10, 12), x1 - 24.6, sd * hw * 0.5, 2.8)
            for k in range(3):
                p.line(dark(paint, 0.5), (x1 - 44 - k * 6, sd * (hw * 0.25)), (x1 - 48 - k * 6, sd * (hw * 0.86)), 1.8)
    elif kind == 7:                                          # slijm dat van voor naar achter druipt
        rnd = random.Random(5)
        p.rect(acc, x1 - 22, -hw - 2, x1 + 4, hw + 2)
        for k in range(9):
            y = -hw + (k + 0.5) * 2 * hw / 9
            ln = rnd.uniform(14, 62)
            w = rnd.uniform(2.6, 4.6)
            p.rect(acc, x1 - 22 - ln, y - w, x1 - 18, y + w, w)
            p.circle(acc, x1 - 22 - ln - rnd.uniform(5, 10), y, w * 0.7)
            p.circle(lite(acc, 0.6), x1 - 26, y - w * 0.3, 1.2)
        for k in range(7):
            p.circle(acc, rnd.uniform(x0, x1 - 60), rnd.uniform(-hw, hw), rnd.uniform(1.5, 4))
    elif kind == 8:                                          # botten op de flanken (de schedel komt er later bovenop)
        for sd in (-1, 1):
            for k in range(int((x1 - x0 - 16) // 15)):
                x = x0 + 8 + k * 15
                p.line((238, 234, 220), (x, sd * (hw - 3)), (x + 9, sd * (hw - 8)), 2.2)
                p.circle((238, 234, 220), x, sd * (hw - 3), 1.8)
                p.circle((238, 234, 220), x + 9, sd * (hw - 8), 1.8)
    elif kind == 9:                                          # camouflage
        rnd = random.Random(9)
        for col in (dark(paint, 0.45), mix(paint, acc, 0.55), lite(paint, 0.28)):
            for _ in range(11):
                x, y = rnd.uniform(x0, x1), rnd.uniform(-hw, hw)
                for _k in range(4):
                    p.circle(col, x + rnd.uniform(-7, 7), y + rnd.uniform(-5, 5), rnd.uniform(3.5, 7.5))
    elif kind == 10:                                         # twee kleuren met een schuine scheiding
        p.poly(acc, [(x0 - 6, -hw - 3), (4, -hw - 3), (-18, hw + 3), (x0 - 6, hw + 3)])
        p.poly(lite(acc, 0.5) if sum(acc) < 200 else dark(acc, 0.5), [(4, -hw - 3), (8, -hw - 3), (-14, hw + 3), (-18, hw + 3)])
        p.poly(lite(paint, 0.6), [(12, -hw - 3), (14, -hw - 3), (-8, hw + 3), (-10, hw + 3)])
    elif kind == 11:                                         # sterren en strepen
        p.rect(dark(paint, 0.45), x0 - 4, -hw - 3, -6, hw + 3)
        for i, (sx, sy) in enumerate(((-16, -0.6), (-16, 0.6), (-30, 0), (-44, -0.6), (-44, 0.6), (-30, -0.95), (-30, 0.95))):
            if x0 < sx - 4:
                star(p, acc, sx, sy * hw * 0.8, 5.2)
        for k in range(5):
            y = -hw + (k + 0.5) * 2 * hw / 5
            p.rect(acc if k % 2 == 0 else (214, 40, 44), -4, y - hw / 5, x1 + 4, y + hw / 5)


# ------------------------------------------------------------------ bovenaanzicht
def glass(p, pts):
    p.poly((8, 12, 20), pts)
    cx = sum(q[0] for q in pts) / len(pts)
    cy = sum(q[1] for q in pts) / len(pts)
    inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.93) for x, y in pts]
    p.poly(GLASS, inner)
    x0, x1 = min(q[0] for q in inner), max(q[0] for q in inner)
    y0, y1 = min(q[1] for q in inner), max(q[1] for q in inner)
    p.poly(GLASS_HI, [(x0 + (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.12), (x0 + (x1 - x0) * 0.75, y0 + (y1 - y0) * 0.12),
                      (x0 + (x1 - x0) * 0.55, y0 + (y1 - y0) * 0.34), (x0 + (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.34)])


def skull(p, sx, k=1.0):
    """Schedel met gekruiste botten (kijkt naar voren)."""
    bone, ink = (238, 234, 220), (14, 12, 16)
    for a, b in (((sx - 15 * k, -13 * k), (sx + 13 * k, 13 * k)), ((sx - 15 * k, 13 * k), (sx + 13 * k, -13 * k))):
        p.line(ink, a, b, 5.4 * k)
        p.line(bone, a, b, 3.4 * k)
        for q in (a, b):
            p.circle(bone, q[0], q[1] - 2 * k, 2.6 * k)
            p.circle(bone, q[0], q[1] + 2 * k, 2.6 * k)
    p.circle(ink, sx + 2 * k, 0, 11.6 * k)
    p.rect(ink, sx - 13 * k, -7 * k, sx - 1 * k, 7 * k, 2.5 * k)
    p.circle(bone, sx + 2 * k, 0, 10.5 * k)
    p.rect(bone, sx - 12 * k, -6 * k, sx - 2 * k, 6 * k, 2 * k)
    for sd in (-1, 1):
        p.circle(ink, sx + 3.5 * k, sd * 4.4 * k, 3.2 * k)
        p.line(ink, (sx - 11 * k, sd * 2 * k), (sx - 5 * k, sd * 2 * k), 0.9 * k)
    p.line(ink, (sx - 11 * k, 0), (sx - 5 * k, 0), 0.9 * k)
    p.poly(ink, [(sx - 3.5 * k, 0), (sx - 0.5 * k, -1.8 * k), (sx - 0.5 * k, 1.8 * k)])


def panel_top(p, col, x0, y0, x1, y1, r=5.0):
    """Los paneel (dak, motorkap-bult): lakkleur met donkere rand en een glans."""
    p.rect(dark(col, 0.5), x0 - 0.8, y0 - 0.8, x1 + 0.8, y1 + 0.8, r + 0.8)
    p.rect(col, x0, y0, x1, y1, r)
    p.rect(lite(col, 0.2), x0 + 2.5, y0 + 2, x1 - 2.5, y0 + (y1 - y0) * 0.24, r * 0.5)


def chrome_bar(p, x0, y0, x1, y1, r=1.5):
    p.rect(CHROME_D, x0 - 0.7, y0 - 0.7, x1 + 0.7, y1 + 0.7, r + 0.7)
    p.rect(CHROME, x0, y0, x1, y1, r)
    if abs(x1 - x0) > abs(y1 - y0):
        p.rect(CHROME_L, x0 + 1, y0 + (y1 - y0) * 0.2, x1 - 1, y0 + (y1 - y0) * 0.45, r * 0.5)
    else:
        p.rect(CHROME_L, x0 + (x1 - x0) * 0.2, y0 + 1, x0 + (x1 - x0) * 0.45, y1 - 1, r * 0.5)


def lamp(p, x, y, col, r=2.6):
    p.circle((20, 20, 24), x, y, r + 0.9)
    p.circle(col, x, y, r)
    p.circle(lite(col, 0.75), x - r * 0.3, y - r * 0.3, r * 0.4)


def body_mask(p, body):
    """Vorm van de carrosserie (wit). Geeft (halve breedte, x van achterkant, x van neus) terug."""
    c = (255, 255, 255)
    if body == 0:                                            # pickup
        p.rect(c, -59, -26, 59, 26, 8)
        p.rect(c, 16, -28.5, 57, 28.5, 9)
        p.rect(c, -57, -28.5, -20, 28.5, 8)
        return 28, -59, 59
    if body == 1:                                            # muscle car: lange neus, ronde kont
        p.rect(c, -60, -25.5, 52, 25.5, 14)
        p.rect(c, 30, -23, 63, 23, 9)
        p.rect(c, -52, -27.5, -18, 27.5, 10)
        p.rect(c, 20, -27, 50, 27, 10)
        return 27, -60, 63
    if body == 2:                                            # SUV
        p.rect(c, -61, -27.5, 60, 27.5, 8)
        p.rect(c, 26, -28.5, 56, 28.5, 8)
        return 28, -61, 60
    if body == 3:                                            # buggy: smalle neus
        p.poly(c, [(64, -5), (64, 5), (58, 10), (26, 17), (-48, 19), (-56, 13), (-56, -13), (-48, -19), (26, -17), (58, -10)])
        return 18, -56, 64
    p.rect(c, 12, -13.5, 62, 13.5, 5)                        # hot rod
    p.rect(c, -42, -23, 18, 23, 9)
    p.rect(c, -60, -21, -34, 21, 11)
    p.poly(c, [(18, -23), (30, -13.5), (30, 13.5), (18, 23)])
    return 23, -60, 62


def draw_top(cfg, K=4):
    body, paint, acc = cfg["body"], PAINTS[cfg["paint"]][1], ACCENTS[cfg["accent"]][1]
    L, Wd = tire_size(cfg)
    p = Pen(TL, TW, K)
    # ---- onderstel: assen, differentieel, schokdempers in de accentkleur
    for ax in (-AX, AX):
        p.tube((70, 72, 82), (ax, -TY), (ax, TY), 5)
        p.circle((52, 54, 62), ax, 0, 7)
        for sd in (-1, 1):
            p.tube(acc, (ax - 6, sd * 22), (ax - 1, sd * (TY - Wd / 2 - 1)), 3.4)
            p.tube((60, 62, 70), (ax + (10 if ax < 0 else -10), sd * 18), (ax, sd * (TY - Wd / 2 - 2)), 2.4)
            tire_top(p, ax, sd * TY, L, Wd)
    # ---- carrosserie: masker -> lak + sticker -> schaduw en glans
    mask = Pen(TL, TW, K)
    hw, x0, x1 = body_mask(mask, body)
    lak = Pen(TL, TW, K)
    lak.s.fill((*paint, 255))
    decal(lak, cfg["decal"], paint, acc, hw, x0, x1)
    shade = pygame.Surface(lak.s.get_size())
    for yy in range(lak.s.get_height()):
        d = abs(yy / K - TW / 2) / (hw + 1)
        g = int(255 * clamp(1.0 - 0.42 * d ** 2.4, 0.5, 1.0))
        pygame.draw.line(shade, (g, g, g), (0, yy), (lak.s.get_width(), yy))
    lak.s.blit(shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    hi = Pen(TL, TW, K)
    hi.s.fill((0, 0, 0, 255))
    hi.rect((54, 54, 54), x0 + 6, -hw * 0.62, x1 - 6, -hw * 0.40, 3)
    hi.rect((24, 24, 24), x0 + 6, hw * 0.50, x1 - 6, hw * 0.60, 2)
    lak.s.blit(hi.s, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    lak.s.blit(mask.s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    edge = pygame.mask.from_surface(mask.s).to_surface(setcolor=(*dark(paint, 0.72), 255), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-0.7, -0.7), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7)):
        p.s.blit(edge, (dx * K * 1.3, dy * K * 1.3))
    p.s.blit(lak.s, (0, 0))
    roof = lite(paint, 0.10)

    # ---- details per body
    if body == 0:                                            # PICKUP
        p.rect(dark(paint, 0.35), 20, -1, 54, 1)                                        # naad in de motorkap
        panel_top(p, lite(paint, 0.06), 28, -9, 48, 9, 4)                               # bult met luchtinlaat
        p.rect((16, 16, 20), 36, -6, 46, 6, 2)
        for k in range(3):
            p.rect(acc, 37.5 + k * 3, -5, 39 + k * 3, 5)
        glass(p, [(21, -21), (21, 21), (8, 24.5), (8, -24.5)])                           # voorruit
        panel_top(p, roof, -15, -24, 9, 24, 6)                                          # dak
        glass(p, [(-15, -22), (-15, 22), (-21, 20), (-21, -20)])                         # achterruit
        p.rect((30, 31, 37), -56, -23, -23, 23, 3)                                      # laadbak
        p.rect((52, 54, 62), -55, -22, -24, 22, 2.5)
        for k in range(7):
            p.rect((38, 39, 46), -54 + k * 4.4, -21, -52.4 + k * 4.4, 21)
        p.circle((24, 24, 27), -40, 0, 12)                                              # reservewiel in de bak
        p.circle((60, 60, 66), -40, 0, 12, 1.5)
        p.circle(acc, -40, 0, 5.5)
        p.circle(CHROME, -40, 0, 2)
        p.tube(CHROME, (-23, -26), (-23, 26), 3.4)                                      # rolbeugel
        for sd in (-1, 1):
            p.circle(CHROME_D, -27, sd * 19, 3.6)                                       # uitlaatpijpen
            p.circle((12, 12, 14), -27, sd * 19, 2.2)
        chrome_bar(p, 59, -25, 63, 25, 2)                                               # bumpers
        chrome_bar(p, -63, -25, -59.5, 25, 2)
        light_x = -4
    elif body == 1:                                          # MUSCLE
        for sd in (-1, 1):
            p.rect(dark(paint, 0.3), 16, sd * 13.2, 58, sd * 14.4)                      # lijnen in de motorkap
        chrome_bar(p, 22, -9, 42, 9, 3)                                                 # compressor (blower)
        for k in range(5):
            p.rect(CHROME_D, 24.5 + k * 3.6, -8, 25.7 + k * 3.6, 8)
        p.rect((18, 18, 22), 26, -6, 40, 6, 3)
        for sd in (-1, 1):
            p.rect(acc, 27.5, sd * 1, 38.5, sd * 4.6, 1.5)
        glass(p, [(8, -19.5), (8, 19.5), (-5, 23), (-5, -23)])
        panel_top(p, roof, -27, -22, -5, 22, 7)
        glass(p, [(-27, -20.5), (-27, 20.5), (-42, 17), (-42, -17)])
        p.rect(dark(paint, 0.3), -52, -0.6, -43, 0.6)
        for sd in (-1, 1):
            chrome_bar(p, -16, sd * 27, 22, sd * 30, 1.5)                               # zij-uitlaten
            p.circle((12, 12, 14), -16, sd * 28.5, 1.3)
        chrome_bar(p, 62.5, -20, 65.5, 20, 1.5)
        chrome_bar(p, -63.5, -22, -60.5, 22, 1.5)
        light_x = -16
    elif body == 2:                                          # SUV
        p.rect(dark(paint, 0.35), 30, -1, 56, 1)
        for sd in (-1, 1):
            p.rect((16, 16, 20), 36, sd * 9, 48, sd * 14, 1.5)                          # ventilatieroosters
            p.rect(dark(paint, 0.4), 37, sd * 10.6, 47, sd * 11.4)
            p.rect(dark(paint, 0.4), 37, sd * 12.2, 47, sd * 13)
        glass(p, [(29, -21.5), (29, 21.5), (16, 25), (16, -25)])
        panel_top(p, roof, -49, -24.5, 17, 24.5, 6)
        for k in range(2):                                                              # dakramen
            glass(p, [(-8 + k * -20, -13), (-8 + k * -20, 13), (-22 + k * -20, 13), (-22 + k * -20, -13)])
        for sd in (-1, 1):
            p.tube(CHROME_D, (-46, sd * 21), (12, sd * 21), 1.8)                        # dakrails
        for k in range(4):
            p.tube((40, 42, 50), (-40 + k * 15, -21), (-40 + k * 15, 21), 1.6)
        glass(p, [(-49, -22), (-49, 22), (-55, 20), (-55, -20)])
        p.rect((20, 20, 23), -68, -12, -61, 12, 3)                                      # reservewiel achterop
        for k in range(5):
            p.rect((70, 70, 78), -67, -10 + k * 4.4, -62, -8.2 + k * 4.4)
        chrome_bar(p, 60, -26, 63, 26, 1.5)
        for sd in (-1, 1):
            p.tube(CHROME, (63, sd * 20), (66.5, sd * 12), 2.2)                         # bullbar
        p.tube(CHROME, (66.5, -12), (66.5, 12), 2.2)
        chrome_bar(p, -62, -26, -60.5, 26, 1)
        light_x = 6
    elif body == 3:                                          # BUGGY
        p.rect(lite(paint, 0.2), 30, -1.2, 60, 1.2, 1)
        p.rect((34, 35, 42), -22, -15, 22, 15, 5)                                       # cockpit
        p.rect((58, 60, 70), -12, -9, 4, 9, 3)                                          # stoel
        p.circle((20, 20, 24), -2, 0, 7.4)                                              # helm
        p.circle(acc, -2, 0, 6.4)
        p.poly((20, 26, 40), [(2.4, -4.2), (4.8, -2.6), (4.8, 2.6), (2.4, 4.2)])
        p.circle(lite(acc, 0.6), -4, -2.4, 1.8)
        p.tube((24, 24, 28), (12, 0), (17, 0), 1.6)                                     # stuur
        p.tube((24, 24, 28), (17, -5), (17, 5), 1.8)
        for a, b in (((-22, -20), (24, -18)), ((-22, 20), (24, 18)), ((-22, -20), (-22, 20)), ((24, -18), (24, 18)),
                     ((-22, -20), (24, 18)), ((-22, 20), (24, -18))):
            p.tube(acc, a, b, 2.6)                                                      # rolkooi
        p.rect((70, 72, 82), -52, -13, -26, 13, 3)                                      # motor achterin
        p.rect((44, 46, 54), -50, -4, -28, 4, 1.5)
        for k in range(4):
            for sd in (-1, 1):
                p.circle(CHROME_D, -47 + k * 6, sd * 8.6, 2.5)
                p.circle(CHROME_L, -47.5 + k * 6, sd * 8.9, 1.0)
        p.circle(CHROME, -34, 0, 4.6)
        p.circle(acc, -34, 0, 2.8)
        for sd in (-1, 1):
            p.tube(CHROME, (-50, sd * 8.6), (-62, sd * 11), 2.6)                        # uitlaten
            p.tube((60, 62, 70), (54, sd * 8), (AX, sd * (TY - Wd / 2)), 2.2)           # wieldraagarmen
        p.tube(CHROME, (64, -12), (64, 12), 2.4)
        light_x = None
    else:                                                    # HOT ROD
        chrome_bar(p, 22, -8, 50, 8, 2)                                                 # open motorblok
        for k in range(4):
            for sd in (-1, 1):
                p.tube(CHROME, (26 + k * 6.5, sd * 6), (20 + k * 6.5, sd * 20), 2.6)    # uitlaatbochten
                p.circle((14, 14, 16), 20 + k * 6.5, sd * 20, 1.2)
        panel_top(p, acc, 30, -5.5, 44, 5.5, 2.5)                                       # luchthapper
        for k in range(3):
            p.rect((16, 16, 20), 33 + k * 3.4, -4, 34.4 + k * 3.4, 4)
        chrome_bar(p, 58, -11, 63.5, 11, 2)                                             # grille
        for k in range(6):
            p.rect(CHROME_D, 59, -9 + k * 3.3, 62.5, -8 + k * 3.3)
        glass(p, [(17, -17.5), (17, 17.5), (7, 21), (7, -21)])
        panel_top(p, roof, -24, -20.5, 8, 20.5, 7)
        glass(p, [(-24, -18), (-24, 18), (-32, 16), (-32, -16)])
        p.rect(dark(paint, 0.3), -56, -0.6, -36, 0.6)
        for sd in (-1, 1):
            p.tube((60, 62, 70), (50, sd * 10), (AX, sd * (TY - Wd / 2)), 2.2)
        chrome_bar(p, -63.5, -18, -61, 18, 1.2)
        light_x = -8
    if cfg["decal"] == 8:
        skull(p, *((-3, 1.0), (-16, 0.95), (36, 0.85), (42, 0.6), (-8, 0.9))[body])
    # ---- lampen
    hy = (hw - 6) if body != 3 else 8
    hx = x1 - 2.5 if body not in (3, 4) else x1 - 6
    for sd in (-1, 1):
        if body == 4:
            lamp(p, 58, sd * 18, (255, 248, 200), 4)
            p.tube(CHROME_D, (58, sd * 14), (56, sd * 12), 1.4)
        else:
            lamp(p, hx, sd * hy, (255, 248, 200), 3.2)
        p.rect((60, 6, 8), x0 + 0.5, sd * (hy - 3.5), x0 + 3.4, sd * (hy + 3.5), 1)
        p.rect((240, 40, 36), x0 + 1, sd * (hy - 2.6), x0 + 2.8, sd * (hy + 2.6), 0.8)
    # ---- extra's bovenop
    ex = cfg["extra"]
    lx = light_x if light_x is not None else -22
    if ex == 1:                                              # lichtbalk
        p.rect((18, 18, 22), lx - 3, -19, lx + 3.4, 19, 2)
        for k in range(5):
            lamp(p, lx + 0.4, -14 + k * 7, (255, 240, 150), 2.5)
    elif ex == 2:                                            # haaienvin
        p.poly((0, 0, 0, 70), [(lx + 16, 3), (lx - 22, 9), (lx - 14, 3)])
        p.poly(dark(paint, 0.35), [(lx + 16, 0), (lx - 22, -3.4), (lx - 16, 0), (lx - 22, 3.4)])
        p.poly(lite(paint, 0.35), [(lx + 16, 0), (lx - 22, -3.4), (lx - 16, 0)])
    elif ex == 3:                                            # stierenhoorns op de neus
        for sd in (-1, 1):
            pts = [(x1 - 12, sd * (hw - 8)), (x1 - 4, sd * (hw + 3)), (x1 + 4, sd * (hw + 11)), (x1 + 12, sd * (hw + 13))]
            for k in range(3):
                p.tube(mix((236, 226, 196), (120, 100, 70), k / 3), pts[k], pts[k + 1], 5.4 - k * 1.5)
        p.circle(CHROME, x1 - 10, 0, 3.4, 1.4)                                           # neusring
    elif ex == 4:                                            # stekels over het midden
        for k in range(7):
            x = x0 + 13 + k * 9.5
            p.poly((0, 0, 0, 70), [(x - 3, 1.5), (x + 3, 1.5), (x - 4, 7)])
            p.poly(CHROME_D, [(x - 3.4, -3.4), (x + 3.4, -3.4), (x + 3.4, 3.4), (x - 3.4, 3.4)])
            p.poly(CHROME_L, [(x - 3.4, -3.4), (x + 3.4, -3.4), (x, 0)])
            p.poly(CHROME, [(x - 3.4, -3.4), (x - 3.4, 3.4), (x, 0)])
    elif ex == 5:                                            # twee vlaggen achterop
        for sd in (-1, 1):
            bx, by = x0 + 8, sd * (hw - 5)
            p.circle(CHROME_D, bx, by, 2)
            for k in range(4):
                col = acc if k % 2 == 0 else lite(acc, 0.55) if sum(acc) < 500 else dark(acc, 0.3)
                p.poly(col, [(bx - k * 5, by - 5 + (k % 2)), (bx - k * 5 - 5, by - 5 + ((k + 1) % 2)),
                             (bx - k * 5 - 5, by + 5 + ((k + 1) % 2)), (bx - k * 5, by + 5 + (k % 2))])
    elif ex == 6:                                            # grote spoiler
        for sd in (-1, 1):
            p.tube((40, 42, 50), (x0 + 12, sd * 12), (x0 + 2, sd * 12), 2.4)
        p.rect((0, 0, 0, 70), x0 - 6, -hw - 1, x0 + 6, hw + 5, 2)
        p.rect(dark(acc, 0.5), x0 - 9, -hw - 4, x0 + 3, hw + 4, 2)
        p.rect(acc, x0 - 8, -hw - 3, x0 + 2, hw + 3, 1.5)
        p.rect(lite(acc, 0.4), x0 - 7, -hw - 2, x0 - 4.5, hw + 2, 1)
        for sd in (-1, 1):
            p.rect(dark(acc, 0.4), x0 - 10, sd * (hw + 2), x0 + 4, sd * (hw + 5), 1)
    return p.s


# ------------------------------------------------------------------ onderkant
def draw_under(cfg, K=4):
    acc = ACCENTS[cfg["accent"]][1]
    L, Wd = tire_size(cfg)
    p = Pen(TL, TW, K)
    p.rect((20, 20, 24), -58, -25, 58, 25, 8)
    p.rect((50, 52, 60), -57, -24, 57, 24, 7.5)
    for sd in (-1, 1):
        p.rect((78, 80, 92), -56, sd * 13, 56, sd * 18, 1.5)                            # chassisbalken
        p.rect((36, 37, 44), -56, sd * 14.6, 56, sd * 15.6)
    for x in (-30, 0, 30):
        p.rect((70, 72, 82), x - 2.5, -14, x + 2.5, 14, 1)
    p.rect((112, 114, 126), 22, -11, 46, 11, 3)                                         # carterpan
    for k in range(5):
        p.rect((84, 86, 98), 25 + k * 4, -9, 26.5 + k * 4, 9)
    p.circle((40, 40, 46), 34, 0, 2.2)
    p.rect((96, 98, 110), 4, -7, 22, 7, 3)                                              # versnellingsbak
    p.tube((150, 154, 168), (-AX, 0), (4, 0), 4)                                        # aandrijfas
    p.tube((150, 154, 168), (AX, 0), (46, 0), 3.4)
    p.tube((150, 110, 70), (20, 21), (-52, 21), 3.4)                                    # uitlaat
    p.rect((124, 92, 60), -30, 17, -10, 25, 3)
    p.rect((24, 24, 28), -54, -10, -44, 10, 2)                                          # tank
    p.rect(acc, 50, -18, 57, 18, 2)                                                     # beschermplaat
    for k in range(4):
        p.circle(dark(acc, 0.5), 53.5, -13 + k * 8.6, 1.2)
    for ax in (-AX, AX):
        p.tube((96, 98, 110), (ax, -TY), (ax, TY), 6)
        p.circle((124, 126, 138), ax, 0, 9)
        p.circle((84, 86, 98), ax, 0, 9, 1.6)
        p.circle((60, 62, 70), ax, 0, 3.4)
        for sd in (-1, 1):
            p.tube(acc, (ax - 7, sd * 20), (ax - 1, sd * (TY - Wd / 2 - 1)), 3.6)
            p.tube((70, 72, 82), (ax + (12 if ax < 0 else -12), sd * 16), (ax, sd * (TY - Wd / 2 - 2)), 2.6)
            tire_top(p, ax, sd * TY, L, Wd)
    return p.s


# ------------------------------------------------------------------ zijaanzicht
# profiel van de carrosserie per body: lijst punten (x, hoogte boven de grond)
PROFILE = [
    [(-59, 44), (60, 44), (62, 52), (58, 58), (22, 60), (10, 76), (-16, 76), (-20, 61), (-59, 61)],
    [(-60, 44), (63, 44), (64, 51), (58, 56), (10, 59), (-4, 72), (-26, 72), (-46, 60), (-60, 58)],
    [(-61, 44), (60, 44), (62, 52), (58, 58), (30, 60), (17, 77), (-52, 77), (-61, 62)],
    [(-56, 46), (64, 46), (64, 51), (26, 56), (-48, 58), (-56, 54)],
    [(-60, 44), (62, 44), (62, 58), (18, 58), (8, 71), (-26, 71), (-34, 59), (-58, 57)],
]
WINDOW = [
    [(19, 61), (9, 73), (-14, 73), (-17, 61)],
    [(7, 60), (-5, 69.5), (-25, 69.5), (-40, 60)],
    [(27, 61), (16, 74), (-49, 74), (-56, 62)],
    None,
    [(15, 59), (7, 68.5), (-25, 68.5), (-31, 59)],
]


def draw_side(cfg, K=4):
    body, paint, acc = cfg["body"], PAINTS[cfg["paint"]][1], ACCENTS[cfg["accent"]][1]
    R = (23, 26, 29)[cfg["wheels"]]
    p = Pen(TL, TH, K)

    def Z(pts):
        return [(x, TH / 2 - z) for x, z in pts]
    g = TH / 2                                               # y van de grond
    p.tube((70, 72, 82), (-56, g - 40), (56, g - 40), 4)                                # chassis
    for ax in (-AX, AX):
        p.tube(acc, (ax - 10, g - 42), (ax - 3, g - R - 2), 3.6)                        # schokdempers
        p.tube((60, 62, 70), (ax + 12, g - 40), (ax, g - R), 2.6)
    p.poly(dark(paint, 0.7), Z([(x * 1.012, z + (1 if z > 50 else -1)) for x, z in PROFILE[body]]))
    p.poly(paint, Z(PROFILE[body]))
    top = max(z for _, z in PROFILE[body])
    p.poly(lite(paint, 0.22), Z([(x * 0.97, z - 1.2) for x, z in PROFILE[body] if z > 55] + [(-54, 57), (54, 57)]))
    p.poly(paint, Z([(x * 0.96, min(z, top) - 3.4) for x, z in PROFILE[body] if z > 55] + [(-54, 56), (54, 56)]))
    p.rect(dark(paint, 0.3), -57, g - 49, 58, g - 44, 1)                                # dorpel
    d = cfg["decal"]
    if d:
        col = acc if d not in (8,) else (238, 234, 220)
        p.rect(col, -52, g - 55, 56, g - 51.5, 1)
        if d in (1, 4, 7):
            for k in range(5):
                p.poly(col, [(56 - k * 14, g - 55), (40 - k * 14, g - 59 - (k % 2) * 2), (46 - k * 14, g - 55)])
    if WINDOW[body]:
        p.poly((8, 12, 20), Z(WINDOW[body]))
        p.poly(GLASS, Z([(x * 0.97 - 0.5, z - 0.8 if z > 65 else z + 0.8) for x, z in WINDOW[body]]))
        wx = [x for x, _ in WINDOW[body]]
        if body == 2:
            for k in (-0.34, 0.3):
                x = wx[2] + (wx[1] - wx[2]) * (0.5 + k)
                p.rect(paint, x - 1.6, g - 74, x + 1.6, g - 61)
    else:                                                    # buggy: rolkooi en helm
        for a, b in (((-22, 58), (-14, 76)), ((-14, 76), (16, 74)), ((16, 74), (26, 56)), ((-14, 76), (2, 57))):
            p.tube(acc, (a[0], g - a[1]), (b[0], g - b[1]), 2.8)
        p.circle((20, 20, 24), -2, g - 64, 6.4)
        p.circle(acc, -2, g - 64, 5.4)
        p.rect((20, 26, 40), 0, g - 66, 4, g - 62, 1)
        p.rect((70, 72, 82), -52, g - 66, -28, g - 57, 2)
        p.tube(CHROME, (-50, g - 62), (-63, g - 68), 2.6)
    if body == 1:
        chrome_bar(p, 22, g - 66, 42, g - 59, 2)
    if body == 4:
        chrome_bar(p, 22, g - 62, 50, g - 52, 2)
        for k in range(4):
            p.tube(CHROME, (26 + k * 6.5, g - 54), (22 + k * 6.5, g - 46), 2.4)
    if body == 0:
        p.tube(CHROME, (-22, g - 61), (-22, g - 74), 3)
    ex = cfg["extra"]
    if ex == 1:
        p.rect((18, 18, 22), -6, g - top - 4, 6, g - top, 1)
        lamp(p, 5, g - top - 2, (255, 240, 150), 2.2)
    elif ex == 2:
        p.poly(dark(paint, 0.2), [(12, g - top), (-22, g - top - 15), (-18, g - top)])
    elif ex == 3:
        p.tube((236, 226, 196), (56, g - 57), (66, g - 68), 4)
    elif ex == 4:
        for k in range(6):
            p.poly(CHROME, [(-30 + k * 9, g - top), (-26 + k * 9, g - top - 7), (-22 + k * 9, g - top)])
    elif ex == 5:
        p.tube(CHROME_D, (-52, g - 60), (-52, g - 79), 1.6)
        p.poly(acc, [(-52, g - 79), (-64, g - 76), (-52, g - 71)])
    elif ex == 6:
        p.tube((40, 42, 50), (-54, g - 60), (-58, g - 72), 2.4)
        p.rect(acc, -68, g - 76, -50, g - 72, 1.5)
    lamp(p, 61, g - 53, (255, 248, 200), 2.6)
    p.rect((240, 40, 36), -60.5, g - 56, -58, g - 50, 1)
    for ax in (-AX, AX):
        tire_side(p, ax, g - R - 2.4, R, acc)
    return p.s


# ------------------------------------------------------------------ voor- en achterkant
def draw_end(cfg, front, K=4):
    body, paint, acc = cfg["body"], PAINTS[cfg["paint"]][1], ACCENTS[cfg["accent"]][1]
    L, Wd = tire_size(cfg)
    R = (23, 26, 29)[cfg["wheels"]]
    p = Pen(TW, TH, K)
    g = TH / 2
    hw = (28, 27, 28, 18, 23)[body]
    top = max(z for _, z in PROFILE[body])
    p.tube((84, 86, 98), (-TY, g - R - 2), (TY, g - R - 2), 6)                          # as + differentieel
    p.circle((124, 126, 138), 0, g - R - 2, 9)
    p.circle((84, 86, 98), 0, g - R - 2, 9, 1.6)
    for sd in (-1, 1):
        p.tube(acc, (sd * 18, g - 44), (sd * (TY - Wd / 2 - 2), g - R - 2), 3.6)
        tire_front(p, sd * TY, g - 2 * R - 2.4, g - 2.4, Wd)
    p.rect(dark(paint, 0.7), -hw - 1, g - 61, hw + 1, g - 41, 4)                        # onderste deel
    p.rect(paint, -hw, g - 60, hw, g - 42, 3.5)
    p.rect(lite(paint, 0.25), -hw + 2, g - 59.5, hw - 2, g - 57.5, 1)
    if body != 3:
        cabw = hw - 3
        p.poly(dark(paint, 0.7), [(-cabw - 1, g - 59), (cabw + 1, g - 59), (cabw - 3, g - top - 1), (-cabw + 3, g - top - 1)])
        p.poly(paint, [(-cabw, g - 59), (cabw, g - 59), (cabw - 4, g - top), (-cabw + 4, g - top)])
        p.poly((8, 12, 20), [(-cabw + 2, g - 60), (cabw - 2, g - 60), (cabw - 5, g - top + 3), (-cabw + 5, g - top + 3)])
        p.poly(GLASS, [(-cabw + 3.4, g - 61), (cabw - 3.4, g - 61), (cabw - 6, g - top + 4), (-cabw + 6, g - top + 4)])
        p.poly(GLASS_HI, [(-cabw + 6, g - top + 5), (-2, g - top + 5), (-8, g - 62), (-cabw + 5, g - 62)])
    else:
        for sd in (-1, 1):
            p.tube(acc, (sd * 17, g - 58), (sd * 13, g - 76), 2.8)
        p.tube(acc, (-13, g - 76), (13, g - 76), 2.8)
        p.circle(acc, 0, g - 64, 5.6)
        p.rect((20, 26, 40), -4, g - 66, 4, g - 62, 1)
    if front:
        p.rect((14, 14, 18), -hw + 9, g - 56, hw - 9, g - 46, 2)                        # grille
        for k in range(int((2 * hw - 20) // 4)):
            p.rect(CHROME, -hw + 10.5 + k * 4, g - 55, -hw + 12 + k * 4, g - 47)
        for sd in (-1, 1):
            lamp(p, sd * (hw - 4.6), g - 51, (255, 248, 200), 3.4)
        chrome_bar(p, -hw - 2, g - 44, hw + 2, g - 39.5, 2)
        if cfg["extra"] == 3:
            for sd in (-1, 1):
                p.tube((236, 226, 196), (sd * (hw - 4), g - 58), (sd * (hw + 12), g - 70), 4.4)
    else:
        p.rect(dark(paint, 0.25), -hw + 6, g - 56, hw - 6, g - 46, 2)                   # achterklep
        img = font(9, False).render("MONSTER", True, lite(paint, 0.6))
        img = pygame.transform.smoothscale(img, (int(img.get_width() * K * 0.8), int(img.get_height() * K * 0.8)))
        p.s.blit(img, img.get_rect(center=p.pt(0, g - 51)))
        for sd in (-1, 1):
            p.rect((240, 40, 36), sd * (hw - 5), g - 57, sd * (hw - 1), g - 46, 1)
        chrome_bar(p, -hw - 2, g - 44, hw + 2, g - 40, 2)
    if cfg["extra"] == 1:
        p.rect((18, 18, 22), -19, g - top - 4.5, 19, g - top - 0.5, 1.5)
        for k in range(5):
            lamp(p, -14 + k * 7, g - top - 2.5, (255, 240, 150), 2.2)
    elif cfg["extra"] == 2:
        p.rect(dark(paint, 0.2), -1.6, g - top - 14, 1.6, g - top, 1)
    elif cfg["extra"] == 6:
        p.rect(acc, -hw - 3, g - top + 2, hw + 3, g - top + 6, 1.5)
    return p.s


# ------------------------------------------------------------------ alle aanzichten samen
class TruckArt:
    Q = 48                                                   # aantal standen van een flip dat we bewaren

    def __init__(self, cfg, big=False):
        def small(img, w, h):
            return pygame.transform.smoothscale(img, (w, h)).convert_alpha()
        raw = draw_top(cfg)
        self.color = PAINTS[cfg["paint"]][1]
        self.top = small(raw, TL, TW)
        self.big = pygame.transform.smoothscale(raw, (TL * 3, TW * 3)).convert_alpha() if big else None
        under = small(draw_under(cfg), TL, TW)
        self.under_x = pygame.transform.flip(under, True, False)          # op zijn kop na een flip: neus wijst naar achter
        self.under_y = pygame.transform.flip(under, False, True)          # op zijn kop na een roll
        side = small(draw_side(cfg), TL, TH)
        self.side = side
        self.side_v = pygame.transform.flip(side, False, True)
        self.front_x = pygame.transform.rotate(small(draw_end(cfg, True), TW, TH), 90)     # dak wijst naar achter
        self.rear_x = pygame.transform.rotate(small(draw_end(cfg, False), TW, TH), -90)    # dak wijst naar voor
        self.cache = {}
        sh = pygame.Surface((TL - 16, TW - 30), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 125), sh.get_rect())
        self.shadow = sh

    def proj(self, pitch, roll=0.0):
        """Afbeelding van de truck van bovenaf bij deze stand (flip = pitch, barrel roll = roll)."""
        rolling = abs(math.sin(roll)) > 0.03
        ang = roll if rolling else pitch
        q = int(round(ang / math.tau * self.Q)) % self.Q
        key = (rolling, q)
        img = self.cache.get(key)
        if img is not None:
            return img
        a = q * math.tau / self.Q
        c, s = math.cos(a), math.sin(a)
        if q == 0:
            img = self.top
        elif not rolling:                                    # flip: bovenkant/onderkant + voor- of achterkant
            lm, lf = int(TL * abs(c)), int(TH * abs(s))
            main = self.top if c >= 0 else self.under_x
            face = self.front_x if s > 0 else self.rear_x
            img = pygame.Surface((max(2, lm + lf), TW), pygame.SRCALPHA)
            first_face = (s > 0) != (c >= 0)
            x = 0
            for part, ln in ((face, lf), (main, lm)) if first_face else ((main, lm), (face, lf)):
                if ln >= 1:
                    img.blit(pygame.transform.smoothscale(part, (ln, TW)), (x, 0))
                    x += ln
        else:                                                # barrel roll: bovenkant/onderkant + een zijkant
            wm, wf = int(TW * abs(c)), int(TH * abs(s))
            main = self.top if c >= 0 else self.under_y
            face = self.side_v if s > 0 else self.side
            img = pygame.Surface((TL, max(2, wm + wf)), pygame.SRCALPHA)
            first_face = (s > 0) == (c >= 0)
            y = 0
            for part, ln in ((face, wf), (main, wm)) if first_face else ((main, wm), (face, wf)):
                if ln >= 1:
                    img.blit(pygame.transform.smoothscale(part, (TL, ln)), (0, y))
                    y += ln
        self.cache[key] = img
        return img


_ART = {}


def get_art(cfg, big=False):
    key = (cfg["body"], cfg["paint"], cfg["accent"], cfg["decal"], cfg["wheels"], cfg["extra"], big)
    if key not in _ART:
        if len(_ART) > 30:
            _ART.clear()
        _ART[key] = TruckArt(cfg, big)
    return _ART[key]
