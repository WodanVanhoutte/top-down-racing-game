"""
td_track.py  -  de circuits van TOKYO DRIFT
Elk circuit is een gesloten lus door controlepunten (x, y, hoogte). Hoogte 0 = straat,
hoogte 1 = verhoogde snelweg / brug. Waar de lus zichzelf kruist rijdt de ene weg
OVER de andere. De wereld wordt in twee lagen getekend:
    world    de grond (stad, water, straten)                 -> onder alle auto's
    tiles    alles wat verhoogd is (opritten, bruggen)       -> boven de auto's op straat
    overs    poorten, borden en torens boven de weg          -> boven alles
Elk circuit heeft een stijl: city (stad), parking (parkeergarage), touge (bergpas) of docks (haven).
"""
import math
import random

import pygame

from td_core import (CELL_H, CELL_W, CYAN, GREEN, J, NEON, ORANGE, PINK, PURPLE, RED, SHEET_COLS, SHEET_FILE, TAU, WHITE,
                     YELLOW, add_glow, dim, font, mix, vtext)

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
    dict(jp="大黒パーキング", name="DAIKOKU PARKING", diff=2, theme=(GREEN, YELLOW), style="parking",
         desc="Car meet in de parkeergarage: tussen de geparkeerde wagens door en via de spiraal naar het dak.",
         pts=[(18, 31.5, 0), (28, 31.5, 0), (38, 31.5, 0), (45, 31, 0), (49, 28.2, 0), (45.5, 25.3, 0), (38, 26, 0),
              (30, 25, 0), (22, 25.6, 0), (16, 25, 0), (12.5, 22, 0), (16, 18.8, 0), (23, 18.5, 0), (30, 18.5, 0),
              (35, 18.6, 0), (38.5, 18.2, 0.12), (42, 14.5, 0.35), (38, 10.5, 0.6), (34, 14, 0.85), (32.5, 19, 1),
              (29, 22, 1), (22, 22, 1), (15, 22, 1), (9, 22.5, 1), (5.5, 26, 0.6), (6.5, 30.5, 0.2), (11, 32, 0)],
         water=None, lot=(1, 5, 54, 37)),
    dict(jp="箱根ターンパイク", name="HAKONE TOUGE", diff=3, theme=(ORANGE, WHITE), style="touge",
         desc="Bergpas in het donker: haarspeldbochten door het bos, langs het meer.",
         pts=[(10, 30, 0), (18, 30.5, 0), (27, 29, 0), (33, 25, 0), (30, 20.5, 0), (22, 21.5, 0), (14, 22, 0),
              (9.5, 18.5, 0), (13, 14.5, 0), (21, 14, 0), (29, 13.5, 0), (36, 11, 0), (42, 7.5, 0), (49, 8, 0),
              (53, 12.5, 0), (50, 17, 0), (43, 18.5, 0), (40, 23, 0), (44, 27, 0), (51, 26, 0), (57, 22.5, 0),
              (62, 26, 0), (60, 31.5, 0), (52, 34, 0), (42, 34, 0), (32, 34.5, 0), (22, 35.5, 0), (12, 36.5, 0),
              (5.5, 35.5, 0), (3.5, 32.5, 0), (6, 30.2, 0)],
         water=[(5, 5), (20, 3.5), (30, 6), (31, 9.5), (22, 10.5), (10, 11), (4, 9)]),
    dict(jp="東京港", name="TOKYO PORT", diff=2, theme=(ORANGE, CYAN), style="docks",
         desc="Tussen de containers van de haven en over de brug boven het water.",
         pts=[(11, 12, 0), (20, 11.5, 0), (29, 12.5, 0), (35, 16, 0), (34, 21.5, 0), (27, 23, 0), (20, 21, 0),
              (14, 22.5, 0), (9, 26, 0), (11, 31, 0), (19, 33, 0), (28, 32, 0), (36, 33.5, 0), (44, 33, 0.4),
              (51, 29, 1), (55, 22, 1), (54, 14, 1), (48, 8.5, 1), (40, 6, 0.5), (31, 5.5, 0), (22, 5, 0),
              (13, 5.3, 0), (7, 5.8, 0), (4.5, 8.8, 0), (7, 11.8, 0)],
         water=[(47.5, 12), (50.5, 4), (70, 4), (70, 37), (49, 37), (47, 31), (48.5, 26), (47, 19)]),
]

# kleuren per stijl: (grond, berm/stoep, stoeprand, asfalt)
STYLES = {
    "city": ((17, 18, 30), (40, 42, 56), (92, 94, 110), (29, 30, 41)),
    "parking": ((17, 18, 30), (50, 50, 58), (214, 170, 30), (30, 31, 39)),
    "touge": ((8, 15, 13), (44, 38, 32), (74, 76, 84), (27, 28, 36)),
    "docks": ((24, 26, 34), (48, 50, 58), (200, 156, 30), (30, 31, 40)),
}
CLOTHES = [(230, 60, 80), (60, 140, 230), (240, 240, 240), (30, 30, 40), (250, 200, 60), (120, 220, 140), (200, 90, 220),
           (240, 130, 40), (90, 90, 100)]
HAIR = [(20, 16, 14), (40, 28, 20), (210, 180, 90), (230, 90, 150), (30, 30, 34), (20, 16, 14)]
BOX_COLORS = [(150, 46, 40), (40, 84, 150), (36, 120, 84), (196, 110, 30), (186, 188, 196), (120, 40, 110), (190, 170, 50)]

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


_PARKED = []


def parked_sprites():
    """De auto's uit cars_sheet.png, klein genoeg om langs de weg te parkeren (neus wijst naar rechts)."""
    if not _PARKED:
        sheet = pygame.image.load(SHEET_FILE).convert_alpha()
        for i in range(38):
            cell = sheet.subsurface((i % SHEET_COLS * CELL_W, i // SHEET_COLS * CELL_H, CELL_W, CELL_H))
            big = cell.subsurface(cell.get_bounding_rect())
            _PARKED.append(pygame.transform.smoothscale(big, (56, round(big.get_height() * 56 / big.get_width()))))
    return _PARKED


def draw_parked(world, x, y, heading, neon=None, lights=False):
    """Geparkeerde auto met schaduw; 'neon' geeft gloed onder de wagen, 'lights' zet de lampen aan."""
    img = pygame.transform.rotate(random.choice(parked_sprites()), -math.degrees(heading))
    r = img.get_rect(center=(x, y))
    world.blit(pygame.mask.from_surface(img).to_surface(setcolor=(0, 0, 0, 120), unsetcolor=(0, 0, 0, 0)), r.move(5, 7))
    if neon:
        add_glow(world, x, y, 150, dim(neon, 0.5), 1.5)
    world.blit(img, r)
    if lights:
        fx, fy = math.cos(heading), math.sin(heading)
        add_glow(world, x + fx * 44, y + fy * 44, 110, (70, 64, 44), 1.6)
        add_glow(world, x - fx * 28, y - fy * 28, 44, (130, 10, 10))


def draw_person(world, x, y):
    """Toeschouwer van bovenaf: schouders en hoofd. Soms flitst er een camera of gsm."""
    x, y = int(x), int(y)
    pygame.draw.circle(world, (6, 6, 12), (x + 2, y + 3), 5)
    pygame.draw.ellipse(world, random.choice(CLOTHES), (x - 5, y - 3, 10, 7))
    pygame.draw.circle(world, random.choice(HAIR), (x, y), 3)
    if random.random() < 0.12:
        add_glow(world, x, y, 50, (80, 84, 110))
        pygame.draw.circle(world, (235, 240, 255), (x + 3, y - 2), 1)


def draw_crowd(world, x, y, n, spread):
    for _ in range(n):
        a, d = random.uniform(0, TAU), random.uniform(0, spread)
        draw_person(world, x + math.cos(a) * d, y + math.sin(a) * d * 0.7)


def draw_tree(world, x, y, r, kind=0):
    """Boom van bovenaf. kind 0 = ceder (donkergroen), 1 = esdoorn in herfstkleur, 2 = kersenbloesem."""
    if kind == 2:
        return draw_sakura(world, x, y, r)
    cols = [((10, 30, 24), (16, 46, 34), (26, 66, 46)), ((90, 30, 16), (150, 52, 20), (220, 110, 30))][kind]
    pygame.draw.circle(world, (3, 6, 6), (x + 7, y + 9), int(r * 0.95))
    for layer, (f, n) in enumerate(((0.62, 7), (0.42, 6), (0.2, 4))):
        for k in range(n):
            a = TAU * k / n + random.uniform(-0.3, 0.3)
            pygame.draw.circle(world, cols[layer], (int(x + math.cos(a) * r * f), int(y + math.sin(a) * r * f)),
                               int(r * (0.52 - 0.1 * layer)))
    pygame.draw.circle(world, cols[2], (x - 2, y - 2), max(2, int(r * 0.18)))


def draw_container(world, x, y, w, h, stack):
    """Stapel zeecontainers (liggend). Elke laag schuift een beetje omhoog voor het diepte-effect."""
    pygame.draw.rect(world, (6, 7, 12), (x + 8, y + 10, w, h))
    for k in range(stack):
        col = random.choice(BOX_COLORS)
        r = pygame.Rect(x, y - k * 6, w, h)
        col = mix(dim(col, 0.62), (50, 54, 66), 0.25)
        pygame.draw.rect(world, dim(col, 0.55), r.move(0, 6))
        pygame.draw.rect(world, col, r)
        if w >= h:
            for rx in range(r.x + 6, r.right - 4, 7):
                pygame.draw.line(world, dim(col, 0.78), (rx, r.y + 3), (rx, r.bottom - 4))
        else:
            for ry in range(r.y + 6, r.bottom - 4, 7):
                pygame.draw.line(world, dim(col, 0.78), (r.x + 3, ry), (r.right - 4, ry))
        pygame.draw.rect(world, mix(col, (255, 255, 255), 0.3), r, 1)


def make_crane():
    """Havenkraan van bovenaf: portaal op rails met een lange arm (wijst naar rechts) en rode lampen."""
    g = pygame.Surface((420, 150), pygame.SRCALPHA)
    pygame.draw.rect(g, (0, 0, 0, 90), (26, 30, 380, 100), border_radius=6)
    for y in (18, 112):
        pygame.draw.rect(g, (196, 60, 40), (10, y, 150, 16))
        pygame.draw.rect(g, (236, 110, 80), (10, y, 150, 4))
    for x in (10, 144):
        pygame.draw.rect(g, (170, 48, 34), (x, 18, 16, 110))
    pygame.draw.rect(g, (214, 76, 50), (60, 58, 340, 28))
    for x in range(64, 396, 20):
        pygame.draw.line(g, (130, 36, 26), (x, 58), (x + 20, 86), 2)
        pygame.draw.line(g, (130, 36, 26), (x + 20, 58), (x, 86), 2)
    pygame.draw.rect(g, (240, 236, 220), (86, 50, 44, 44), border_radius=3)
    pygame.draw.rect(g, (60, 70, 90), (92, 56, 32, 32))
    for x, y in ((14, 22), (14, 122), (398, 72), (150, 22), (150, 122)):
        pygame.draw.circle(g, (255, 60, 50), (x, y), 4)
    return g


def make_height_bar(length):
    """Geel-zwarte hoogtebalk (制限高 2.1m) zoals aan de ingang van een Japanse parkeergarage."""
    g = pygame.Surface((length, 30), pygame.SRCALPHA)
    pygame.draw.rect(g, (20, 20, 24), (0, 6, length, 18), border_radius=3)
    for x in range(0, length, 24):
        pygame.draw.polygon(g, (240, 200, 30), [(x, 24), (x + 12, 6), (x + 24, 6), (x + 12, 24)])
    r = pygame.Rect(length // 2 - 74, 2, 148, 26)
    pygame.draw.rect(g, (16, 16, 22), r, border_radius=4)
    pygame.draw.rect(g, (240, 200, 30), r, 2, border_radius=4)
    t = font(15, True).render(J("制限高 2.1m", "MAX 2.1m"), True, (255, 230, 90))
    g.blit(t, t.get_rect(center=r.center))
    return g


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
    elif kind < 0.62 and min(bw, bh) > 90:                                      # groot led-scherm op het dak
        col = random.choice(NEON)
        r = pygame.Rect(0, 0, int(bw * 0.62), int(bh * 0.5))
        r.center = (cx, cy)
        pygame.draw.rect(world, (6, 6, 12), r.inflate(8, 8), border_radius=3)
        for yy in range(r.y, r.bottom, 3):
            f = (yy - r.y) / r.h
            pygame.draw.line(world, mix(dim(col, 0.9), (255, 255, 255), 0.5 * abs(math.sin(f * 5))), (r.x, yy), (r.right - 1, yy), 2)
        add_glow(world, cx, cy, int(bw * 1.7), dim(col, 0.3), 1.6)
    elif kind < 0.72 and min(bw, bh) > 80:                                      # daktuin
        pygame.draw.rect(world, (22, 60, 40), (x0 + 12, y0 + 12, bw - 24, bh - 24), border_radius=4)
        for _ in range(6):
            pygame.draw.circle(world, (36, 96, 60), (random.randint(x0 + 18, x0 + bw - 18), random.randint(y0 + 18, y0 + bh - 18)), 7)
    elif kind < 0.82:                                                           # antenne met rood knipperlicht
        pygame.draw.line(world, (150, 154, 170), (cx - 14, cy), (cx + 14, cy), 2)
        pygame.draw.line(world, (150, 154, 170), (cx, cy - 14), (cx, cy + 14), 2)
        pygame.draw.circle(world, (255, 60, 50), (cx, cy), 3)
        add_glow(world, cx, cy, 80, (110, 14, 10))
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
        self.style = spec.get("style", "city")
        self.lot = None                                      # parkeerterrein: rechthoek waar geen gebouwen staan
        if spec.get("lot"):
            a, b, c, d = spec["lot"]
            self.lot = pygame.Rect(a * U - minx, b * U - miny, (c - a) * U, (d - b) * U)
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
        base, walk, curb, asphalt = STYLES[self.style]
        tile.fill(base)
        for _ in range(2400):
            d = random.randint(-5, 7)
            pygame.draw.circle(tile, (base[0] + 3 + d, base[1] + 4 + d, base[2] + 4 + d),
                               (random.randrange(256), random.randrange(256)), random.randint(1, 2))
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
                    if random.random() < 0.25 and self.style != "touge":   # neon dat weerspiegelt in het water
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

        # ---- omgeving: hangt af van de stijl van het circuit
        if self.style == "touge":
            yield from self._forest(world, pool)
        elif self.style == "docks":
            yield from self._docks(world, pool)
        else:
            yield from self._city(world, pool)
            if self.lot:
                self._parking_lot(world)
        yield J("道路を舗装中", "WEGEN AANLEGGEN")

        # ---- straat (hoogte 0)
        self.strip(world, ground, -HALF - 26, HALF + 26, walk, False)                     # stoep / berm
        self.strip(world, ground, -HALF - 6, HALF + 6, curb, False)                       # stoeprand
        self.strip(world, ground, -HALF, HALF, asphalt, False)                            # asfalt
        self._road_wear(world, ground, asphalt)
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

    # ---- omgeving per stijl
    def free(self, x, y, margin):
        """Is dit punt ver genoeg van elke weg en niet in het water?"""
        return self.dist(x, y) > HALF + margin and not self.wet(x, y)

    def _city(self, world, pool):
        """Dichte stad: steegjes met geparkeerde auto's en daartussen gebouwen vol neon."""
        cw, ch = 214, 204
        lot = self.lot.inflate(120, 120) if self.lot else None
        for gx in range(0, self.w // cw + 2):                 # steegjes tussen de blokken
            pygame.draw.rect(world, (25, 26, 38), (gx * cw - 20, 0, 40, self.h))
        for gy in range(0, self.h // ch + 2):
            pygame.draw.rect(world, (25, 26, 38), (0, gy * ch - 20, self.w, 40))
        for gy in range(0, self.h // ch + 2):
            for gx in range(0, self.w // cw + 2):
                x, y = gx * cw, gy * ch
                for d in range(30, cw - 20, 22):              # streepjes in het midden
                    pygame.draw.line(world, (70, 70, 76), (x + d, y), (x + d + 9, y), 1)
                for d in range(30, ch - 20, 22):
                    pygame.draw.line(world, (70, 70, 76), (x, y + d), (x, y + d + 9), 1)
                for d in range(-16, 17, 8):                   # zebrapad op elk kruispunt
                    pygame.draw.line(world, (120, 120, 124), (x + d, y + 24), (x + d, y + 34), 3)
                    pygame.draw.line(world, (120, 120, 124), (x + 24, y + d), (x + 34, y + d), 3)
                if (gx + gy) % 2 == 0:
                    add_glow(world, x, y, 240, (46, 30, 12), 1.6)   # lantaarn op het kruispunt
                r = random.random()
                if r < 0.5 and self.free(x + cw // 2, y, 90):       # auto geparkeerd in het steegje
                    draw_parked(world, x + random.randint(50, cw - 50), y + random.choice([-9, 9]), random.choice([0, math.pi]),
                                random.choice(NEON) if r < 0.06 else None, r < 0.1)
                elif r < 0.62 and self.free(x, y + ch // 2, 90):
                    draw_parked(world, x + random.choice([-9, 9]), y + random.randint(50, ch - 50), random.choice([1, -1]) * math.pi / 2)
            if gy % 6 == 0:
                yield J("路地を作成中", "STEEGJES MAKEN")
        for gy in range(0, self.h // ch + 1):
            for gx in range(0, self.w // cw + 1):
                bw, bh = random.randint(110, 176), random.randint(100, 150)
                x = gx * cw + cw // 2 + random.randint(-8, 8)
                y = gy * ch + ch // 2 + random.randint(-8, 8)
                if lot and lot.collidepoint(x, y):
                    continue
                if self.dist(x, y) < HALF + 80 + max(bw, bh) * 0.62:
                    bw, bh = int(bw * 0.6), int(bh * 0.6)                       # kleiner gebouw vlak bij de weg
                    if self.dist(x, y) < HALF + 70 + max(bw, bh) * 0.62:
                        continue
                if self.water and any(self.wet(x + dx * bw * 0.7, y + dy * bh * 0.8) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    continue
                draw_building(world, pool, x, y, bw, bh)
            if gy % 4 == 0:
                yield J("ビルを建設中", "GEBOUWEN PLAATSEN")

    def _parking_lot(self, world):
        """Groot parkeerterrein: vakken, pijlen, pilaren, tl-licht en een car meet met neon onder de wagens."""
        L = self.lot
        pygame.draw.rect(world, (4, 4, 8), L.inflate(60, 60), border_radius=10)
        pygame.draw.rect(world, (33, 34, 43), L)
        for _ in range(L.w * L.h // 900):                     # vlekken en korrel in het beton
            d = random.randint(-5, 6)
            pygame.draw.circle(world, (33 + d, 34 + d, 43 + d), (random.randint(L.x, L.right), random.randint(L.y, L.bottom)), random.randint(1, 3))
        for _ in range(140):                                  # olievlekken
            x, y = random.randint(L.x, L.right), random.randint(L.y, L.bottom)
            pygame.draw.ellipse(world, (24, 25, 32), (x, y, random.randint(14, 40), random.randint(10, 26)))
        for k in range(0, 2 * (L.w + L.h), 40):               # geel-zwarte rand rond het terrein
            for a, b in ((0, 20),):
                pass
        pygame.draw.rect(world, (214, 170, 30), L, 8)
        pygame.draw.rect(world, (96, 98, 112), L.inflate(16, 16), 6)
        bay, deep, row = 40, 78, 236
        meet = []                                             # plaatsen waar toeschouwers bij een auto staan
        for y in range(L.y + 150, L.bottom - 100, row):
            for x in range(L.x + 60, L.right - 60, bay):
                near = self.dist(x + bay / 2, y)
                k = (x - L.x) // bay
                if near > HALF + 54:
                    pygame.draw.line(world, (210, 210, 200), (x, y - deep), (x, y + deep), 2)
                    pygame.draw.line(world, (210, 210, 200), (x, y), (x + bay, y), 2)
                    if k % 5 == 0:                            # pilaar met waarschuwingsstrepen
                        pygame.draw.rect(world, (8, 8, 12), (x - 5, y - 5, 18, 18))
                        pygame.draw.rect(world, (120, 124, 136), (x - 9, y - 9, 18, 18))
                        pygame.draw.rect(world, (236, 196, 40), (x - 9, y - 9, 18, 18), 3)
                    if k % 7 == 3:                            # tl-licht aan het plafond
                        add_glow(world, x, y, 330, (30, 38, 44), 1.5)
                        pygame.draw.rect(world, (220, 240, 255), (x - 14, y - 2, 28, 4))
                for side in (-1, 1):
                    cx, cy = x + bay / 2, y + side * deep / 2
                    if self.dist(cx, cy) < HALF + 62 or self.dist(cx, cy + side * 30) < HALF + 50:
                        continue
                    r = random.random()
                    if r < 0.5:
                        show = r < 0.09                       # opgevoerde wagen met neon en lichten aan
                        draw_parked(world, cx, cy + side * 2, side * math.pi / 2 if r < 0.3 else -side * math.pi / 2,
                                    random.choice(NEON) if show else None, show)
                        if show:
                            meet.append((cx, cy + side * 62))
                    elif r < 0.54:                            # leeg vak met kegel
                        pygame.draw.circle(world, (255, 120, 40), (cx, cy), 5)
                        pygame.draw.circle(world, (255, 240, 230), (cx, cy), 2)
            # rijstrook tussen twee rijen: pijlen en tekst op de vloer
            ay = y + row // 2
            for x in range(L.x + 200, L.right - 200, 420):
                if self.dist(x, ay) > HALF + 70:
                    kk = (x + y) // 420
                    jp, lat = [("駐車場", "PARKING"), ("徐行", "SLOW"), ("出口", "EXIT"), ("B2", "B2")][kk % 4]
                    img = road_paint(jp, lat, 30, 0 if (y // row) % 2 else math.pi, (226, 190, 60), 190)
                    world.blit(img, img.get_rect(center=(x, ay)))
        for x, y in meet:
            if self.dist(x, y) > HALF + 40:
                draw_crowd(world, x, y, random.randint(4, 9), 26)

    def _forest(self, world, pool):
        """Bergpas: dicht bos met ceders, rode esdoorns, rotsen en hier en daar een theehuis."""
        for _ in range(60):                                   # open plekken met maanlicht
            x, y = random.randint(0, self.w), random.randint(0, self.h)
            add_glow(world, x, y, random.choice([400, 520, 640]), (8, 14, 16), 1.4)
        for _ in range(260):                                  # rotsen
            x, y = random.randint(0, self.w), random.randint(0, self.h)
            if self.free(x, y, 50):
                r = random.randint(10, 26)
                pts = [(x + math.cos(TAU * k / 7) * r * random.uniform(0.6, 1.1), y + math.sin(TAU * k / 7) * r * random.uniform(0.6, 1.1)) for k in range(7)]
                pygame.draw.polygon(world, (5, 8, 9), [(px + 5, py + 6) for px, py in pts])
                pygame.draw.polygon(world, (62, 66, 72), pts)
                pygame.draw.polygon(world, (96, 100, 108), pts, 2)
        yield J("森を植樹中", "BOS PLANTEN")
        k = 0
        for i in range(30, self.n, 170):                      # theehuisjes en uitkijkpunten langs de weg
            for side in (-1, 1):
                k += 1
                x, y = self.P(i, side * (HALF + 200), False)
                if k % 3 == 0 and self.free(x, y, 170) and 100 < x < self.w - 100 and 100 < y < self.h - 100:
                    draw_building(world, pool, int(x), int(y), random.randint(90, 130), random.randint(80, 110))
        step = 58
        for gy in range(0, self.h // step + 1):
            for gx in range(0, self.w // step + 1):
                x = gx * step + random.randint(-22, 22)
                y = gy * step + random.randint(-22, 22)
                if not self.free(x, y, 44 + 20):
                    continue
                r = random.random()
                near = self.dist(x, y) < HALF + 150            # langs de weg staan de kleurrijke bomen
                kind = 1 if r < (0.2 if near else 0.03) else 2 if r < (0.27 if near else 0.04) else 0
                draw_tree(world, x, y, random.randint(22, 36), kind)
            if gy % 12 == 0:
                yield J("森を植樹中", "BOS PLANTEN")

    def _docks(self, world, pool):
        """Haven: rijen containers, loodsen, schijnwerpers, kranen aan de kade en een vrachtschip."""
        cw, ch = 300, 150
        for gy in range(0, self.h // ch + 1):
            for gx in range(0, self.w // cw + 1):
                x0, y0 = gx * cw, gy * ch
                block = (gx // 3 + gy // 4 * 7) % 6            # elk blok van het terrein heeft een eigen invulling
                if block == 5:                                # loods of kantoor
                    if gx % 3 == 1 and gy % 4 == 1:
                        x, y = x0 + cw // 2, y0 + ch
                        if all(self.free(x + dx * 150, y + dy * 120, 60) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                            draw_building(world, pool, x, y, 250, 190)
                    continue
                if gy % 4 == 3:                               # rijpad tussen de stapels
                    if gx % 2 == 0 and self.free(x0 + 150, y0 + 75, 60):
                        add_glow(world, x0 + 150, y0 + 75, 420, (34, 34, 30), 1.5)   # schijnwerper
                        pygame.draw.circle(world, (255, 244, 210), (x0 + 150, y0 + 75), 4)
                    elif random.random() < 0.3 and self.free(x0 + 150, y0 + 75, 70):
                        draw_parked(world, x0 + 150, y0 + 75, random.choice([0, math.pi]))
                    continue
                for cx in (x0 + 12, x0 + 156):                # twee containers naast elkaar per vak
                    for cy in (y0 + 14, y0 + 82):
                        if random.random() < 0.86 and all(self.free(cx + dx, cy + dy, 46) for dx in (0, 66, 132) for dy in (0, 26, 52)):
                            draw_container(world, cx, cy, 132, 52, random.choice([1, 1, 2, 2, 3]))
            if gy % 6 == 0:
                yield J("コンテナを積載中", "CONTAINERS STAPELEN")
        if self.water:                                        # kranen langs de kade
            crane = make_crane()
            for k in range(len(self.water)):
                a, b = self.water[k], self.water[(k + 1) % len(self.water)]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                for d in range(260, int(L) - 200, 560):
                    x, y = a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L
                    for sign in (1, -1):                      # de arm moet boven het water hangen
                        h = ang + sign * math.pi / 2
                        if self.wet(x + math.cos(h) * 200, y + math.sin(h) * 200) and self.free(x - math.cos(h) * 60, y - math.sin(h) * 60, 110) \
                                and self.dist(x + math.cos(h) * 150, y + math.sin(h) * 150) > HALF + 60:
                            img = pygame.transform.rotate(crane, -math.degrees(h))
                            world.blit(img, img.get_rect(center=(x + math.cos(h) * 110, y + math.sin(h) * 110)))
                            add_glow(world, x, y, 360, (44, 24, 14), 1.5)
            xs, ys = [p[0] for p in self.water], [p[1] for p in self.water]
            ship = pygame.Surface((520, 130), pygame.SRCALPHA)      # vrachtschip vol containers
            hull = [(10, 12), (410, 12), (500, 64), (410, 116), (10, 116)]
            pygame.draw.polygon(ship, (28, 30, 40), hull)
            pygame.draw.polygon(ship, (150, 40, 36), hull, 5)
            for cx in range(96, 380, 70):
                for cy in (24, 66):
                    draw_container(ship, cx, cy, 64, 36, random.choice([1, 2]))
            pygame.draw.rect(ship, (226, 228, 236), (26, 30, 50, 68), border_radius=4)
            done = 0
            for _ in range(300):
                x, y = random.uniform(min(xs), max(xs)), random.uniform(min(ys), max(ys))
                for ang in (0, 90):
                    dx, dy = (260, 70) if ang == 0 else (70, 260)
                    if done < 2 and all(self.wet(x + a * dx, y + b * dy) and self.dist(x + a * dx, y + b * dy) > HALF + 110
                                        for a in (-1, 0, 1) for b in (-1, 1)):
                        img = pygame.transform.rotate(ship, ang)
                        world.blit(img, img.get_rect(center=(x, y)))
                        add_glow(world, x, y, 300, (40, 36, 24))
                        done += 1
                        xs = [x + 700, x + 2400] if ang else xs       # het tweede schip een eind verder

    def _road_wear(self, world, ground, asphalt):
        """Sleet op het asfalt: herstelde vlakken, scheuren, putdeksels en oude remsporen."""
        n = self.n
        for i in ground:
            r = random.random()
            if r < 0.03:                                      # herstelde lap asfalt
                lat = random.randint(-HALF + 30, HALF - 70)
                self.strip(world, [i, i + 1, i + 2], lat, lat + random.randint(30, 60), dim(asphalt, random.choice([0.82, 1.14])), False)
            elif r < 0.05:                                    # putdeksel
                x, y = self.P(i, random.randint(-HALF + 30, HALF - 30), False)
                pygame.draw.circle(world, (50, 52, 62), (x, y), 9)
                pygame.draw.circle(world, (22, 23, 30), (x, y), 9, 2)
                pygame.draw.line(world, (22, 23, 30), (x - 5, y), (x + 5, y), 1)
        for z in self.zones:                                  # zwarte bandensporen in elke driftzone
            for _ in range(5):
                a = random.randint(z["a"], max(z["a"], z["b"] - 14))
                b = min(z["b"], a + random.randint(14, 40))
                l0 = -z["side"] * random.randint(-20, 60)
                l1 = -z["side"] * random.randint(20, 80)
                for wheel in (-13, 13):
                    pts = [self.P(i, l0 + (l1 - l0) * (i - a) / max(1, b - a) + wheel, False) for i in range(a, b + 1)
                           if not self.up[i % n]]
                    if len(pts) > 1:
                        pygame.draw.lines(world, (15, 15, 21), False, pts, 4)

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

        style = self.style
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
                if style == "touge":                          # bergpas: alleen reflectorpaaltjes en soms een automaat
                    px, py = self.P(i, side * (HALF + 12), False)
                    pygame.draw.circle(world, (255, 150, 40) if side > 0 else (235, 235, 240), (px, py), 3)
                    if r == 0 and k % 4 == 0:
                        draw_vending(world, int(x) - 20, int(y) - 10)
                elif style == "parking" or style == "docks":  # kegels en betonblokken
                    if r < 4:
                        px, py = self.P(i, side * (HALF + 14), False)
                        pygame.draw.circle(world, (255, 120, 40), (px, py), 5)
                        pygame.draw.circle(world, (255, 240, 230), (px, py), 2)
                elif r < 3:
                    draw_sakura(world, int(x), int(y), random.randint(20, 28))
                elif r < 5:
                    draw_vending(world, int(x) - 20, int(y) - 10)
                elif r == 5:
                    pygame.draw.circle(world, (255, 120, 40), (x, y), 5)       # verkeerskegel
                    pygame.draw.circle(world, (255, 240, 230), (x, y), 2)
                elif r < 8 and abs(self.curv[i]) < 1 / 500:   # auto geparkeerd langs de stoep
                    px, py = self.P(i, side * (HALF + 46), False)
                    if self.dist(px, py) > HALF + 30:
                        draw_parked(world, px, py, self.headings[i] + (0 if side > 0 else math.pi),
                                    NEON[k % 8] if k % 9 == 0 else None, k % 9 == 0)
        self._spectators(world, gset)
        bb = 0
        placed = []
        for i in range(20, n, 30 if style != "touge" else 90):   # grote flikkerende reclameborden
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
                if style == "parking":
                    img = make_height_bar(L)
                elif style == "touge":
                    img = make_torii(L) if k % 2 else make_lanterns(L - 20)
                elif style == "docks":
                    img = make_footbridge(L + 30, c1, c2)
                else:
                    img = [make_torii(L), make_footbridge(L + 30, c1, c2), make_lanterns(L - 20)][k % 3]
                g = across(img, self.headings[i])
                x, y = self.pts[i]
                self.overs.append((g, x - g.get_width() / 2, y - g.get_height() / 2))
                if k % 3 == 2:
                    add_glow(world, x, y, 320, (70, 20, 12), 1.4)

    def _spectators(self, world, gset):
        """Publiek achter de vangrail: aan de buitenkant van elke driftzone en bij de start."""
        spots = [(i, -z["side"]) for z in self.zones for i in range(z["a"], z["b"] + 1, 2)]
        spots += [(i % self.n, s) for i in range(-70, 30, 2) for s in (-1, 1)]
        for i, side in spots:
            if i not in gset:
                continue
            for _ in range(3):
                x, y = self.P(i, side * (HALF + random.randint(30, 60)), False)
                x, y = x + random.randint(-8, 8), y + random.randint(-8, 8)
                if self.dist(x, y) > HALF + 22 and not self.wet(x, y) and not self.under(x, y):
                    draw_person(world, x, y)
        for z in self.zones:                                  # geel-zwarte schrikplanken in de buitenbocht
            for i in range(z["a"], z["b"] + 1):
                if i in gset:
                    a, b = (-HALF - 12, -HALF - 5) if z["side"] > 0 else (HALF + 5, HALF + 12)
                    self.strip(world, [i], a, b, (240, 200, 30) if (i // 2) % 2 else (20, 20, 24), False)

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
