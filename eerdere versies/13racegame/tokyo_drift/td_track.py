"""
td_track.py  -  de circuits van TOKYO DRIFT
Elk circuit is een gesloten lus door controlepunten (x, y, hoogte). Hoogte 0 = straat,
hoogte 1 = verhoogde snelweg / brug. Waar de lus zichzelf kruist rijdt de ene weg
OVER de andere. De wereld wordt in twee lagen getekend:
    world    de grond (stad, water, straten)                 -> onder alle auto's
    tiles    alles wat verhoogd is (opritten, bruggen)       -> boven de auto's op straat
    overs    poorten, borden en torens boven de weg          -> boven alles
"""
import math
import random

import pygame

from td_core import (CYAN, GREEN, J, NEON, ORANGE, PINK, PURPLE, RED, TAU, WHITE, YELLOW, add_glow, clamp, dim,
                     font, mix, vtext)

DS = 12                 # afstand tussen twee punten van de middenlijn (px)
HALF = 112              # halve breedte van het asfalt
WALL = HALF - 12        # zo ver mag het midden van een auto van de middenlijn
LIFT = 30               # zoveel px schuift een weg op hoogte 1 omhoog op het scherm (diepte-effect)
U = 100                 # 1 eenheid in de circuit-tabellen = 100 px
MARGIN = 560
TILE = 256

COURSES = [
    dict(jp="渋谷クロス", name="SHIBUYA CROSS", diff=1, theme=(CYAN, PINK),
         desc="Een acht dwars door Shibuya met een brug in het midden.",
         pts=[(45, 11, 0), (52, 14, 0), (54, 21, 0), (49, 27, 0), (44, 32, 0), (37, 29, 0.45), (30, 22, 1),
              (23, 15, 0.45), (16, 11, 0), (9, 12, 0), (6, 18, 0), (9.5, 24, 0), (15, 26.5, 0), (16, 31.5, 0),
              (21, 35, 0), (26, 30, 0), (30, 22, 0), (37, 15, 0)],
         water=None),
    dict(jp="首都高ループ", name="SHUTO EXPRESSWAY", diff=2, theme=(GREEN, CYAN),
         desc="Oprit op, over de verhoogde snelweg en twee keer onder jezelf door.",
         pts=[(11, 31, 0), (17, 27, 0), (21, 22, 0), (25, 17, 0), (30, 14, 0), (35, 17, 0.5), (39, 22, 1),
              (44, 28, 1), (51, 32, 1), (58, 29, 1), (62, 21, 1), (58, 12, 1), (50, 9, 0.6), (43, 14, 0.12),
              (39, 22, 0), (35, 27, 0), (30, 30, 0), (25, 27, 0.5), (21, 22, 1), (17, 17, 0.8), (11, 13, 0.3),
              (5, 17, 0), (3, 24, 0), (6, 30, 0)],
         water=None),
    dict(jp="湾岸スパイラル", name="WANGAN SPIRAL", diff=3, theme=(PINK, PURPLE),
         desc="De spiraal-oprit van Daikoku en de lange brug over de baai.",
         pts=[(20, 12, 0), (28, 14, 0), (34, 17, 0), (37.5, 21.5, 0.22), (33.5, 25.5, 0.48),
              (29, 21.5, 0.74), (31.5, 16.5, 0.95), (37, 13, 1), (45, 11, 1), (52, 14, 1), (56, 21, 1),
              (55, 29, 1), (50, 35, 1), (43, 37.5, 0.5), (35, 36, 0), (27, 33, 0), (20, 36, 0), (12, 34, 0),
              (7, 28, 0), (9.5, 21.5, 0), (6.5, 17, 0), (10, 12.5, 0)],
         water=[(43, 19.5), (48, 17.5), (70, 16.5), (70, 32.5), (58, 33), (48, 31.5), (43.5, 29), (41.5, 24)]),
]

# (Japans, reserve-tekst): winkels en wijken van Tokyo
SIGNS = [("ラーメン", "RAMEN"), ("居酒屋", "IZAKAYA"), ("焼肉", "YAKINIKU"), ("寿司", "SUSHI"), ("カラオケ", "KARAOKE"),
         ("パチンコ", "PACHINKO"), ("薬局", "PHARMACY"), ("ホテル", "HOTEL"), ("喫茶", "KISSA"), ("麻雀", "MAHJONG"),
         ("酒", "SAKE"), ("営業中", "OPEN"), ("24時間", "24H"), ("歌舞伎町", "KABUKICHO"), ("新宿", "SHINJUKU"),
         ("渋谷", "SHIBUYA"), ("秋葉原", "AKIHABARA"), ("原宿", "HARAJUKU"), ("銀座", "GINZA"), ("池袋", "IKEBUKURO"),
         ("六本木", "ROPPONGI"), ("上野", "UENO"), ("ゲーム", "GAME"), ("カフェ", "CAFE"), ("焼鳥", "YAKITORI"),
         ("天ぷら", "TEMPURA"), ("うどん", "UDON"), ("牛丼", "GYUDON"), ("中華", "CHUKA"), ("電気", "DENKI"),
         ("東京", "TOKYO"), ("おでん", "ODEN"), ("たこ焼き", "TAKOYAKI"), ("ようこそ", "WELCOME"), ("湯", "SENTO"),
         ("ゲームセンター", "ARCADE")]
# grote reclameborden langs de weg: (groot teken, onderschrift)
BILLBOARDS = [("東京", "TOKYO"), ("ドリフト", "DRIFT"), ("走り屋", "HASHIRIYA"), ("峠", "TOUGE"), ("夜", "NIGHT"),
              ("速", "SPEED"), ("魂", "SOUL"), ("夢", "DREAM"), ("風", "WIND"), ("龍", "DRAGON"), ("侍", "SAMURAI"),
              ("最速", "FASTEST"), ("首都高", "SHUTOKO"), ("湾岸", "WANGAN"), ("新宿", "SHINJUKU"), ("渋谷", "SHIBUYA"),
              ("秋葉原", "AKIHABARA"), ("カラオケ", "KARAOKE"), ("ラーメン", "RAMEN"), ("寿司", "SUSHI"),
              ("パチンコ", "PACHINKO"), ("ターボ", "TURBO"), ("全開", "FULL THROTTLE"), ("神", "KAMI")]
ROAD_PAINT = [("止まれ", "STOP"), ("速度落せ", "SLOW"), ("徐行", "SLOW"), ("ドリフト", "DRIFT"), ("40", "40"),
              ("追越禁止", "NO PASS")]


# ------------------------------------------------------------------ neon-onderdelen
def neon_sign(jp, lat, size, color, vertical=False):
    """Neon uithangbord: donker bord met gloeiende rand en gloeiende letters."""
    core = mix(color, (255, 255, 255), 0.55)
    s = J(jp, lat)
    vertical = vertical and s == jp and len(s) > 1

    def txt(c):
        return vtext(s, size, c, True) if vertical else font(size, True).render(s, True, c)
    img = txt(color)
    tw, th = img.get_size()
    pad, m = 6, 5
    w, h = tw + 2 * pad + 2 * m, th + 2 * pad + 2 * m
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    board = pygame.Rect(m, m, w - 2 * m, h - 2 * m)
    for k, a in ((4, 28), (3, 46), (2, 70), (1, 100)):
        pygame.draw.rect(out, (*color, a), board.inflate(2 * k, 2 * k), 2, border_radius=6)
    pygame.draw.rect(out, (10, 8, 20, 240), board, border_radius=5)
    pygame.draw.rect(out, (*core, 255), board, 2, border_radius=5)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        g = img.copy()
        g.set_alpha(80)
        out.blit(g, (m + pad + dx, m + pad + dy))
    out.blit(txt(core), (m + pad, m + pad))
    return out


def make_billboard(jp, lat, color):
    """Groot reclamebord met een enorm Japans teken en een klein onderschrift."""
    core = mix(color, (255, 255, 255), 0.6)
    big = font(46 if len(jp) <= 2 else 34, True).render(J(jp, lat), True, core)
    small = font(13, True).render(lat, True, color)
    w, h = max(big.get_width(), small.get_width()) + 34, big.get_height() + small.get_height() + 14
    out = pygame.Surface((w + 12, h + 12), pygame.SRCALPHA)
    board = pygame.Rect(6, 6, w, h)
    for k, a in ((6, 22), (4, 44), (2, 80)):
        pygame.draw.rect(out, (*color, a), board.inflate(2 * k, 2 * k), 3, border_radius=8)
    pygame.draw.rect(out, (8, 6, 18, 245), board, border_radius=6)
    pygame.draw.rect(out, (*core, 255), board, 3, border_radius=6)
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
        g = font(46 if len(jp) <= 2 else 34, True).render(J(jp, lat), True, color)
        g.set_alpha(90)
        out.blit(g, (6 + (w - big.get_width()) // 2 + dx, 8 + dy))
    out.blit(big, (6 + (w - big.get_width()) // 2, 8))
    out.blit(small, (6 + (w - small.get_width()) // 2, h - small.get_height() + 1))
    off = out.copy()                                              # 'uit'-versie voor het flikkeren
    off.fill((70, 70, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return out, off


def road_paint(jp, lat, size, heading, color=(214, 214, 200), alpha=200, stretch=1.9):
    """Tekst die op het asfalt geschilderd is, uitgerekt in de rijrichting (zoals in Japan)."""
    img = font(size, True).render(J(jp, lat), True, color)
    img = pygame.transform.smoothscale(img, (img.get_width(), int(img.get_height() * stretch)))
    rot = pygame.transform.rotate(img, -math.degrees(heading) - 90)
    rot.set_alpha(alpha)
    return rot


def across(surface, heading, shadow=True):
    """Draait een liggende afbeelding zodat ze dwars over de weg hangt (met slagschaduw)."""
    ang = -math.degrees(heading) - 90
    rot = pygame.transform.rotate(surface, ang)
    if not shadow:
        return rot
    sh = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 90))
    sh = pygame.transform.rotate(sh, ang)
    out = pygame.Surface((rot.get_width() + 40, rot.get_height() + 50), pygame.SRCALPHA)
    out.blit(sh, (34, 44))
    out.blit(rot, (10, 10))
    return out


def make_torii(length):
    g = pygame.Surface((length, 30), pygame.SRCALPHA)
    pygame.draw.rect(g, (196, 30, 34), (0, 4, length, 14), border_radius=3)
    pygame.draw.rect(g, (236, 74, 66), (0, 4, length, 4), border_radius=2)
    pygame.draw.rect(g, (22, 20, 24), (0, 0, length, 5), border_radius=2)
    pygame.draw.rect(g, (170, 24, 30), (length * 0.12, 20, length * 0.76, 6))
    for px in (length * 0.1, length * 0.9):
        pygame.draw.circle(g, (200, 34, 38), (int(px), 14), 9)
        pygame.draw.circle(g, (240, 90, 80), (int(px) - 2, 12), 3)
    return g


def make_footbridge(length, c1, c2):
    d = pygame.Surface((length, 34), pygame.SRCALPHA)
    d.fill((74, 78, 92))
    pygame.draw.rect(d, (130, 136, 152), d.get_rect(), 2)
    pygame.draw.rect(d, c1, (0, 0, length, 3))
    pygame.draw.rect(d, c2, (0, 31, length, 3))
    for x in range(14, length - 20, 26):
        pygame.draw.line(d, (104, 110, 126), (x, 4), (x, 29), 2)
    return d


def make_lanterns(length):
    """Rij rode papieren lantaarns (提灯) aan een kabel over de straat."""
    d = pygame.Surface((length, 26), pygame.SRCALPHA)
    pygame.draw.line(d, (40, 40, 50), (0, 6), (length, 6), 2)
    for x in range(18, length - 10, 30):
        pygame.draw.ellipse(d, (150, 20, 24), (x - 8, 6, 16, 19))
        pygame.draw.ellipse(d, (255, 84, 60), (x - 7, 7, 14, 17))
        pygame.draw.ellipse(d, (255, 210, 150), (x - 3, 10, 6, 10))
        pygame.draw.rect(d, (30, 20, 20), (x - 4, 5, 8, 3))
    return d


def make_gantry(length, panels, start=False):
    """Portaal boven de snelweg met groene Japanse richtingsborden (of het START-bord)."""
    g = pygame.Surface((length, 54), pygame.SRCALPHA)
    pygame.draw.rect(g, (52, 56, 70), (0, 20, length, 12))
    for x in range(0, length, 14):
        pygame.draw.line(g, (96, 102, 120), (x, 20), (x + 7, 31), 2)
        pygame.draw.line(g, (96, 102, 120), (x + 7, 31), (x + 14, 20), 2)
    for px in (6, length - 6):
        pygame.draw.circle(g, (120, 126, 144), (px, 26), 9)
    n = len(panels)
    pw = (length - 60) // n
    for k, (jp, lat) in enumerate(panels):
        r = pygame.Rect(30 + k * pw + 4, 2, pw - 8, 50)
        if start:
            for cx in range(r.x, r.right, 10):
                for cy in range(r.y, r.bottom, 10):
                    pygame.draw.rect(g, (240, 240, 240) if ((cx - r.x) // 10 + (cy - r.y) // 10) % 2 else (20, 20, 24),
                                     (cx, cy, min(10, r.right - cx), min(10, r.bottom - cy)))
            pygame.draw.rect(g, (10, 8, 20), r.inflate(-70, -12))
            col = PINK
        else:
            pygame.draw.rect(g, (10, 96, 62), r, border_radius=5)
            pygame.draw.rect(g, (235, 240, 235), r, 2, border_radius=5)
            col = (240, 245, 240)
        a = font(21, True).render(J(jp, lat), True, col)
        b = font(11, True).render(lat, True, col)
        g.blit(a, a.get_rect(center=(r.centerx, r.y + 18)))
        g.blit(b, b.get_rect(center=(r.centerx, r.y + 40)))
    return g


def draw_sakura(world, x, y, r):
    """Kersenbloesemboom van bovenaf."""
    pygame.draw.circle(world, (6, 6, 12), (x + 8, y + 10), int(r * 0.95))
    for k in range(7):
        a = TAU * k / 7 + random.uniform(-0.2, 0.2)
        pygame.draw.circle(world, (140, 80, 116), (int(x + math.cos(a) * r * 0.5), int(y + math.sin(a) * r * 0.5)), int(r * 0.55))
    for k in range(6):
        a = TAU * k / 6 + random.uniform(-0.3, 0.3)
        pygame.draw.circle(world, (206, 128, 168), (int(x + math.cos(a) * r * 0.38), int(y + math.sin(a) * r * 0.38)), int(r * 0.42))
    for _ in range(int(r * 1.2)):
        a, d = random.uniform(0, TAU), random.uniform(0, r * 0.85)
        pygame.draw.circle(world, random.choice([(255, 196, 220), (240, 170, 205), (255, 220, 235)]),
                           (int(x + math.cos(a) * d), int(y + math.sin(a) * d)), random.randint(1, 3))


def draw_vending(world, x, y):
    """Rijtje drankautomaten (自動販売機): typisch Tokyo, ze geven veel licht."""
    for k in range(random.randint(2, 4)):
        col = random.choice([(235, 240, 255), (255, 80, 80), (80, 160, 255), (255, 220, 90)])
        r = pygame.Rect(x + k * 15, y, 13, 20)
        pygame.draw.rect(world, (10, 10, 16), r.move(3, 4))
        pygame.draw.rect(world, col, r, border_radius=2)
        pygame.draw.rect(world, (245, 250, 255), (r.x + 2, r.y + 2, 9, 8))
        add_glow(world, r.centerx, r.centery + 6, 70, dim(col, 0.35))


class SignPool:
    """Voorraad kant-en-klare neonborden, zodat niet elk gebouw nieuwe tekst moet tekenen."""

    def __init__(self):
        self.h, self.v = [], []
        for jp, lat in SIGNS:
            for _ in range(2):
                col = random.choice(NEON)
                self.h.append((neon_sign(jp, lat, random.choice([15, 17, 20]), col), col))
            if len(jp) <= 4:
                col = random.choice(NEON)
                self.v.append((neon_sign(jp, lat, 17, col, True), col))


def draw_building(world, pool, x, y, bw, bh):
    """Gebouw bij nacht: dak met installaties, verlichte ramen en neonborden."""
    x0, y0 = int(x - bw / 2), int(y - bh / 2)
    pygame.draw.rect(world, (5, 5, 11), (x0 + 12, y0 + 16, bw + 8, bh + 10), border_radius=4)
    fh, fw = random.randint(18, 28), random.randint(10, 16)
    pygame.draw.rect(world, (16, 18, 30), (x0, y0 + bh - 4, bw, fh + 4))
    pygame.draw.rect(world, (12, 14, 24), (x0 + bw - 4, y0 + 6, fw + 4, bh + fh - 6))
    lit = random.choice([(255, 226, 150), (190, 230, 255), (255, 205, 130), (255, 240, 210), (255, 150, 200)])
    for wx in range(x0 + 5, x0 + bw - 8, 11):
        for wy in range(y0 + bh + 2, y0 + bh + fh - 3, 10):
            pygame.draw.rect(world, lit if random.random() < 0.55 else (26, 30, 46), (wx, wy, 6, 6))
    for wy in range(y0 + 12, y0 + bh + fh - 6, 11):
        col = lit if random.random() < 0.5 else (22, 26, 40)
        pygame.draw.rect(world, dim(col, 0.7), (x0 + bw + 2, wy, 6, 6))
    roof = random.choice([(50, 54, 76), (58, 62, 84), (42, 46, 68), (68, 58, 74), (44, 60, 76), (54, 52, 66)])
    pygame.draw.rect(world, roof, (x0, y0, bw, bh), border_radius=3)
    pygame.draw.rect(world, mix(roof, (150, 160, 190), 0.35), (x0, y0, bw, bh), 2, border_radius=3)
    pygame.draw.rect(world, dim(roof, 0.75), (x0 + 6, y0 + 6, bw - 12, bh - 12), 1)
    for _ in range(random.randint(1, 4)):                                       # airco's
        ax, ay = random.randint(x0 + 8, x0 + bw - 24), random.randint(y0 + 8, y0 + bh - 22)
        pygame.draw.rect(world, (96, 100, 112), (ax, ay, 16, 12), border_radius=2)
        pygame.draw.circle(world, (36, 38, 48), (ax + 8, ay + 6), 4)
    kind = random.random()
    cx, cy = x0 + bw // 2, y0 + bh // 2
    if kind < 0.16 and min(bw, bh) > 110:                                       # helikopterplatform
        pygame.draw.circle(world, (40, 44, 58), (cx, cy), 28)
        pygame.draw.circle(world, (230, 200, 60), (cx, cy), 28, 2)
        img = font(26, True).render("H", True, (230, 200, 60))
        world.blit(img, img.get_rect(center=(cx, cy)))
        add_glow(world, cx, cy, 90, (60, 20, 20))
    elif kind < 0.34 and min(bw, bh) > 100:                                     # dak-neon: een groot teken
        col = random.choice(NEON)
        jp, lat = random.choice(BILLBOARDS[:12])
        img = font(40, True).render(J(jp, lat)[:2] if J(jp, lat) == jp else lat[:3], True, mix(col, (255, 255, 255), 0.4))
        if img.get_width() < bw - 10:
            world.blit(img, img.get_rect(center=(cx, cy)))
            add_glow(world, cx, cy, 190, dim(col, 0.32), 1.6)
    elif kind < 0.48:                                                           # watertank
        pygame.draw.circle(world, (30, 32, 42), (cx + 5, cy + 6), 15)
        pygame.draw.circle(world, (120, 126, 140), (cx, cy), 15)
        pygame.draw.circle(world, (170, 176, 190), (cx - 3, cy - 3), 8)
    if random.random() < 0.85:                                                  # liggend neonbord aan de gevel
        sg, col = random.choice(pool.h)
        if sg.get_width() > bw:
            sg = pygame.transform.smoothscale(sg, (bw - 4, max(10, int(sg.get_height() * (bw - 4) / sg.get_width()))))
        world.blit(sg, sg.get_rect(center=(cx, y0 + bh + fh // 2 + 2)))
        add_glow(world, cx, y0 + bh + fh // 2, 170, dim(col, 0.32), 1.8)
    if random.random() < 0.7 and bh > 80:                                       # staand neonbord aan de zijkant
        sg, col = random.choice(pool.v)
        sx = x0 - 2 if random.random() < 0.5 else x0 + bw + 6
        sy = cy + random.randint(-12, 12)
        world.blit(sg, sg.get_rect(center=(sx, sy)))
        add_glow(world, sx, sy, 150, dim(col, 0.30), 1.8)


def in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


# ------------------------------------------------------------------ het circuit
class Track:
    def __init__(self, spec):
        self.spec = spec
        self.theme = spec["theme"]
        ctrl = [(x * U, y * U, z) for x, y, z in spec["pts"]]
        m = len(ctrl)
        dense = []
        for i in range(m):                                  # vloeiende kromme door de controlepunten
            p0, p1, p2, p3 = ctrl[i - 1], ctrl[i], ctrl[(i + 1) % m], ctrl[(i + 2) % m]
            for k in range(24):
                t = k / 24
                t2, t3 = t * t, t * t * t
                xy = [0.5 * (2 * p1[a] + (p2[a] - p0[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2
                             + (3 * p1[a] - p0[a] - 3 * p2[a] + p3[a]) * t3) for a in (0, 1)]
                dense.append((xy[0], xy[1], p1[2] + (p2[2] - p1[2]) * t))
        # opnieuw verdelen: om de DS pixels een punt
        cum = [0.0]
        for i in range(len(dense)):
            a, b = dense[i], dense[(i + 1) % len(dense)]
            cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        n = int(cum[-1] / DS)
        step = cum[-1] / n
        pts, zs, j = [], [], 0
        for i in range(n):
            d = i * step
            while cum[j + 1] < d:
                j += 1
            a, b = dense[j], dense[(j + 1) % len(dense)]
            t = (d - cum[j]) / max(1e-9, cum[j + 1] - cum[j])
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            zs.append(a[2] + (b[2] - a[2]) * t)
        zs = [sum(zs[(i + k) % n] for k in range(-9, 10)) / 19 for i in range(n)]       # hellingen afronden
        zs = [0.0 if z < 0.012 else min(1.0, z) for z in zs]
        minx, miny = min(p[0] for p in pts) - MARGIN, min(p[1] for p in pts) - MARGIN
        self.pts = [(p[0] - minx, p[1] - miny) for p in pts]
        self.z = zs
        self.n = n
        self.w = int(max(p[0] for p in self.pts) + MARGIN)
        self.h = int(max(p[1] for p in self.pts) + MARGIN)
        self.water = [(x * U - minx, y * U - miny) for x, y in spec["water"]] if spec["water"] else None
        self.headings, self.normals = [], []
        for i in range(n):
            a, b = self.pts[i - 1], self.pts[(i + 1) % n]
            h = math.atan2(b[1] - a[1], b[0] - a[0])
            self.headings.append(h)
            self.normals.append((-math.sin(h), math.cos(h)))          # wijst naar RECHTS van de rijrichting
        raw = [((self.headings[(i + 1) % n] - self.headings[i - 1] + math.pi) % TAU - math.pi) / (2 * DS) for i in range(n)]
        self.curv = [sum(raw[(i + k) % n] for k in range(-4, 5)) / 9 for i in range(n)]
        self.up = [z > 0 for z in zs]
        self.zmax = [max(zs[(i + k) % n] for k in range(-6, 7)) for i in range(n)]       # voor de tekenlaag van auto's
        self.length_m = int(n * DS / 10)
        self.elev_pct = int(100 * sum(self.up) / n)
        self._find_zones()
        self.world = None

    # ---- meetkunde
    def P(self, i, lat=0.0, lift=True):
        """Punt op de weg: index i, 'lat' px naar rechts van de middenlijn. lift = verhoogd tekenen."""
        i %= self.n
        x, y = self.pts[i]
        nx, ny = self.normals[i]
        return (x + nx * lat, y + ny * lat - (self.z[i] * LIFT if lift else 0))

    def _find_zones(self):
        """Driftzones: de scherpste bochten. Daar krijg je dubbele punten en ligt een clipping point."""
        self.zones, self.zone_at = [], [-1] * self.n
        i = 0
        while i < self.n:
            if abs(self.curv[i]) > 1 / 600:
                j = i
                while j < self.n - 1 and abs(self.curv[j + 1]) > 1 / 720 and self.curv[j + 1] * self.curv[i] > 0:
                    j += 1
                if j - i >= 18 and i > 12:
                    apex = max(range(i, j + 1), key=lambda k: abs(self.curv[k]))
                    side = 1 if self.curv[apex] > 0 else -1
                    for k in range(i, j + 1):
                        self.zone_at[k] = len(self.zones)
                    self.zones.append(dict(a=i, b=j, apex=apex, side=side))
                i = j + 1
            else:
                i += 1

    def minimap(self, size, ground=CYAN, high=PINK, width=3):
        """Kaartje van het circuit: straat in de ene kleur, verhoogde stukken in de andere."""
        sw, sh = size
        k = min((sw - 16) / (self.w - 2 * MARGIN + 300), (sh - 16) / (self.h - 2 * MARGIN + 300))
        ox = (sw - self.w * k) / 2
        oy = (sh - self.h * k) / 2
        surf = pygame.Surface(size, pygame.SRCALPHA)
        if self.water:
            pygame.draw.polygon(surf, (20, 40, 110, 150), [(ox + x * k, oy + y * k) for x, y in self.water])
        P = [(ox + x * k, oy + y * k) for x, y in self.pts]
        for i in range(0, self.n, 2):
            if not (self.up[i] and self.up[(i + 2) % self.n]):
                pygame.draw.line(surf, ground, P[i], P[(i + 2) % self.n], width)
        for col, wd in (((8, 6, 20), width + 5), (high, width + 1)):
            for i in range(0, self.n, 2):
                if self.up[i] or self.up[(i + 2) % self.n]:
                    pygame.draw.line(surf, col, P[i], P[(i + 2) % self.n], wd)
        pygame.draw.circle(surf, (255, 255, 255), P[0], width + 2)
        return surf, k, ox, oy

    def _make_grid(self):
        """Rooster met de afstand tot de dichtste weg (om gebouwen en bomen vrij van de weg te houden)."""
        c = self.cell = 40
        gw, gh = self.w // c + 2, self.h // c + 2
        g = [[999.0] * gw for _ in range(gh)]
        gu = [[999.0] * gw for _ in range(gh)]              # idem, maar alleen tot de verhoogde wegen
        for i in range(0, self.n, 2):
            todo = [(g, self.P(i, 0, False))]
            if self.up[i]:
                todo += [(g, self.P(i, 0, True)), (gu, self.P(i, 0, True))]
            for grid, (px, py) in todo:
                cx, cy = int(px // c), int(py // c)
                for gy in range(max(0, cy - 10), min(gh, cy + 11)):
                    row = grid[gy]
                    dy = (gy + 0.5) * c - py
                    for gx in range(max(0, cx - 10), min(gw, cx + 11)):
                        d = math.hypot((gx + 0.5) * c - px, dy)
                        if d < row[gx]:
                            row[gx] = d
        self.grid, self.grid_up = g, gu

    def under(self, x, y):
        """Ligt dit punt van de straat onder een verhoogde weg?"""
        gx, gy = int(x // self.cell), int(y // self.cell)
        return 0 <= gy < len(self.grid_up) and 0 <= gx < len(self.grid_up[0]) and self.grid_up[gy][gx] < HALF + 8

    def dist(self, x, y):
        gx, gy = int(x // self.cell), int(y // self.cell)
        if 0 <= gy < len(self.grid) and 0 <= gx < len(self.grid[0]):
            return self.grid[gy][gx]
        return 999.0

    def wet(self, x, y):
        return self.water is not None and in_poly(x, y, self.water)

    def strip(self, surf, segs, a, b, color, lift=True, dx=0, dy=0):
        """Tekent een strook langs de weg tussen 'a' en 'b' px van de middenlijn."""
        for i in segs:
            p = [self.P(i, a, lift), self.P(i, b, lift), self.P(i + 1, b, lift), self.P(i + 1, a, lift)]
            if dx or dy:
                p = [(x + dx, y + dy) for x, y in p]
            pygame.draw.polygon(surf, color, p)

    # ---- de wereld tekenen (generator: geeft tussendoor een tekst terug voor het laadscherm)
    def build(self):
        random.seed(self.spec["name"])
        n = self.n
        c1, c2 = self.theme
        yield J("地図を作成中", "KAART MAKEN")
        self._make_grid()
        pool = SignPool()
        world = pygame.Surface((self.w, self.h))
        tile = pygame.Surface((256, 256))
        tile.fill((17, 18, 30))
        for _ in range(2400):
            d = random.randint(-6, 7)
            pygame.draw.circle(tile, (20 + d, 22 + d, 34 + d), (random.randrange(256), random.randrange(256)), random.randint(1, 2))
        for ty in range(0, self.h, 256):
            for tx in range(0, self.w, 256):
                world.blit(tile, (tx, ty))
        ground = [i for i in range(n) if not (self.up[i] and self.up[(i + 1) % n])]
        upper = [i for i in range(n) if self.up[i] or self.up[(i + 1) % n]]
        self.live = []                                       # flikkerende neonborden: (aan, uit, x, y, kleur, fase)
        self.overs = []                                      # afbeeldingen boven alles: (afbeelding, x, y)

        # ---- water (de baai van Tokyo)
        if self.water:
            pygame.draw.polygon(world, (6, 12, 34), self.water)
            xs, ys = [p[0] for p in self.water], [p[1] for p in self.water]
            for _ in range(2600):
                x, y = random.uniform(min(xs), max(xs)), random.uniform(min(ys), max(ys))
                if self.wet(x, y) and self.wet(x + 30, y):
                    if random.random() < 0.25:                # neon dat weerspiegelt in het water
                        col = dim(random.choice(NEON), random.uniform(0.2, 0.5))
                        for k in range(random.randint(3, 7)):
                            pygame.draw.line(world, col, (x + random.randint(-3, 3), y + k * 4), (x + random.randint(8, 22), y + k * 4), 2)
                    else:
                        pygame.draw.line(world, (16, 30, 66), (x, y), (x + random.randint(8, 30), y), 1)
            pygame.draw.lines(world, (70, 72, 90), True, self.water, 9)
            pygame.draw.lines(world, (120, 124, 146), True, self.water, 2)
            for k in range(len(self.water)):                  # kade-lampjes
                a, b = self.water[k], self.water[(k + 1) % len(self.water)]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                for s in range(0, int(L), 90):
                    x, y = a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L
                    add_glow(world, x, y, 60, (90, 60, 20))
                    pygame.draw.circle(world, (255, 220, 150), (x, y), 2)
            for _ in range(7):                                # bootjes
                x, y = random.uniform(min(xs), max(xs)), random.uniform(min(ys), max(ys))
                if self.wet(x, y) and self.dist(x, y) > 260 and self.wet(x - 60, y) and self.wet(x + 60, y):
                    pygame.draw.polygon(world, (210, 214, 226), [(x - 30, y - 9), (x + 18, y - 9), (x + 34, y), (x + 18, y + 9), (x - 30, y + 9)])
                    pygame.draw.rect(world, (90, 96, 116), (x - 16, y - 5, 22, 10))
                    for lx, col in ((-28, RED), (30, GREEN), (0, YELLOW)):
                        add_glow(world, x + lx, y, 50, dim(col, 0.5))
        yield J("ビルを建設中", "GEBOUWEN PLAATSEN")

        # ---- gebouwen in een dicht raster (Tokyo is vol!)
        cw, ch = 214, 204
        for gy in range(0, self.h // ch + 1):
            for gx in range(0, self.w // cw + 1):
                bw, bh = random.randint(110, 176), random.randint(100, 150)
                x = gx * cw + cw // 2 + random.randint(-8, 8)
                y = gy * ch + ch // 2 + random.randint(-8, 8)
                if self.dist(x, y) < HALF + 80 + max(bw, bh) * 0.62:
                    bw, bh = int(bw * 0.6), int(bh * 0.6)                       # kleiner gebouw vlak bij de weg
                    if self.dist(x, y) < HALF + 70 + max(bw, bh) * 0.62:
                        continue
                if self.water and any(self.wet(x + dx * bw * 0.7, y + dy * bh * 0.8) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    continue
                draw_building(world, pool, x, y, bw, bh)
            if gy % 4 == 0:
                yield J("ビルを建設中", "GEBOUWEN PLAATSEN")
        yield J("道路を舗装中", "WEGEN AANLEGGEN")

        # ---- straat (hoogte 0)
        self.strip(world, ground, -HALF - 26, HALF + 26, (40, 42, 56), False)             # stoep
        self.strip(world, ground, -HALF - 6, HALF + 6, (92, 94, 110), False)              # stoeprand
        self.strip(world, ground, -HALF, HALF, (29, 30, 41), False)                       # asfalt
        for i in ground:
            if abs(self.curv[i]) > 1 / 800 and i % 2 == 0:                                # rood-witte kerbs in bochten
                col = (214, 40, 50) if (i // 2) % 2 else (236, 236, 240)
                self.strip(world, [i, (i + 1) % n], -HALF, -HALF + 9, col, False)
                self.strip(world, [i, (i + 1) % n], HALF - 9, HALF, col, False)
        self.strip(world, ground, -HALF + 14, -HALF + 17, (200, 200, 190), False)         # kantlijnen
        self.strip(world, ground, HALF - 17, HALF - 14, (200, 200, 190), False)
        self.strip(world, [i for i in ground if i % 8 < 4], -2, 2, (226, 150, 40), False)  # oranje middenstreep
        self._paint_ground(world, ground)
        yield J("高架を建設中", "SNELWEG BOUWEN")

        # ---- verhoogde laag: schaduw, pijlers, dek, vangrail met neon
        ov = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.ramp_marks = []
        self._draw_upper(ov, upper)
        yield J("ネオンを点灯中", "NEON AANSTEKEN")
        self._props(world, ov, pool, ground, upper)
        self._drift_zones(world, ov)
        self._start_line(world)

        self.tiles = {}
        for ty in range(0, self.h, TILE):
            for tx in range(0, self.w, TILE):
                r = pygame.Rect(tx, ty, min(TILE, self.w - tx), min(TILE, self.h - ty))
                sub = ov.subsurface(r)
                if sub.get_bounding_rect().w:
                    self.tiles[(tx // TILE, ty // TILE)] = sub.copy().convert_alpha()
        del ov
        self.world = world.convert()
        yield J("準備完了", "KLAAR")

    def _paint_ground(self, world, ground):
        n = self.n
        gset = set(ground)
        k = 0
        for i in range(40, n - 30, 46):                       # Japanse tekst op het wegdek + zebrapaden
            if not all(((i + d) % n) in gset and self.z[(i + d) % n] == 0 for d in range(-8, 9)):
                continue
            if abs(self.curv[i]) > 1 / 700:
                continue
            k += 1
            if k % 3 == 0:                                    # zebrapad
                for lat in range(-HALF + 22, HALF - 26, 20):
                    self.strip(world, [i, i + 1, i + 2, i + 3], lat, lat + 10, (206, 206, 196), False)
            else:
                jp, lat = ROAD_PAINT[(k * 5) % len(ROAD_PAINT)]
                for side in (-1, 1):
                    img = road_paint(jp, lat, 26, self.headings[i])
                    x, y = self.P(i, side * HALF * 0.5, False)
                    world.blit(img, img.get_rect(center=(x, y)))

    def _draw_upper(self, ov, upper):
        n = self.n
        c1, c2 = self.theme
        rainbow = self.water is not None
        self.strip(ov, upper, -HALF - 22, HALF + 22, (0, 0, 0, 105), False, 26, 40)      # slagschaduw op de grond
        ground_pts = [self.pts[i] for i in range(0, n, 3) if not self.up[i]]
        for i in upper:                                                                    # pijlers
            if i % 14 == 0 and self.z[i] > 0.2:
                for side in (-1, 1):
                    gx, gy = self.P(i, side * (HALF + 4), False)
                    if all((gx - px) ** 2 + (gy - py) ** 2 > (HALF + 34) ** 2 for px, py in ground_pts) and not self.wet(gx, gy):
                        tx, ty = self.P(i, side * (HALF + 4), True)
                        pygame.draw.line(ov, (30, 32, 44), (gx, gy + 6), (tx, ty + 6), 22)
                        pygame.draw.circle(ov, (30, 32, 44), (gx, gy + 6), 11)
                        pygame.draw.line(ov, (52, 54, 70), (gx - 4, gy + 6), (tx - 4, ty + 6), 6)
        for k in range(5):                                                                 # zijkant van het dek
            f = 0.68 + 0.08 * k
            for i in upper:
                p = []
                for j, lat in ((i, -HALF - 20), (i, HALF + 20), (i + 1, HALF + 20), (i + 1, -HALF - 20)):
                    x, y = self.P(j, lat, False)
                    p.append((x, y - self.z[j % n] * LIFT * f))
                pygame.draw.polygon(ov, (20, 21, 32) if k < 4 else (36, 38, 52), p)
        self.strip(ov, upper, -HALF - 20, HALF + 20, (84, 86, 102))                        # betonnen rand
        self.strip(ov, upper, -HALF - 6, HALF + 6, (112, 114, 130))
        self.strip(ov, upper, -HALF, HALF, (36, 38, 52))                                   # asfalt (iets blauwer)
        for i in upper:
            if i % 26 == 0:                                                                # voegen in het wegdek
                pygame.draw.line(ov, (22, 23, 34), self.P(i, -HALF), self.P(i, HALF), 3)
        self.strip(ov, upper, -HALF + 12, -HALF + 15, (214, 214, 206))
        self.strip(ov, upper, HALF - 15, HALF - 12, (214, 214, 206))
        dash = [i for i in upper if i % 8 < 4]
        self.strip(ov, dash, -HALF / 3 - 1.5, -HALF / 3 + 1.5, (214, 214, 206))
        self.strip(ov, dash, HALF / 3 - 1.5, HALF / 3 + 1.5, (214, 214, 206))
        # neon-ledstrips op de vangrail (regenboogkleuren op de brug over de baai)
        for i in upper:
            if rainbow and self.wet(*self.pts[i]):
                h = pygame.Color(0, 0, 0)
                h.hsva = ((i * 3) % 360, 85, 100, 100)
                ca = cb = (h.r, h.g, h.b)
            else:
                ca, cb = c1, c2
            self.strip(ov, [i], -HALF - 5, -HALF - 1, ca)
            self.strip(ov, [i], HALF + 1, HALF + 5, cb)
            if i % 5 == 0:
                for lat, col in ((-HALF - 3, ca), (HALF + 3, cb)):
                    x, y = self.P(i, lat)
                    add_glow(ov, x, y, 96, dim(col, 0.30), 1.7)
        k = 0
        for i in range(30, n - 20, 58):                                                    # tekst op het wegdek
            if all(self.z[(i + d) % n] >= 1 for d in range(-6, 7)) and abs(self.curv[i]) < 1 / 500:
                k += 1
                jp, lat = [("首都高", "SHUTOKO"), ("80", "80"), ("湾岸", "WANGAN"), ("追越", "PASS")][k % 4]
                img = road_paint(jp, lat, 24, self.headings[i])
                x, y = self.P(i, 0)
                ov.blit(img, img.get_rect(center=(x, y)))
        # borden bij het begin/einde van elke helling + portalen boven de snelweg
        gk = 0
        for i in range(n):
            a, b = self.z[i - 1], self.z[i]
            if a == 0 and b > 0:                                                           # oprit begint
                for side in (-1, 1):
                    img = road_paint("入口", "IN", 26, self.headings[i - 14], (120, 255, 170), 220)
                    x, y = self.P(i - 14, side * HALF * 0.5, False)
                    self.ramp_marks.append((img, x, y))
            if a >= 1 > b:                                                                 # afrit begint
                img = road_paint("出口", "EXIT", 26, self.headings[i - 8], (255, 220, 90), 220)
                x, y = self.P(i - 8, 0)
                ov.blit(img, img.get_rect(center=(x, y)))
            if b >= 1 and i % 150 == 75 and all(self.z[(i + d) % n] >= 1 for d in (-12, 12)):
                gk += 1
                panels = [[("首都高速", "SHUTO EXPWY"), ("渋谷 ↑", "SHIBUYA")], [("湾岸線", "WANGAN LINE"), ("横浜 ↑", "YOKOHAMA")],
                          [("新宿 ↑", "SHINJUKU"), ("銀座 出口", "GINZA EXIT")]][gk % 3]
                g = across(make_gantry(2 * HALF + 70, panels), self.headings[i])
                x, y = self.P(i, 0)
                self.overs.append((g, x - g.get_width() / 2, y - g.get_height() / 2))
        if rainbow:                                                                        # torens en kabels van de baaibrug
            wet = [i for i in range(n) if self.wet(*self.pts[i])]
            if wet:
                a, b = wet[0], wet[-1]
                for t in (a + (b - a) // 4, a + 3 * (b - a) // 4):
                    for side in (-1, 1):
                        top = self.P(t, side * (HALF + 12))
                        for d in range(-60, 61, 6):
                            if d:
                                pygame.draw.line(ov, (150, 156, 180), top, self.P(t + d, side * (HALF + 12)), 1)
                    tw = pygame.Surface((2 * HALF + 80, 26), pygame.SRCALPHA)
                    pygame.draw.rect(tw, (206, 210, 226), (0, 6, tw.get_width(), 14), border_radius=4)
                    pygame.draw.rect(tw, (120, 124, 146), (0, 6, tw.get_width(), 14), 2, border_radius=4)
                    for px in (13, tw.get_width() - 13):
                        pygame.draw.rect(tw, (236, 238, 248), (px - 13, 0, 26, 26), border_radius=4)
                        pygame.draw.circle(tw, RED, (px, 13), 4)
                    g = across(tw, self.headings[t % n])
                    x, y = self.P(t, 0)
                    self.overs.append((g, x - g.get_width() / 2, y - g.get_height() / 2))
                    add_glow(ov, x, y, 300, (40, 40, 60), 1.5)

    def _props(self, world, ov, pool, ground, upper):
        """Lantaarns, bomen, automaten, reclameborden, torii, voetgangersbruggen en lantaarn-slingers."""
        n = self.n
        c1, c2 = self.theme
        for img, x, y in self.ramp_marks:
            world.blit(img, img.get_rect(center=(x, y)))
        gset = set(ground)
        for i in ground:                                      # straatlantaarns (warm oranje natriumlicht)
            if i % 18 == 0:
                side = 1 if (i // 18) % 2 else -1
                x, y = self.P(i, side * (HALF + 14), False)
                add_glow(world, *self.P(i, side * (HALF - 40), False), 300, (70, 44, 16), 1.5)
                pygame.draw.line(world, (60, 62, 76), (x, y), self.P(i, side * (HALF - 14), False), 3)
                pygame.draw.circle(world, (255, 214, 150), self.P(i, side * (HALF - 14), False), 4)
        for i in upper:                                       # snelweglampen (koel wit)
            if i % 16 == 0 and self.z[i] > 0.3:
                for side in (-1, 1):
                    x, y = self.P(i, side * (HALF - 26))
                    add_glow(ov, x, y, 230, (26, 34, 46), 1.6)
                    pygame.draw.circle(ov, (220, 240, 255), self.P(i, side * (HALF + 9)), 3)
        # vangrail langs de straat
        for i in ground:
            if i % 3 == 0:
                for side in (-1, 1):
                    pygame.draw.circle(world, (150, 154, 170), self.P(i, side * (HALF + 3), False), 2)
        self.strip(world, ground, -HALF - 4, -HALF - 2, (120, 124, 140), False)
        self.strip(world, ground, HALF + 2, HALF + 4, (120, 124, 140), False)

        k = 0
        for i in range(8, n, 9):                              # spullen langs de weg
            if i not in gset:
                continue
            for side in (-1, 1):
                k += 1
                lat = side * (HALF + 62)
                x, y = self.P(i, lat, False)
                if self.dist(x, y) < HALF + 40 or self.wet(x, y):
                    continue
                r = (k * 7919) % 10
                if r < 3:
                    draw_sakura(world, int(x), int(y), random.randint(20, 28))
                elif r < 5:
                    draw_vending(world, int(x) - 20, int(y) - 10)
                elif r == 5:
                    pygame.draw.circle(world, (255, 120, 40), (x, y), 5)       # verkeerskegel
                    pygame.draw.circle(world, (255, 240, 230), (x, y), 2)
        bb = 0
        placed = []
        for i in range(20, n, 30):                            # grote flikkerende reclameborden
            for side in ((1, -1) if (i // 30) % 2 else (-1, 1)):
                jp, lat = BILLBOARDS[(bb * 5 + i) % len(BILLBOARDS)]
                col = NEON[(bb * 3 + i) % 7]
                on, off = make_billboard(jp, lat, col)
                w, h = on.get_size()
                x, y = self.P(i, side * (HALF + 70 + max(w, h) * 0.55), False)
                box = pygame.Rect(0, 0, w + 20, h + 20)
                box.center = (x, y)
                ok = all(self.dist(x + dx * w / 2, y + dy * h / 2) > HALF + 34 and not self.wet(x + dx * w / 2, y + dy * h / 2)
                         for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                if ok and box.collidelist(placed) < 0:
                    placed.append(box)
                    pygame.draw.rect(world, (6, 6, 12), box.inflate(-14, -14).move(8, 10), border_radius=6)
                    add_glow(world, x, y, int(max(w, h) * 2.4), dim(col, 0.22), 1.5)
                    self.live.append((on, off, int(x - w / 2), int(y - h / 2), col, random.uniform(0, 100)))
                    bb += 1
                    break
        # boven de weg: torii, voetgangersbruggen en lantaarn-slingers (alleen op vlakke straat)
        k = 0
        for i in range(60, n - 40, 70):
            if all(((i + d) % n) in gset and self.zmax[(i + d) % n] == 0 for d in (-20, 0, 20)) and abs(self.curv[i]) < 1 / 600:
                far = all((self.pts[i][0] - self.pts[j][0]) ** 2 + (self.pts[i][1] - self.pts[j][1]) ** 2 > 330 ** 2
                          for j in range(0, n, 4) if self.up[j])
                if not far:
                    continue
                k += 1
                L = 2 * HALF + 70
                img = [make_torii(L), make_footbridge(L + 30, c1, c2), make_lanterns(L - 20)][k % 3]
                g = across(img, self.headings[i])
                x, y = self.pts[i]
                self.overs.append((g, x - g.get_width() / 2, y - g.get_height() / 2))
                if k % 3 == 2:
                    add_glow(world, x, y, 320, (70, 20, 12), 1.4)

    def _drift_zones(self, world, ov):
        """Neon-pijlen langs elke driftzone en een gloeiend clipping point in de binnenbocht."""
        for zi, z in enumerate(self.zones):
            col = (PINK, CYAN, YELLOW, GREEN)[zi % 4]
            for i in range(z["a"], z["b"] + 1, 3):
                surf, lift = (ov, True) if self.up[i] else (world, False)
                lat = -z["side"] * (HALF - 30)                # pijlen aan de buitenkant van de bocht
                x, y = self.P(i, lat, lift)
                h = self.headings[i]
                fx, fy, rx, ry = math.cos(h), math.sin(h), -math.sin(h), math.cos(h)
                pts = [(x - fx * 9 + rx * 8, y - fy * 9 + ry * 8), (x + fx * 7, y + fy * 7), (x - fx * 9 - rx * 8, y - fy * 9 - ry * 8)]
                pygame.draw.lines(surf, col, False, pts, 3)
                if i % 6 == 0:
                    add_glow(surf, x, y, 70, dim(col, 0.35))
            a = z["apex"]
            surf, lift = (ov, True) if self.up[a] else (world, False)
            x, y = self.P(a, z["side"] * (HALF - 24), lift)
            z["clip"] = self.P(a, z["side"] * (HALF - 24), False)
            pygame.draw.circle(surf, (255, 255, 255), (x, y), 12, 3)
            pygame.draw.circle(surf, YELLOW, (x, y), 6)
            add_glow(surf, x, y, 150, (90, 80, 20), 1.6)
            img = road_paint("ドリフト", "DRIFT", 22, self.headings[z["a"]], col, 230)
            x, y = self.P(z["a"] - 4, 0, self.up[z["a"]])
            surf2 = ov if self.up[z["a"]] and self.up[z["a"] - 4] else world
            surf2.blit(img, img.get_rect(center=(x, y)))

    def _start_line(self, world):
        for k in range(-HALF + 2, HALF - 2, 10):
            for r in range(2):
                col = (240, 240, 240) if ((k // 10) + r) % 2 else (16, 16, 20)
                self.strip(world, [r], k, k + 10, col, False)
        for g in range(8):                                    # startvakken
            i = -6 - g * 6
            lat = 46 if g % 2 else -46
            for a, b in ((lat - 26, lat - 23), (lat + 23, lat + 26)):
                self.strip(world, [i - 1, i, i + 1], a, b, (214, 214, 206), False)
            self.strip(world, [i + 2], lat - 26, lat + 26, (214, 214, 206), False)
        g = across(make_gantry(2 * HALF + 70, [("スタート", "START / FINISH")], True), self.headings[0])
        x, y = self.pts[0]
        self.overs.append((g, x - g.get_width() / 2, y - g.get_height() / 2))
        add_glow(world, x, y, 380, (60, 16, 40), 1.4)
