"""
ma_arena.py  -  de arena's van MONSTER ARENA
Een arena = een vloer met schansen, heuvels, modder/ijs/olie, een muur en tribunes eromheen,
plus alles wat erop staat: autowrakken, bussen, explosieve vaten, bandenstapels,
vuurringen, pickups en vlammenwerpers.
"""
import math
import random

import pygame

from ma_core import (CYAN, FIRE, GOLD, LIME, RED, SHEET_FILE, TAU, WHITE, add_glow, clamp, dark, dim, font, glow, lite, mix,
                     soft)

AW, AH, AM = 3400, 2400, 330        # wereld (incl. tribunes) en breedte van de tribune-rand
CROWD = [(230, 70, 60), (240, 180, 50), (70, 150, 230), (235, 235, 235), (90, 200, 110), (200, 90, 200), (250, 130, 40)]
WRECK_MODELS = [9, 10, 11, 12, 13, 14, 15, 19, 21, 22, 23, 24, 25, 26, 27, 29, 34, 35, 36, 37]

THEMES = {
    "dirt": dict(base=(164, 108, 60), spots=((236, 176, 108, 22), (104, 62, 30, 28)), track=(128, 82, 44), dust=(208, 156, 100),
                 wall=((214, 56, 40), (236, 232, 224)), light=(255, 214, 150), dark=0, pit="mud", back=(18, 13, 12)),
    "scrap": dict(base=(78, 74, 78), spots=((20, 18, 24, 46), (150, 78, 34, 30)), track=(50, 48, 54), dust=(150, 146, 150),
                  wall=((240, 190, 30), (30, 30, 34)), light=(255, 190, 110), dark=40, pit="oil", back=(10, 10, 14)),
    "frost": dict(base=(206, 218, 234), spots=((255, 255, 255, 40), (150, 176, 214, 34)), track=(160, 178, 204), dust=(236, 242, 250),
                  wall=((40, 110, 210), (240, 244, 250)), light=(190, 225, 255), dark=22, pit="ice", back=(10, 14, 24)),
}

ARENAS = [
    dict(name="DIRT DOME", theme="dirt", desc="De klassieke stuntarena: twee mega-schansen, modder en een rij wrakken."),
    dict(name="SCRAPYARD", theme="scrap", desc="Schroothoop bij nacht: bussen, olievlekken en heel veel vaten."),
    dict(name="FROST BOWL", theme="frost", desc="Sneeuw en een bevroren meer in het midden. Glad, dus pas op!"),
]


def layout(idx):
    """Wat staat waar? Geeft een dict met lijsten terug (posities in wereld-pixels)."""
    cx, cy = AW / 2, AH / 2
    L = dict(ramps=[], mounds=[], pits=[], wrecks=[], buses=[], barrels=[], stacks=[], hoops=[], pickups=[], jets=[])

    def ramp(x, y, ang, ln=200, wr=84, hr=84):
        L["ramps"].append((x, y, math.cos(ang), math.sin(ang), ln, wr, hr))

    def row(x, y, ang, n, gap=62):                           # rij wrakken dwars op de rijrichting geparkeerd
        for k in range(n):
            L["wrecks"].append((x + math.cos(ang) * k * gap, y + math.sin(ang) * k * gap, ang + math.pi / 2))

    def cluster(key, x, y, n, r=46):
        for k in range(n):
            a = TAU * k / n + 0.4
            L[key].append((x + math.cos(a) * r * (0 if n == 1 else 1), y + math.sin(a) * r * (0 if n == 1 else 1)))

    if idx == 0:                                             # ---- DIRT DOME
        ramp(600, cy, 0.0, 280, 104, 124)
        ramp(AW - 600, cy, math.pi, 280, 104, 124)
        row(980, cy, 0.0, 7)
        row(AW - 980, cy, math.pi, 7)
        L["hoops"] += [(1180, cy, 0.0), (AW - 1180, cy, math.pi)]
        for x, y in ((820, 660), (AW - 820, 660), (820, AH - 660), (AW - 820, AH - 660), (cx, 600), (cx, AH - 600)):
            ramp(x, y, math.atan2(cy - y, cx - x))
        L["mounds"] = [(cx, cy, 170, 46), (cx - 400, cy - 340, 110, 34), (cx + 400, cy + 340, 110, 34),
                       (cx - 400, cy + 340, 100, 30), (cx + 400, cy - 340, 100, 30)]
        L["pits"] = [(1130, AH - 560, 120, 90), (AW - 1130, 560, 120, 90)]
        L["buses"] = [(cx - 108, AH - 870, 0.0), (cx + 108, AH - 870, 0.0)]
        cluster("barrels", 1130, 560, 3)
        cluster("barrels", AW - 1130, AH - 560, 3)
        for x, y in ((cx - 720, cy - 270), (cx + 720, cy + 270), (cx, cy - 300), (cx - 720, cy + 270), (cx + 720, cy - 270)):
            cluster("stacks", x, y, 1)
        L["pickups"] = [(cx, cy, "x2"), (700, 520, "nitro"), (AW - 700, AH - 520, "nitro"), (AW - 700, 520, "time"), (700, AH - 520, "nitro")]
    elif idx == 1:                                           # ---- SCRAPYARD
        ramp(560, 720, 0.25, 260, 96, 116)
        row(920, 820, 0.25, 6)
        L["hoops"].append((1120, 870, 0.25))
        ramp(AW - 560, AH - 720, math.pi + 0.25, 260, 96, 116)
        row(AW - 920, AH - 820, math.pi + 0.25, 6)
        L["hoops"].append((AW - 1120, AH - 870, math.pi + 0.25))
        ramp(cx - 420, AH - 620, -math.pi / 2, 230, 92, 104)          # over de bussen
        L["buses"] = [(cx - 420, AH - 940, 0.0), (cx - 420, AH - 1010, 0.0), (cx - 420, AH - 1080, 0.0)]
        ramp(cx + 420, 620, math.pi / 2, 230, 92, 104)
        L["buses"] += [(cx + 420, 940, math.pi), (cx + 420, 1010, math.pi), (cx + 420, 1080, math.pi)]
        for x, y, a in ((cx, cy - 40, 0.9), (700, AH - 620, -0.6), (AW - 700, 620, 2.5), (cx + 760, cy + 300, 3.6), (cx - 760, cy - 300, 0.5)):
            ramp(x, y, a, 170, 76, 70)
        L["mounds"] = [(cx - 150, cy + 330, 120, 36), (cx + 150, cy - 330, 120, 36)]
        L["pits"] = [(cx + 520, AH - 620, 150, 84), (cx - 520, 620, 150, 84), (cx - 430, cy - 150, 110, 70)]
        for x, y, n in ((760, cy + 120, 4), (AW - 760, cy - 120, 4), (cx - 60, 520, 3), (cx + 60, AH - 520, 3), (cx + 300, cy + 140, 2)):
            cluster("barrels", x, y, n)
        rnd = random.Random(4)
        busy = [(r[0] + r[2] * r[4] / 2, r[1] + r[3] * r[4] / 2, 250) for r in L["ramps"]] + [(b[0], b[1], 190) for b in L["buses"]] \
            + [(b[0], b[1], 90) for b in L["barrels"]] + [(p[0], p[1], 170) for p in L["pits"]] + [(m[0], m[1], 160) for m in L["mounds"]] \
            + [(w[0], w[1], 110) for w in L["wrecks"]] + [(h[0], h[1], 150) for h in L["hoops"]]
        for _ in range(12):                                  # losse wrakken op vrije plekken
            for _try in range(60):
                x, y = rnd.uniform(AM + 240, AW - AM - 240), rnd.uniform(AM + 240, AH - AM - 240)
                if all(math.hypot(x - bx, y - by) > br for bx, by, br in busy):
                    L["wrecks"].append((x, y, rnd.uniform(0, TAU)))
                    busy.append((x, y, 130))
                    break
        for x, y in ((cx - 900, cy + 420), (cx + 900, cy - 420), (cx, cy - 560), (cx, cy + 560), (620, 1300), (AW - 620, 1100)):
            cluster("stacks", x, y, 1)
        L["pickups"] = [(cx, cy - 320, "x2"), (640, 1040, "nitro"), (AW - 640, AH - 1040, "nitro"), (cx + 900, AH - 560, "time"), (cx - 900, 560, "nitro")]
    else:                                                    # ---- FROST BOWL
        L["pits"] = [(cx, cy, 520, 330)]                     # het bevroren meer
        for k in range(6):                                   # schansen rond het meer, wijzen over het ijs
            a = TAU * k / 6 + 0.26
            x, y = cx + math.cos(a) * 880, cy + math.sin(a) * 600
            ramp(x, y, math.atan2(cy - y, cx - x), 240 if k % 3 == 0 else 190, 96 if k % 3 == 0 else 80, 118 if k % 3 == 0 else 80)
        for a in (0.26, 0.26 + math.pi):
            L["hoops"].append((cx + math.cos(a) * 380, cy + math.sin(a) * 250, a + math.pi))
        row(cx - 186, cy, 0.0, 7)
        L["buses"] = [(cx - 1030, AM + 250, 0.0), (cx + 1030, AH - AM - 250, math.pi)]
        for x, y in ((640, AH - 560), (AW - 640, 560), (cx - 420, AM + 190), (cx + 420, AH - AM - 190)):
            cluster("barrels", x, y, 3)
        for k in range(8):
            a = TAU * k / 8
            L["stacks"].append((cx + math.cos(a) * 650, cy + math.sin(a) * 440))
        L["pickups"] = [(cx, cy - 130, "x2"), (cx, cy + 130, "time"), (640, cy, "nitro"), (AW - 640, cy, "nitro"), (cx, AM + 150, "nitro")]
        busy = [(r[0] + r[2] * r[4] / 2, r[1] + r[3] * r[4] / 2, 330) for r in L["ramps"]] + [(b[0], b[1], 260) for b in L["buses"]] \
            + [(b[0], b[1], 190) for b in L["barrels"]] + [(p[0], p[1], 170) for p in L["stacks"]] + [(p[0], p[1], 190) for p in L["pickups"]]
        rnd = random.Random(8)
        for _ in range(10):                                  # sneeuwhopen op vrije plekken
            for _try in range(80):
                x, y = rnd.uniform(AM + 190, AW - AM - 190), rnd.uniform(AM + 190, AH - AM - 190)
                if ((x - cx) / 700) ** 2 + ((y - cy) / 480) ** 2 > 1 and all(math.hypot(x - bx, y - by) > br for bx, by, br in busy):
                    L["mounds"].append((x, y, rnd.randint(84, 120), rnd.randint(26, 40)))
                    busy.append((x, y, 250))
                    break
    for k in range(6):                                       # vlammenwerpers langs de lange muren
        x = AM + 260 + k * (AW - 2 * AM - 520) / 5
        L["jets"] += [(x, AM + 34), (x, AH - AM - 34)]
    return L


# ------------------------------------------------------------------ dingen in de arena
class Wreck:
    """Een oude auto die je kunt platrijden (of overheen springen)."""
    R = 40

    def __init__(self, x, y, ang, sprite):
        self.x, self.y, self.ang = x, y, ang
        self.crushed = False
        self.img = pygame.transform.rotate(sprite, -math.degrees(ang))
        w, h = sprite.get_size()
        flat = pygame.transform.smoothscale(sprite, (int(w * 1.1), int(h * 1.12)))
        flat.fill((120, 112, 108, 255), special_flags=pygame.BLEND_RGBA_MULT)
        rnd = random.Random(int(x * 7 + y))
        for _ in range(7):                                   # deuken en barsten
            a = (rnd.uniform(6, flat.get_width() - 6), rnd.uniform(4, flat.get_height() - 4))
            pygame.draw.line(flat, (22, 22, 26), a, (a[0] + rnd.uniform(-16, 16), a[1] + rnd.uniform(-10, 10)), 2)
        self.flat = pygame.transform.rotate(flat, -math.degrees(ang))

    def touches(self, x, y, r=46):
        return (x - self.x) ** 2 + (y - self.y) ** 2 < r * r

    def draw(self, s, cx, cy):
        img = self.flat if self.crushed else self.img
        s.blit(img, img.get_rect(center=(self.x - cx, self.y - cy)))


def make_bus(col):
    L, Wd = 210, 58
    b = pygame.Surface((L, Wd), pygame.SRCALPHA)
    pygame.draw.rect(b, dark(col, 0.6), (0, 0, L, Wd), border_radius=9)
    pygame.draw.rect(b, col, (2, 2, L - 4, Wd - 4), border_radius=8)
    pygame.draw.rect(b, lite(col, 0.25), (10, 6, L - 60, 8), border_radius=4)
    pygame.draw.rect(b, dark(col, 0.18), (8, Wd - 12, L - 50, 6), border_radius=3)
    for sd in (4, Wd - 9):                                   # zwarte strepen
        pygame.draw.rect(b, (24, 24, 28), (10, sd, L - 54, 5))
    for k in range(8):                                       # dakribbels
        pygame.draw.line(b, dark(col, 0.2), (22 + k * 20, 12), (22 + k * 20, Wd - 14), 2)
    for x in (60, 120):                                      # dakluiken
        pygame.draw.rect(b, dark(col, 0.3), (x, 20, 22, 18), border_radius=3)
        pygame.draw.rect(b, lite(col, 0.3), (x + 2, 22, 18, 14), border_radius=2)
    pygame.draw.polygon(b, (10, 14, 22), [(L - 46, 6), (L - 34, 10), (L - 34, Wd - 10), (L - 46, Wd - 6)])
    pygame.draw.polygon(b, (40, 60, 90), [(L - 44, 9), (L - 36, 12), (L - 36, Wd - 12), (L - 44, Wd - 9)])
    pygame.draw.polygon(b, (120, 170, 220), [(L - 43, 11), (L - 38, 13), (L - 38, 24), (L - 43, 22)])
    pygame.draw.rect(b, dark(col, 0.12), (L - 33, 7, 28, Wd - 14), border_radius=6)
    pygame.draw.rect(b, (20, 20, 24), (L - 6, 10, 5, Wd - 20), border_radius=2)
    for y in (9, Wd - 15):
        pygame.draw.circle(b, (255, 248, 200), (L - 6, y + 3), 4)
        pygame.draw.rect(b, (240, 40, 36), (1, y, 4, 7))
    pygame.draw.rect(b, (20, 20, 24), (8, 16, 5, Wd - 32))
    return b


class Bus:
    """Een bus: platrijden of er in de lengte overheen springen."""
    HL, HW = 105, 29

    def __init__(self, x, y, ang, col):
        self.x, self.y, self.ang = x, y, ang
        self.crushed = False
        base = make_bus(col)
        self.img = pygame.transform.rotate(base, -math.degrees(ang))
        flat = pygame.transform.smoothscale(base, (int(base.get_width() * 1.04), int(base.get_height() * 1.14)))
        flat.fill((116, 110, 106, 255), special_flags=pygame.BLEND_RGBA_MULT)
        rnd = random.Random(int(x + y * 3))
        for _ in range(16):
            a = (rnd.uniform(8, flat.get_width() - 8), rnd.uniform(5, flat.get_height() - 5))
            pygame.draw.line(flat, (20, 20, 24), a, (a[0] + rnd.uniform(-26, 26), a[1] + rnd.uniform(-14, 14)), 2)
        pygame.draw.ellipse(flat, (34, 32, 34), (50, 14, 110, 38))
        pygame.draw.ellipse(flat, (64, 60, 60), (56, 18, 98, 30), 3)
        self.flat = pygame.transform.rotate(flat, -math.degrees(ang))

    def touches(self, x, y, r=30):
        dx, dy = x - self.x, y - self.y
        c, s = math.cos(self.ang), math.sin(self.ang)
        return abs(dx * c + dy * s) < self.HL + r and abs(-dx * s + dy * c) < self.HW + r

    def draw(self, s, cx, cy):
        img = self.flat if self.crushed else self.img
        s.blit(img, img.get_rect(center=(self.x - cx, self.y - cy)))


class Thing:
    """Vat, stapel of pickup: staat er, verdwijnt als je hem raakt en komt later terug."""

    def __init__(self, x, y, kind, respawn):
        self.x, self.y, self.kind, self.respawn = x, y, kind, respawn
        self.away = 0.0                                      # > 0: nog zoveel seconden weg

    @property
    def here(self):
        return self.away <= 0


def make_sprites(theme):
    """Kleine afbeeldingen voor vaten, stapels en pickups."""
    S = {}
    b = pygame.Surface((44, 44), pygame.SRCALPHA)            # explosief vat
    pygame.draw.circle(b, (0, 0, 0, 90), (25, 26), 17)
    pygame.draw.circle(b, (120, 14, 14), (22, 22), 17)
    pygame.draw.circle(b, (226, 44, 36), (22, 22), 15)
    pygame.draw.circle(b, (150, 20, 20), (22, 22), 15, 2)
    pygame.draw.circle(b, (250, 110, 90), (17, 17), 5)
    pygame.draw.polygon(b, (250, 210, 40), [(22, 12), (31, 28), (13, 28)])
    pygame.draw.polygon(b, (20, 16, 12), [(22, 16), (28, 26), (16, 26)], 2)
    pygame.draw.line(b, (20, 16, 12), (22, 19), (22, 23), 2)
    S["barrel"] = b
    t = pygame.Surface((80, 80), pygame.SRCALPHA)
    if theme == "frost":                                     # sneeuwpop
        pygame.draw.circle(t, (0, 0, 0, 70), (45, 46), 26)
        pygame.draw.circle(t, (232, 240, 250), (40, 40), 27)
        pygame.draw.circle(t, (255, 255, 255), (38, 37), 19)
        pygame.draw.circle(t, (200, 214, 234), (40, 40), 27, 2)
        pygame.draw.circle(t, (30, 30, 36), (40, 40), 10)
        pygame.draw.circle(t, (60, 60, 70), (40, 40), 6)
        pygame.draw.polygon(t, (250, 130, 30), [(48, 38), (62, 40), (48, 43)])
        pygame.draw.line(t, (110, 70, 40), (16, 30), (4, 20), 3)
        pygame.draw.line(t, (110, 70, 40), (64, 52), (76, 60), 3)
    else:                                                    # stapel banden
        for ox, oy in ((-13, -8), (13, -8), (0, 14), (0, -1)):
            x, y = 40 + ox, 40 + oy
            pygame.draw.circle(t, (0, 0, 0, 80), (x + 4, y + 5), 19)
            pygame.draw.circle(t, (22, 22, 25), (x, y), 19)
            pygame.draw.circle(t, (66, 66, 72), (x, y), 19, 3)
            pygame.draw.circle(t, (44, 44, 48), (x, y), 13, 2)
            pygame.draw.circle(t, (10, 10, 12), (x, y), 8)
        pygame.draw.circle(t, (250, 210, 40), (40, 39), 4)
    S["stack"] = t
    for kind, col, label in (("nitro", CYAN, "N"), ("x2", GOLD, "x2"), ("time", LIME, "+10")):
        p = pygame.Surface((64, 64), pygame.SRCALPHA)
        pts = [(32 + math.cos(TAU * k / 6 + 0.52) * 26, 32 + math.sin(TAU * k / 6 + 0.52) * 26) for k in range(6)]
        pygame.draw.polygon(p, (10, 10, 14, 220), pts)
        pygame.draw.polygon(p, col, pts, 4)
        img = font(22 if len(label) < 3 else 17).render(label, True, col)
        p.blit(img, img.get_rect(center=(31, 31)))
        S[kind] = p
    return S


# ------------------------------------------------------------------ de arena zelf
class Arena:
    def __init__(self, idx):
        self.idx = idx
        self.spec = ARENAS[idx]
        self.theme = THEMES[self.spec["theme"]]
        self.w, self.h = AW, AH
        self.x0, self.y0, self.x1, self.y1 = AM, AM, AW - AM, AH - AM
        L = layout(idx)
        self.ramps, self.mounds, self.pits = L["ramps"], L["mounds"], L["pits"]
        self.hoops, self.jets = L["hoops"], L["jets"]
        self.L = L
        self.world = None

    # ---- vragen aan de arena
    def height(self, x, y):
        """Hoogte van de grond (schans of heuvel) op deze plek."""
        h = 0.0
        for sx, sy, dx, dy, L, Wr, Hr in self.ramps:
            rx, ry = x - sx, y - sy
            u = rx * dx + ry * dy
            if 0 <= u <= L and abs(-rx * dy + ry * dx) <= Wr:
                h = max(h, Hr * u / L)
        for mx, my, r, hm in self.mounds:
            d2 = (x - mx) ** 2 + (y - my) ** 2
            if d2 < r * r:
                h = max(h, hm * 0.5 * (1 + math.cos(math.pi * math.sqrt(d2) / r)))
        return h

    def in_pit(self, x, y):
        for px, py, rx, ry in self.pits:
            if ((x - px) / rx) ** 2 + ((y - py) / ry) ** 2 < 1:
                return True
        return False

    def schematic(self, size):
        """Plattegrond (voor het menu en de radar). Geeft (afbeelding, schaal) terug."""
        k = min(size[0] / (self.x1 - self.x0), size[1] / (self.y1 - self.y0))
        s = pygame.Surface((int((self.x1 - self.x0) * k), int((self.y1 - self.y0) * k)), pygame.SRCALPHA)
        th = self.theme

        def P(x, y):
            return ((x - self.x0) * k, (y - self.y0) * k)
        pygame.draw.rect(s, (*dim(th["base"], 0.75), 235), s.get_rect(), border_radius=8)
        pitcol = {"mud": (84, 52, 28), "oil": (16, 14, 20), "ice": (150, 214, 240)}[th["pit"]]
        for px, py, rx, ry in self.pits:
            a, b = P(px - rx, py - ry), P(px + rx, py + ry)
            pygame.draw.ellipse(s, pitcol, (a[0], a[1], b[0] - a[0], b[1] - a[1]))
        for mx, my, r, hm in self.mounds:
            pygame.draw.circle(s, lite(th["base"], 0.2), P(mx, my), r * k)
        for sx, sy, dx, dy, L, Wr, Hr in self.ramps:
            nx, ny = -dy, dx
            pygame.draw.polygon(s, GOLD, [P(sx + nx * Wr, sy + ny * Wr), P(sx - nx * Wr, sy - ny * Wr),
                                          P(sx + dx * L - nx * Wr * 0.6, sy + dy * L - ny * Wr * 0.6), P(sx + dx * L + nx * Wr * 0.6, sy + dy * L + ny * Wr * 0.6)])
        for x, y, a in self.L["wrecks"]:
            pygame.draw.circle(s, (230, 230, 236), P(x, y), max(2, 26 * k))
        for x, y, a in self.L["buses"]:
            c, sn = math.cos(a) * 100, math.sin(a) * 100
            pygame.draw.line(s, (240, 190, 40), P(x - c, y - sn), P(x + c, y + sn), max(2, int(50 * k)))
        for x, y in self.L["barrels"]:
            pygame.draw.circle(s, RED, P(x, y), max(2, 18 * k))
        for x, y, a in self.hoops:
            pygame.draw.circle(s, FIRE, P(x, y), max(3, 44 * k), 2)
        pygame.draw.rect(s, th["wall"][0], s.get_rect(), 3, border_radius=8)
        return s, k

    # ---- objecten aanmaken (bij elke nieuwe ronde opnieuw)
    def make_objects(self):
        sheet = pygame.image.load(SHEET_FILE).convert_alpha()
        cars = []
        for i in WRECK_MODELS:
            cell = sheet.subsurface(((i % 10) * 208, (i // 10) * 112, 208, 112)).copy()
            big = cell.subsurface(cell.get_bounding_rect())
            k = 92 / big.get_width()
            spr = pygame.transform.smoothscale(big, (92, max(8, round(big.get_height() * k))))
            if self.spec["theme"] == "scrap":                # roestig
                spr.fill((200, 170, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
            cars.append(spr)
        rnd = random.Random(self.idx + 1)
        L = self.L
        self.wrecks = [Wreck(x, y, a, rnd.choice(cars)) for x, y, a in L["wrecks"]]
        cols = [(240, 190, 40), (226, 232, 240), (214, 60, 50), (60, 130, 220)]
        self.buses = [Bus(x, y, a, cols[(k // 2 if self.idx != 1 else k) % 4]) for k, (x, y, a) in enumerate(L["buses"])]
        self.barrels = [Thing(x, y, "barrel", 22.0) for x, y in L["barrels"]]
        self.stacks = [Thing(x, y, "stack", 30.0) for x, y in L["stacks"]]
        self.pickups = [Thing(x, y, k, 18.0) for x, y, k in L["pickups"]]
        self.sprites = make_sprites(self.spec["theme"])

    # ---- de wereld tekenen (generator: geeft tussendoor een tekst terug voor het laadscherm)
    def build(self):
        random.seed(self.idx * 17 + 3)
        th = self.theme
        w, h = self.w, self.h
        world = pygame.Surface((w, h))
        world.fill(th["back"])
        floor = pygame.Rect(self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0)
        yield "TRIBUNES VULLEN"
        self._stands(world, floor)
        yield "VLOER AANLEGGEN"
        base = th["base"]
        tile = pygame.Surface((256, 256))
        tile.fill(base)
        for _ in range(2600):
            d = random.randint(-14, 14)
            pygame.draw.circle(tile, (clamp(base[0] + d, 0, 255), clamp(base[1] + d, 0, 255), clamp(base[2] + d, 0, 255)),
                               (random.randrange(256), random.randrange(256)), random.randint(1, 3))
        for y in range(floor.top, floor.bottom, 256):
            for x in range(floor.left, floor.right, 256):
                world.blit(tile, (x, y), pygame.Rect(0, 0, min(256, floor.right - x), min(256, floor.bottom - y)))
        world.set_clip(floor)
        for _ in range(130):                                 # lichte en donkere vlekken
            r = random.randint(100, 330)
            s = pygame.Surface((2 * r, r), pygame.SRCALPHA)
            pygame.draw.ellipse(s, random.choice(th["spots"]), s.get_rect())
            world.blit(s, (random.randint(floor.left, floor.right) - r, random.randint(floor.top, floor.bottom) - r // 2))
        for _ in range(90):                                  # oude bandensporen
            x, y = random.uniform(floor.left + 100, floor.right - 100), random.uniform(floor.top + 100, floor.bottom - 100)
            a = random.uniform(0, TAU)
            pts = []
            for k in range(30):
                a += random.uniform(-0.2, 0.2)
                x += math.cos(a) * 34
                y += math.sin(a) * 34
                pts.append((x, y))
            for off in (-22, 22):
                pygame.draw.lines(world, mix(base, th["track"], 0.7), False, [(px - math.sin(a) * off, py + math.cos(a) * off) for px, py in pts], 9)
        if self.spec["theme"] == "scrap":                    # vervaagde parkeervakken
            for gx in range(floor.left + 200, floor.right - 300, 620):
                for gy in (floor.top + 150, floor.bottom - 260):
                    for k in range(6):
                        pygame.draw.line(world, (150, 140, 90), (gx + k * 60, gy), (gx + k * 60, gy + 110), 4)
                    pygame.draw.line(world, (150, 140, 90), (gx, gy), (gx + 300, gy), 4)
        ring = mix(base, th["wall"][0], 0.55)                # middencirkel met logo
        pygame.draw.circle(world, ring, (w // 2, h // 2), 560, 8)
        pygame.draw.circle(world, ring, (w // 2, h // 2), 536, 3)
        yield "SCHANSEN BOUWEN"
        self._pits(world)
        self._mounds(world)
        self._ramps(world)
        world.set_clip(None)
        self._walls(world, floor)
        yield "SCHIJNWERPERS AAN"
        if th["dark"]:
            dk = pygame.Surface((w, h), pygame.SRCALPHA)
            dk.fill((0, 0, 20, th["dark"]))
            world.blit(dk, (0, 0))
        light = soft(620, th["light"], 60)
        for gx, gy in ((floor.left + 320, floor.top + 270), (floor.right - 320, floor.top + 270), (floor.left + 320, floor.bottom - 270),
                       (floor.right - 320, floor.bottom - 270), (w // 2, h // 2), (w // 2, floor.top + 200), (w // 2, floor.bottom - 200)):
            world.blit(light, (gx - 620, gy - 620))
        for x, y in self.jets:                               # voet van de vlammenwerpers
            pygame.draw.circle(world, (20, 20, 24), (x, y), 17)
            pygame.draw.circle(world, (90, 94, 106), (x, y), 14)
            pygame.draw.circle(world, (30, 30, 34), (x, y), 8)
            pygame.draw.circle(world, FIRE, (x, y), 4)
        self.world = world.convert()
        self.make_objects()
        yield "KLAAR"

    def _stands(self, world, floor):
        w, h = self.w, self.h
        self.stand_rects = [pygame.Rect(0, 0, w, floor.top - 60), pygame.Rect(0, floor.bottom + 60, w, h - floor.bottom - 60),
                            pygame.Rect(0, floor.top - 60, floor.left - 60, floor.height + 120),
                            pygame.Rect(floor.right + 60, floor.top - 60, w - floor.right - 60, floor.height + 120)]
        for bi, b in enumerate(self.stand_rects):
            pygame.draw.rect(world, (30, 26, 32), b)
            horiz = bi < 2
            rows = range(b.top + 8, b.bottom - 6, 17) if horiz else range(b.left + 8, b.right - 6, 17)
            for r in rows:
                if horiz:
                    pygame.draw.rect(world, (44, 38, 46), (b.left, r + 10, b.width, 5))
                else:
                    pygame.draw.rect(world, (44, 38, 46), (r + 10, b.top, 5, b.height))
                for q in (range(b.left + 6, b.right - 4, 12) if horiz else range(b.top + 6, b.bottom - 4, 12)):
                    if (q // 12) % 24 == 0:                  # trap tussen de vakken
                        continue
                    if random.random() < 0.93:
                        c = dark(random.choice(CROWD), random.uniform(0.0, 0.45))
                        x, y = (q, r) if horiz else (r, q)
                        pygame.draw.circle(world, dark(c, 0.5), (x + random.randint(-1, 1), y + 5), 5)
                        pygame.draw.circle(world, c, (x + random.randint(-1, 1), y + random.randint(0, 2)), 4)
                        pygame.draw.circle(world, mix((236, 190, 150), (120, 80, 50), random.random()), (x, y - 2), 2)
        words = ["MONSTER ARENA", "NITRO", "BIG AIR", "CRUSH!", "BACKFLIP", "FULL SEND", "MEGA RAMP", "KABOOM"]
        cols = [self.theme["wall"][0], (255, 190, 30), (40, 150, 230), (236, 232, 224), (150, 220, 60)]
        x, i = 150, 0
        while x < w - 420:                                   # reclameborden boven en onder
            img = font(34).render(words[i % len(words)], True, (20, 14, 10))
            bw = img.get_width() + 44
            for yy in (floor.top - 112, floor.bottom + 66):
                pygame.draw.rect(world, (12, 10, 12), (x + 4, yy + 5, bw, 46), border_radius=6)
                pygame.draw.rect(world, cols[i % 5], (x, yy, bw, 46), border_radius=6)
                pygame.draw.rect(world, lite(cols[i % 5], 0.5), (x + 3, yy + 3, bw - 6, 8), border_radius=4)
                world.blit(img, (x + 22, yy + 1))
            x += bw + 80
            i += 1

    def _pits(self, world):
        kind = self.theme["pit"]
        for px, py, rx, ry in self.pits:
            r = pygame.Rect(px - rx, py - ry, 2 * rx, 2 * ry)
            if kind == "mud":
                pygame.draw.ellipse(world, (150, 100, 58), r.inflate(16, 16))
                pygame.draw.ellipse(world, (86, 54, 30), r)
                pygame.draw.ellipse(world, (112, 74, 44), r.inflate(-rx * 0.5, -ry * 0.6).move(-rx * 0.1, -ry * 0.1))
                pygame.draw.ellipse(world, (170, 134, 100), (px - rx * 0.5, py - ry * 0.55, rx * 0.5, ry * 0.22))
                for _ in range(14):
                    a = random.uniform(0, TAU)
                    pygame.draw.circle(world, (86, 54, 30), (px + math.cos(a) * rx * 1.08, py + math.sin(a) * ry * 1.08), random.randint(4, 10))
            elif kind == "oil":
                pygame.draw.ellipse(world, (16, 14, 20), r)
                for k, c in enumerate(((60, 30, 90), (30, 70, 110), (90, 80, 30))):       # regenboogglans
                    pygame.draw.ellipse(world, c, r.inflate(-rx * (0.3 + 0.3 * k), -ry * (0.3 + 0.3 * k)), 3)
                pygame.draw.ellipse(world, (120, 120, 140), (px - rx * 0.5, py - ry * 0.5, rx * 0.4, ry * 0.16))
            else:
                pygame.draw.ellipse(world, (236, 244, 252), r.inflate(26, 26))
                pygame.draw.ellipse(world, (150, 206, 236), r)
                pygame.draw.ellipse(world, (176, 224, 246), r.inflate(-rx * 0.3, -ry * 0.3))
                for _ in range(46):                          # krassen en glans op het ijs
                    a, d = random.uniform(0, TAU), random.uniform(0, 0.86)
                    x, y = px + math.cos(a) * rx * d, py + math.sin(a) * ry * d
                    ln = random.uniform(30, 120)
                    b = random.uniform(-0.5, 0.5)
                    pygame.draw.line(world, (226, 244, 255), (x, y), (x + math.cos(b) * ln, y + math.sin(b) * ln * 0.5), random.choice((1, 1, 2, 3)))
                pygame.draw.ellipse(world, (120, 180, 220), r, 4)

    def _mounds(self, world):
        base = self.theme["base"]
        for mx, my, r, hm in self.mounds:
            pygame.draw.circle(world, dark(base, 0.3), (mx + 10, my + 14), r)                # schaduwkant
            for i in range(12):
                t = i / 11
                pygame.draw.circle(world, mix(dark(base, 0.08), lite(base, 0.4), t), (int(mx - t * r * 0.16), int(my - t * r * 0.16)), int(r * (1 - t * 0.86)))
            pygame.draw.circle(world, dark(base, 0.3), (int(mx), int(my)), int(r), 3)

    def _ramps(self, world):
        wall = self.theme["wall"]
        for sx, sy, dx, dy, L, Wr, Hr in self.ramps:
            L, Wr = int(L), int(Wr)
            surf = pygame.Surface((L + 60, Wr * 2 + 30), pygame.SRCALPHA)
            ox, oy = 20, 15
            for u in range(L):                               # staalplaat die lichter wordt naar boven toe
                t = u / L
                pygame.draw.line(surf, mix((70, 74, 86), (206, 212, 226), t ** 0.8), (ox + u, oy), (ox + u, oy + 2 * Wr))
            for u in range(0, L, 26):                        # naden tussen de platen
                pygame.draw.line(surf, (48, 50, 60), (ox + u, oy), (ox + u, oy + 2 * Wr), 2)
            for u in range(40, L - 20, 52):                  # gele pijlen
                c = oy + Wr
                pygame.draw.polygon(surf, (255, 206, 40), [(ox + u + 24, c), (ox + u, c - 30), (ox + u, c - 12), (ox + u + 10, c),
                                                           (ox + u, c + 12), (ox + u, c + 30)])
            for y in (oy, oy + 2 * Wr - 12):                 # zijrand: waarschuwingsstrepen
                for u in range(0, L, 24):
                    pygame.draw.rect(surf, wall[(u // 24) % 2], (ox + u, y, min(24, L - u), 12))
                pygame.draw.rect(surf, (30, 30, 36), (ox, y, L, 12), 2)
            pygame.draw.rect(surf, (255, 250, 220), (ox + L - 7, oy, 7, 2 * Wr))             # de lip
            pygame.draw.rect(surf, (40, 42, 50), (ox + L, oy, 12, 2 * Wr))                   # achterkant (steil)
            for y in range(oy + 6, oy + 2 * Wr - 6, 22):
                pygame.draw.line(surf, (90, 94, 106), (ox + L + 1, y), (ox + L + 11, y + 10), 3)
            ang = -math.degrees(math.atan2(dy, dx))
            sh = pygame.Surface((L + 60, Wr * 2 + 30), pygame.SRCALPHA)
            pygame.draw.polygon(sh, (0, 0, 0, 100), [(ox + 30, oy + 6), (ox + L + 12 + Hr * 0.45, oy + 6), (ox + L + 12 + Hr * 0.45, oy + 2 * Wr + 10), (ox + 30, oy + 2 * Wr + 10)])
            rs = pygame.transform.rotate(sh, ang)
            mx, my = sx + dx * L / 2 + dx * 10, sy + dy * L / 2 + dy * 10
            world.blit(rs, rs.get_rect(center=(mx + 10, my + 14)))
            rot = pygame.transform.rotate(surf, ang)
            world.blit(rot, rot.get_rect(center=(mx, my)))

    def _walls(self, world, floor):
        c1, c2 = self.theme["wall"]
        T = 40
        for x in range(floor.left - T, floor.right + T, 56):
            for yy in (floor.top - T, floor.bottom):
                col = c1 if (x // 56) % 2 else c2
                pygame.draw.rect(world, col, (x, yy, 56, T))
                pygame.draw.rect(world, lite(col, 0.35), (x, yy, 56, 7))
                pygame.draw.rect(world, dark(col, 0.35), (x, yy + T - 8, 56, 8))
        for y in range(floor.top - T, floor.bottom + T, 56):
            for xx in (floor.left - T, floor.right):
                col = c1 if (y // 56) % 2 else c2
                pygame.draw.rect(world, col, (xx, y, T, 56))
                pygame.draw.rect(world, lite(col, 0.35), (xx, y, 7, 56))
                pygame.draw.rect(world, dark(col, 0.35), (xx + T - 8, y, 8, 56))
        pygame.draw.rect(world, (20, 18, 20), floor.inflate(2 * T, 2 * T), 4)
        pygame.draw.rect(world, (24, 18, 14), floor.inflate(2, 2), 5)
        for x in range(floor.left + 24, floor.right - 10, 40):                              # bandenmuur aan de binnenkant
            for yy in (floor.top + 12, floor.bottom - 12):
                pygame.draw.circle(world, (18, 18, 20), (x, yy), 17)
                pygame.draw.circle(world, (64, 64, 70), (x, yy), 17, 3)
                pygame.draw.circle(world, (8, 8, 10), (x, yy), 7)
        for y in range(floor.top + 24, floor.bottom - 10, 40):
            for xx in (floor.left + 12, floor.right - 12):
                pygame.draw.circle(world, (18, 18, 20), (xx, y), 17)
                pygame.draw.circle(world, (64, 64, 70), (xx, y), 17, 3)
                pygame.draw.circle(world, (8, 8, 10), (xx, y), 7)
        for cxp, cyp in ((floor.left - 20, floor.top - 20), (floor.right + 20, floor.top - 20), (floor.left - 20, floor.bottom + 20), (floor.right + 20, floor.bottom + 20)):
            pygame.draw.circle(world, (16, 16, 20), (cxp + 5, cyp + 6), 44)                 # lichtmasten in de hoeken
            pygame.draw.circle(world, (70, 74, 86), (cxp, cyp), 42)
            pygame.draw.circle(world, (120, 126, 140), (cxp, cyp), 42, 4)
            for k in range(6):
                a = TAU * k / 6
                pygame.draw.circle(world, (255, 246, 214), (cxp + math.cos(a) * 24, cyp + math.sin(a) * 24), 8)
            pygame.draw.circle(world, (255, 246, 214), (cxp, cyp), 8)
            add_glow(world, cxp, cyp, 420, dim(self.theme["light"], 0.5), 1.6)
