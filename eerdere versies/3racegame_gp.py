"""
TOP-DOWN RACER 2  -  Grand Prix editie
======================================
Race tegen 1 tot 7 AI-bots op willekeurig gegenereerde circuits.
Alles in de menu's werkt met de muis (toetsen kunnen ook).

Installeren:   py -m pip install pygame-ce
Starten:       py racegame_gp.py     (of:  python racegame_gp.py)

Spelmodi
    SNELLE RACE   een enkele race met eigen instellingen
    GRAND PRIX    meerdere races achter elkaar, punten per positie,
                  na afloop kampioenschapsstand en podium
    GARAGE        je auto aanpassen: model, kleur, accentkleur en tuning

Besturing tijdens de race
    Pijltje omhoog / W      gas
    Pijltje omlaag / S      remmen / achteruit
    Links / rechts / A / D  sturen
    SHIFT                   NITRO (meter loopt leeg en laadt weer op)
    SPATIE                  handrem (driften)
    T                       terugzetten op het circuit
    ESC                     pauzemenu       F11  volledig scherm
"""
import colorsys
import json
import math
import os
import random
import sys

import pygame

# ------------------------------------------------------------------ instellingen
W, H = 1280, 720
FPS = 60
TAU = math.pi * 2

ROAD_W = 170            # breedte van het asfalt
HALF = ROAD_W / 2
DS = 12                 # afstand tussen punten van de middenlijn (px)

TURN_RATE = 3.3         # stuursnelheid (rad/s)
TURN_LOSS = 0.38        # minder wendbaar bij hoge snelheid
BASE_ACCEL = 430
BRAKE = 720
NITRO_USE = 32          # nitro per seconde verbruikt
NITRO_REGEN = 9         # nitro per seconde bijgeladen

POINTS = [25, 18, 15, 12, 10, 8, 6, 4]      # Grand Prix punten per positie
MAX_BOTS = 7
STAT_MAX, STAT_BUDGET = 6, 12               # tuning: max per onderdeel / totaal aantal punten
STAT_NAMES = ["Topsnelheid", "Acceleratie", "Wendbaarheid", "Nitro"]
BODY_NAMES = ["Formule", "Sportwagen", "Rally"]

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "racegame_save.json")

LEVELS = {
    1: dict(name="Makkelijk", desc="Brede, rustige bochten", K=5, A0=0.30, R=850,
            min_r=260, ai_vmax=450, ai_corner=0.80, rubber=0.0, mercy=0.10, nitro=False,
            color=(90, 210, 120)),
    2: dict(name="Normaal", desc="Veel bochten, wisselend ritme", K=7, A0=0.34, R=1050,
            min_r=200, ai_vmax=510, ai_corner=0.88, rubber=0.0, mercy=0.05, nitro=False,
            color=(255, 200, 70)),
    3: dict(name="Moeilijk", desc="Extreem veel scherpe bochten", K=11, A0=0.36, R=1250,
            min_r=150, ai_vmax=545, ai_corner=0.93, rubber=0.0, mercy=0.0, nitro=False,
            color=(255, 110, 80)),
    4: dict(name="Expert", desc="Snelle bots die nitro gebruiken", K=13, A0=0.38, R=1350,
            min_r=135, ai_vmax=580, ai_corner=0.96, rubber=0.05, mercy=0.0, nitro=True,
            color=(255, 70, 120)),
    5: dict(name="Onmogelijk", desc="Bijna perfect en geeft nooit op", K=15, A0=0.40, R=1450,
            min_r=120, ai_vmax=612, ai_corner=0.985, rubber=0.09, mercy=0.0, nitro=True,
            color=(200, 80, 255)),
}

PALETTE = [(225, 40, 40), (255, 140, 30), (250, 205, 40), (140, 210, 50),
           (40, 170, 80), (30, 185, 170), (60, 190, 240), (50, 120, 235),
           (140, 80, 220), (240, 90, 170), (235, 235, 240), (45, 48, 56)]
ACCENTS = [(245, 245, 245), (20, 20, 24), (250, 205, 40), (225, 40, 40),
           (50, 120, 235), (255, 140, 30), (40, 170, 80), (170, 175, 190)]
BOT_NAMES = ["Viper", "Blitz", "Nova", "Turbo", "Apex", "Drift", "Rocket", "Comet",
             "Falcon", "Storm"]

DEFAULTS = dict(level=2, bots=3, laps_q=5, laps_gp=3, weather=0, gp_races=4,
                car=dict(color=[225, 40, 40], accent=[245, 245, 245], body=0,
                         stats=[3, 3, 3, 3]))


# ------------------------------------------------------------------ hulpfuncties
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wrap_rad(a):
    return (a + math.pi) % TAU - math.pi


def fmt(t):
    if t is None:
        return "-:--.-"
    m = int(t // 60)
    return f"{m}:{t - m * 60:04.1f}"


def hsv(h, s=0.85, v=0.95):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def col_dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def car_params(stats):
    """Vertaal de tuningpunten naar echte eigenschappen."""
    s, a, h, n = stats
    return dict(vmax=480 + 27 * s, accel=BASE_ACCEL * (0.8 + 0.0667 * a),
                turn=0.85 + 0.05 * h, nitro=60 + 13 * n)


# ------------------------------------------------------------------ opslaan / laden
def sanitize(d):
    d["level"] = int(clamp(int(d["level"]), 1, 5))
    d["bots"] = int(clamp(int(d["bots"]), 1, MAX_BOTS))
    d["laps_q"] = int(clamp(int(d["laps_q"]), 1, 10))
    d["laps_gp"] = int(clamp(int(d["laps_gp"]), 1, 10))
    d["weather"] = 1 if int(d["weather"]) else 0
    d["gp_races"] = int(clamp(int(d["gp_races"]), 2, 8))
    car = d["car"]
    car["color"] = [int(clamp(int(v), 0, 255)) for v in list(car["color"])[:3]]
    car["accent"] = [int(clamp(int(v), 0, 255)) for v in list(car["accent"])[:3]]
    car["body"] = int(clamp(int(car["body"]), 0, len(BODY_NAMES) - 1))
    st = [int(clamp(int(v), 0, STAT_MAX)) for v in list(car["stats"])[:4]]
    while len(st) < 4:
        st.append(3)
    while sum(st) > STAT_BUDGET:
        st[st.index(max(st))] -= 1
    car["stats"] = st


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        for k in data:
            if k == "car" and isinstance(raw.get("car"), dict):
                data["car"].update(raw["car"])
            elif k in raw:
                data[k] = raw[k]
        sanitize(data)
    except Exception:
        data = json.loads(json.dumps(DEFAULTS))
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ------------------------------------------------------------------ circuit genereren
def _polar_curve(K, a0, R):
    """Gesloten kromme r(theta) opgebouwd uit willekeurige harmonischen."""
    coef = []
    for k in range(2, K + 1):
        if k == K or random.random() < 0.85:
            coef.append((k, a0 * random.uniform(0.5, 1.0) / k ** 0.6,
                         random.uniform(0, TAU)))
    steps = 1440
    pts = []
    for s in range(steps):
        th = TAU * s / steps
        r = 1.0 + sum(a * math.cos(k * th + ph) for k, a, ph in coef)
        if r < 0.4:
            return None
        pts.append((R * r * math.cos(th), R * 0.72 * r * math.sin(th)))
    return pts


def _resample(pts, ds):
    """Verdeel een gesloten polylijn in punten op gelijke afstand."""
    n = len(pts)
    out = [pts[0]]
    cur = pts[0]
    to_next = ds
    for i in range(1, n + 1):
        nxt = pts[i % n]
        seg = math.dist(cur, nxt)
        while seg >= to_next and seg > 0:
            t = to_next / seg
            cur = (cur[0] + (nxt[0] - cur[0]) * t, cur[1] + (nxt[1] - cur[1]) * t)
            out.append(cur)
            seg = math.dist(cur, nxt)
            to_next = ds
        to_next -= seg
        cur = nxt
    if math.dist(out[-1], out[0]) < ds * 0.5:
        out.pop()
    return out


def _valid(pts, min_r):
    n = len(pts)
    # 1) bochten niet te scherp
    for i in range(n):
        a, b, c = pts[i - 3], pts[i], pts[(i + 3) % n]
        a1 = math.atan2(b[1] - a[1], b[0] - a[0])
        a2 = math.atan2(c[1] - b[1], c[0] - b[0])
        if abs(wrap_rad(a2 - a1)) * min_r > 3 * DS:
            return False
    # 2) delen van het circuit mogen elkaar niet te dicht naderen
    cell = 260
    sep2 = (ROAD_W + 80) ** 2
    grid = {}
    for i, p in enumerate(pts):
        grid.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(i)
    for i, p in enumerate(pts):
        gx, gy = int(p[0] // cell), int(p[1] // cell)
        for ax in (gx - 1, gx, gx + 1):
            for ay in (gy - 1, gy, gy + 1):
                for j in grid.get((ax, ay), ()):
                    if j <= i:
                        continue
                    if min(j - i, n - (j - i)) < 60:
                        continue
                    q = pts[j]
                    if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < sep2:
                        return False
    return True


def _straightest_start(pts):
    """Roteer de lijst zodat de start op het rechtste stuk ligt."""
    n = len(pts)
    h = [math.atan2(pts[(i + 1) % n][1] - pts[i][1], pts[(i + 1) % n][0] - pts[i][0])
         for i in range(n)]
    d = [abs(wrap_rad(h[i] - h[i - 1])) for i in range(n)]
    best, bi = 1e9, 0
    for i in range(n):
        s = sum(d[(i + k) % n] for k in range(-24, 25))
        if s < best:
            best, bi = s, i
    return pts[bi:] + pts[:bi]


def generate_centerline(level):
    cfg = LEVELS[level]
    a0 = cfg["A0"]
    for attempt in range(800):
        if attempt and attempt % 80 == 0:
            a0 *= 0.85                      # lukt het niet? iets rustiger maken
        raw = _polar_curve(cfg["K"], a0, cfg["R"])
        if raw is None:
            continue
        pts = _resample(raw, DS)
        if len(pts) < 150 or not _valid(pts, cfg["min_r"]):
            continue
        return _straightest_start(pts)
    return _straightest_start(_resample(_polar_curve(0, 0, cfg["R"]), DS))


def count_bends(pts):
    """Aantal bochten (aaneengesloten stukken met kleine bochtstraal)."""
    n = len(pts)
    flags = []
    for i in range(n):
        a, b, c = pts[i - 3], pts[i], pts[(i + 3) % n]
        a1 = math.atan2(b[1] - a[1], b[0] - a[0])
        a2 = math.atan2(c[1] - b[1], c[0] - b[0])
        flags.append(abs(wrap_rad(a2 - a1)) / (3 * DS) > 1 / 520)
    return sum(1 for i in range(n) if flags[i] and not flags[i - 1])


# ------------------------------------------------------------------ circuit-object
class Track:
    def __init__(self, raw):
        margin = 520
        xs = [p[0] for p in raw]
        ys = [p[1] for p in raw]
        ox, oy = margin - min(xs), margin - min(ys)
        self.pts = [(x + ox, y + oy) for x, y in raw]
        self.w = int(max(xs) - min(xs) + 2 * margin)
        self.h = int(max(ys) - min(ys) + 2 * margin)
        n = self.n = len(self.pts)
        P = self.pts
        self.headings = [math.atan2(P[(i + 1) % n][1] - P[i][1],
                                    P[(i + 1) % n][0] - P[i][0]) for i in range(n)]
        self.normals = [(-math.sin(h), math.cos(h)) for h in self.headings]   # rechts van rijrichting
        k = [abs(wrap_rad(self.headings[(i + 2) % n] - self.headings[(i - 2) % n])) / (4 * DS)
             for i in range(n)]
        self.kappa = [sum(k[(i + j) % n] for j in range(-3, 4)) / 7 for i in range(n)]
        self.B = 128
        self.grid = {}
        for p in P:
            self.grid.setdefault((int(p[0] // self.B), int(p[1] // self.B)), []).append(p)
        self.world = None

    # ---- afstandsvragen
    def near(self, x, y, r):
        B = self.B
        k = int(r // B) + 1
        gx, gy = int(x // B), int(y // B)
        r2 = r * r
        for ax in range(gx - k, gx + k + 1):
            for ay in range(gy - k, gy + k + 1):
                for px, py in self.grid.get((ax, ay), ()):
                    if (px - x) ** 2 + (py - y) ** 2 <= r2:
                        return True
        return False

    def on_road(self, x, y):
        return self.near(x, y, HALF)

    # ---- tekenen van de hele wereld (1x)
    def render(self):
        w, h = self.w, self.h
        world = pygame.Surface((w, h)).convert()
        tile = make_grass_tile()
        for y in range(0, h, 256):
            for x in range(0, w, 256):
                world.blit(tile, (x, y))
        for _ in range(100):                                   # zachte kleurvlekken
            r = random.randint(120, 320)
            s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
            d = random.randint(-30, 30)
            pygame.draw.circle(s, (40 + d, 130 + d, 55 + d // 2, 24), (r, r), r)
            world.blit(s, (random.randint(0, w) - r, random.randint(0, h) - r))

        ip = [(int(x), int(y)) for x, y in self.pts]
        curvy = [kp > 0.0035 for kp in self.kappa]
        for p in ip:
            pygame.draw.circle(world, (30, 105, 50), p, int(HALF + 50))       # donkere rand
        for p in ip:
            pygame.draw.circle(world, (206, 186, 126), p, int(HALF + 38))     # zand/grind
        for i, p in enumerate(ip):                                            # kerbs
            if curvy[i] and (i // 2) % 2 == 0:
                col = (214, 40, 40)
            else:
                col = (240, 240, 240)
            pygame.draw.circle(world, col, p, int(HALF + 14))
        for p in ip:
            pygame.draw.circle(world, (64, 66, 74), p, int(HALF))             # asfalt
        for p in ip:                                                          # asfaltkorrel
            for _ in range(5):
                a = random.uniform(0, TAU)
                d = random.uniform(0, HALF - 4)
                c = random.choice([(72, 74, 82), (54, 56, 63), (80, 82, 90)])
                pygame.draw.circle(world, c, (int(p[0] + math.cos(a) * d),
                                              int(p[1] + math.sin(a) * d)), random.randint(1, 2))
        for i in range(0, self.n, 8):                                         # middenstreep
            a, b = ip[i], ip[(i + 4) % self.n]
            pygame.draw.line(world, (110, 112, 122), a, b, 3)

        # start/finish
        line = pygame.Surface((168, 24), pygame.SRCALPHA)
        for r in range(2):
            for c in range(14):
                col = (245, 245, 245) if (r + c) % 2 == 0 else (20, 20, 24)
                pygame.draw.rect(line, col, (c * 12, r * 12, 12, 12))
        rot = pygame.transform.rotate(line, -(math.degrees(self.headings[0]) + 90))
        world.blit(rot, rot.get_rect(center=ip[0]))
        nx, ny = self.normals[0]
        for side in (-1, 1):
            px = int(self.pts[0][0] + nx * side * (HALF + 30))
            py = int(self.pts[0][1] + ny * side * (HALF + 30))
            pygame.draw.circle(world, (0, 0, 0), (px + 4, py + 5), 12)
            pygame.draw.circle(world, (40, 40, 48), (px, py), 12)
            pygame.draw.circle(world, (230, 50, 50), (px, py), 7)
            pygame.draw.circle(world, (255, 255, 255), (px - 2, py - 2), 3)

        # bomen en struiken
        for _ in range(int(w * h / 19000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            if self.near(x, y, HALF + 100):
                continue
            draw_tree(world, x, y, random.randint(26, 52))
        for _ in range(int(w * h / 60000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            if self.near(x, y, HALF + 70):
                continue
            pygame.draw.circle(world, (110, 110, 118), (x, y), random.randint(6, 12))
            pygame.draw.circle(world, (150, 150, 158), (x - 2, y - 2), random.randint(3, 6))
        self.world = world


def make_grass_tile(size=256):
    t = pygame.Surface((size, size))
    t.fill((44, 138, 62))
    for _ in range(2600):
        d = random.randint(-14, 14)
        c = (clamp(44 + d, 0, 255), clamp(138 + d, 0, 255), clamp(62 + d // 2, 0, 255))
        pygame.draw.circle(t, c, (random.randrange(size), random.randrange(size)),
                           random.randint(1, 3))
    return t


def draw_tree(world, x, y, r):
    pad = 20
    sh = pygame.Surface((r * 2 + pad * 2, r * 2 + pad * 2), pygame.SRCALPHA)
    pygame.draw.circle(sh, (0, 0, 0, 70), (r + pad + 10, r + pad + 12), r)
    world.blit(sh, (x - r - pad, y - r - pad))
    base = random.choice([(30, 105, 45), (36, 122, 52), (26, 96, 42)])
    dark = tuple(int(c * 0.7) for c in base)
    light = tuple(min(255, int(c * 1.35) + 8) for c in base)
    pygame.draw.circle(world, dark, (x, y), r)
    pygame.draw.circle(world, base, (int(x - r * 0.12), int(y - r * 0.12)), int(r * 0.85))
    pygame.draw.circle(world, light, (int(x - r * 0.3), int(y - r * 0.3)), int(r * 0.4))


# ------------------------------------------------------------------ UI-helpers
GLOW = {}          # wordt gevuld in make_assets()


def text(surf, font, s, pos, color=(255, 255, 255), anchor="topleft", shadow=True):
    img = font.render(s, True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font.render(s, True, (0, 0, 0))
        sh.set_alpha(120)
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def panel(surf, rect, alpha=150, radius=16, border=True):
    r = pygame.Rect(rect)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (10, 14, 22, alpha), s.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(s, (255, 255, 255, 40), s.get_rect(), 2, border_radius=radius)
    surf.blit(s, r.topleft)


def make_glow(size, color, power=2.0):
    """Zachte gloed (RGB, bedoeld voor additief tekenen)."""
    s = pygame.Surface((size, size))
    c = size / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
            v = max(0.0, 1 - d) ** power
            s.set_at((x, y), (int(color[0] * v), int(color[1] * v), int(color[2] * v)))
    return s


def make_cone(L=150):
    """Koplampbundel, wijst naar rechts vanuit het midden."""
    s = pygame.Surface((L * 2, L * 2))
    for x in range(L):
        hw = 6 + x * 0.6
        fall = (1 - x / L) ** 1.4
        for dy in range(-int(hw), int(hw) + 1):
            v = fall * (1 - abs(dy) / (hw + 1)) ** 1.3 * 0.5
            s.set_at((L + x, L + dy), (int(255 * v), int(240 * v), int(190 * v)))
    return s


def make_dial(size=200):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    pygame.draw.circle(s, (10, 14, 22, 175), (c, c), c)
    pygame.draw.circle(s, (255, 255, 255, 45), (c, c), c, 2)
    font = pygame.font.SysFont("segoeui,arial", 14, bold=True)
    for v in range(0, 301, 20):
        ang = math.radians(135 + 270 * v / 300)
        major = v % 60 == 0
        r1, r2 = c - 6, c - (18 if major else 12)
        col = (255, 80, 70) if v >= 240 else (235, 235, 240)
        pygame.draw.line(s, col, (c + math.cos(ang) * r1, c + math.sin(ang) * r1),
                         (c + math.cos(ang) * r2, c + math.sin(ang) * r2), 3 if major else 2)
        if major:
            img = font.render(str(v), True, col)
            s.blit(img, img.get_rect(center=(c + math.cos(ang) * (c - 34),
                                             c + math.sin(ang) * (c - 34))))
    return s


def make_vignette():
    small = pygame.Surface((160, 90), pygame.SRCALPHA)
    for y in range(90):
        for x in range(160):
            d = math.hypot((x - 80) / 80, (y - 45) / 45)
            a = int(120 * clamp((d - 0.6) / 0.7, 0, 1) ** 2)
            small.set_at((x, y), (0, 0, 0, a))
    return pygame.transform.smoothscale(small, (W, H))


def make_menu_bg():
    s = pygame.Surface((W, H))
    for y in range(H):
        t = y / H
        pygame.draw.line(s, (int(12 + 26 * t), int(18 + 10 * t), int(38 + 34 * t)), (0, y), (W, y))
    stripes = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(-2, 9):
        x = i * 220
        pygame.draw.polygon(stripes, (255, 255, 255, 9),
                            [(x, 0), (x + 90, 0), (x + 90 - 360, H), (x - 360, H)])
    s.blit(stripes, (0, 0))
    return s


def make_hue_strip(w, h):
    s = pygame.Surface((w, h))
    for x in range(w):
        pygame.draw.line(s, hsv(x / w), (x, 0), (x, h))
    return s


# ------------------------------------------------------------------ auto-uiterlijk
def make_car_big(color, accent, body):
    """Auto van boven gezien, kijkend naar rechts (240x120)."""
    big = pygame.Surface((240, 120), pygame.SRCALPHA)
    dark = (24, 24, 28)
    shade = tuple(int(c * 0.72) for c in color)
    light = tuple(min(255, int(c * 1.2) + 25) for c in color)
    if body == 0:                                                       # formule
        for rect in [(30, 4, 56, 26), (30, 90, 56, 26), (158, 6, 46, 22), (158, 92, 46, 22)]:
            pygame.draw.rect(big, dark, rect, border_radius=8)
        pygame.draw.rect(big, dark, (6, 20, 20, 80), border_radius=4)
        pygame.draw.rect(big, accent, (6, 16, 20, 8))
        pygame.draw.rect(big, accent, (6, 96, 20, 8))
        poly = [(22, 34), (120, 28), (176, 38), (228, 54), (228, 66), (176, 82), (120, 92), (22, 86)]
        pygame.draw.polygon(big, color, poly)
        pygame.draw.polygon(big, shade, [(22, 62), (228, 62), (228, 66), (176, 82), (120, 92), (22, 86)])
        pygame.draw.polygon(big, light, [(30, 37), (120, 32), (172, 41), (220, 54), (120, 46), (30, 47)])
        pygame.draw.polygon(big, accent, [(50, 57), (228, 57), (228, 63), (50, 63)])
        pygame.draw.rect(big, dark, (222, 22, 10, 76), border_radius=3)
        pygame.draw.rect(big, accent, (222, 18, 10, 8))
        pygame.draw.rect(big, accent, (222, 94, 10, 8))
        pygame.draw.ellipse(big, (24, 30, 46), (92, 42, 64, 36))
        pygame.draw.ellipse(big, (80, 105, 140), (100, 46, 30, 12))
        pygame.draw.circle(big, (250, 250, 250), (122, 60), 11)
        pygame.draw.circle(big, light, (122, 60), 5)
    elif body == 1:                                                     # sportwagen
        for rect in [(34, 4, 50, 24), (34, 92, 50, 24), (150, 4, 50, 24), (150, 92, 50, 24)]:
            pygame.draw.rect(big, dark, rect, border_radius=8)
        pygame.draw.rect(big, shade, (12, 22, 216, 80), border_radius=36)
        pygame.draw.rect(big, color, (12, 18, 216, 80), border_radius=36)
        pygame.draw.rect(big, light, (36, 23, 168, 12), border_radius=6)
        pygame.draw.rect(big, accent, (14, 52, 212, 6))
        pygame.draw.rect(big, accent, (14, 62, 212, 6))
        pygame.draw.polygon(big, (24, 30, 46), [(92, 30), (150, 36), (166, 60), (150, 84), (92, 90), (80, 60)])
        pygame.draw.rect(big, color, (100, 42, 42, 36), border_radius=10)
        pygame.draw.rect(big, accent, (100, 56, 42, 8))
        pygame.draw.rect(big, light, (104, 44, 30, 6), border_radius=3)
        pygame.draw.ellipse(big, (255, 245, 200), (206, 24, 14, 16))
        pygame.draw.ellipse(big, (255, 245, 200), (206, 80, 14, 16))
        pygame.draw.rect(big, (200, 20, 20), (12, 28, 6, 16), border_radius=2)
        pygame.draw.rect(big, (200, 20, 20), (12, 76, 6, 16), border_radius=2)
    else:                                                               # rally
        for rect in [(28, 2, 52, 26), (28, 92, 52, 26), (152, 2, 52, 26), (152, 92, 52, 26)]:
            pygame.draw.rect(big, dark, rect, border_radius=8)
        pygame.draw.rect(big, dark, (4, 10, 18, 100), border_radius=4)
        pygame.draw.rect(big, accent, (4, 6, 18, 6))
        pygame.draw.rect(big, accent, (4, 108, 18, 6))
        pygame.draw.rect(big, shade, (24, 24, 196, 76), border_radius=18)
        pygame.draw.rect(big, color, (24, 20, 196, 76), border_radius=18)
        pygame.draw.rect(big, accent, (34, 26, 170, 5))
        pygame.draw.rect(big, accent, (34, 85, 170, 5))
        pygame.draw.rect(big, shade, (150, 46, 56, 26), border_radius=6)
        pygame.draw.rect(big, dark, (160, 52, 36, 14), border_radius=4)
        pygame.draw.rect(big, (24, 30, 46), (82, 30, 62, 56), border_radius=12)
        pygame.draw.rect(big, color, (92, 38, 44, 40), border_radius=8)
        pygame.draw.circle(big, (245, 245, 245), (114, 58), 11)
        pygame.draw.circle(big, accent, (114, 58), 6)
        pygame.draw.rect(big, dark, (216, 22, 12, 72), border_radius=4)
        pygame.draw.rect(big, accent, (216, 22, 12, 6))
        pygame.draw.rect(big, accent, (216, 88, 12, 6))
        pygame.draw.circle(big, (255, 240, 170), (206, 32), 7)
        pygame.draw.circle(big, (255, 240, 170), (206, 84), 7)
    return big


def make_car_sprite(color, accent, body):
    return pygame.transform.smoothscale(make_car_big(color, accent, body), (60, 30))


# ------------------------------------------------------------------ auto
class Car:
    def __init__(self, track, idx, offset, look, params, name, is_player=False):
        p = track.pts[idx]
        nx, ny = track.normals[idx]
        self.x, self.y = p[0] + nx * offset, p[1] + ny * offset
        self.heading = track.headings[idx]
        self.vx = self.vy = 0.0
        self.vmax = self.base_vmax = params["vmax"]
        self.accel = params["accel"]
        self.turn = params.get("turn", 1.0)
        self.nitro_cap = params.get("nitro", 100)
        self.nitro = self.nitro_cap
        self.boosting = False
        self.braking = False
        self.name = name
        self.is_player = is_player
        self.color = tuple(look["color"])
        self.idx = idx
        self.progress = idx - track.n          # negatief: nog voor de startlijn
        self.laps = 0
        self.lap_times = []
        self.last_lap_t = 0.0
        self.finished = False
        self.finish_time = None
        self.slip = 0.0
        self.on_road = True
        self.sprite = make_car_sprite(look["color"], look["accent"], look["body"])
        self.shadow = pygame.mask.from_surface(self.sprite).to_surface(
            setcolor=(0, 0, 0, 95), unsetcolor=(0, 0, 0, 0))

    @property
    def forward_speed(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    def physics(self, track, dt, throttle, brake, steer, hand=False, boost=False, grip_mult=1.0):
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        vf = self.vx * fx + self.vy * fy
        grip_turn = clamp(vf / 140, -1, 1)
        turn = TURN_RATE * self.turn * (1 - TURN_LOSS * min(1, abs(vf) / self.vmax))
        self.heading += steer * turn * grip_turn * dt * (1.25 if hand else 1.0)

        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        vf = self.vx * fx + self.vy * fy
        vl = self.vx * rx + self.vy * ry

        on = track.on_road(self.x, self.y)
        boosting = bool(boost and throttle and self.nitro > 0)
        if boosting:
            self.nitro = max(0.0, self.nitro - NITRO_USE * dt)
        else:
            self.nitro = min(self.nitro_cap, self.nitro + NITRO_REGEN * dt)
        self.boosting = boosting
        accel = self.accel * (1.7 if boosting else 1.0)
        vmax = self.vmax * (1.2 if boosting else 1.0)
        acc = accel * (1.0 if on else 0.55)
        if throttle:
            vf += acc * dt
        self.braking = bool(brake and vf > 20)
        if brake:
            if vf > 20:
                vf -= BRAKE * dt
            else:
                vf -= acc * 0.5 * dt
        drag = accel / vmax + (0 if on else 1.6)
        vf -= vf * drag * dt
        if not throttle and not brake:
            vf -= math.copysign(min(abs(vf), 90 * dt), vf)
        if hand:
            vf -= vf * 0.7 * dt
        vf = max(vf, -self.vmax * 0.3)
        grip = (12.0 if on else 6.0) * grip_mult
        if hand:
            grip = 2.5
        vl *= math.exp(-grip * dt)

        self.vx = fx * vf + rx * vl
        self.vy = fy * vf + ry * vl
        self.x = clamp(self.x + self.vx * dt, 20, track.w - 20)
        self.y = clamp(self.y + self.vy * dt, 20, track.h - 20)
        self.slip = abs(vl)
        self.on_road = on

    def update_progress(self, track):
        n = track.n
        best, best_off = 1e18, 0
        for off in range(-25, 26):
            px, py = track.pts[(self.idx + off) % n]
            d = (px - self.x) ** 2 + (py - self.y) ** 2
            if d < best:
                best, best_off = d, off
        self.idx = (self.idx + best_off) % n
        self.progress += best_off

    def respawn(self, track):
        p = track.pts[self.idx]
        self.x, self.y = p
        self.heading = track.headings[self.idx]
        self.vx = self.vy = 0.0

    def draw(self, screen, cx, cy):
        if not (-90 < self.x - cx < W + 90 and -90 < self.y - cy < H + 90):
            return
        ang = -math.degrees(self.heading)
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        sh = pygame.transform.rotozoom(self.shadow, ang, 1)
        screen.blit(sh, sh.get_rect(center=(self.x - cx + 7, self.y - cy + 9)))
        sp = pygame.transform.rotozoom(self.sprite, ang, 1)
        screen.blit(sp, sp.get_rect(center=(self.x - cx, self.y - cy)))
        if self.braking and "red" in GLOW:                      # remlichten
            g = GLOW["red"]
            for s in (-1, 1):
                px = self.x - cx - fx * 27 + rx * s * 9
                py = self.y - cy - fy * 27 + ry * s * 9
                screen.blit(g, g.get_rect(center=(px, py)), special_flags=pygame.BLEND_RGB_ADD)
        if self.boosting and "blue" in GLOW:                    # nitro-gloed
            g = GLOW["blue"]
            px = self.x - cx - fx * 34
            py = self.y - cy - fy * 34
            screen.blit(g, g.get_rect(center=(px, py)), special_flags=pygame.BLEND_RGB_ADD)


def collide(a, b):
    """Botsing tussen twee auto's. Geeft de botssterkte terug (0 = geen botsing)."""
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy) or 0.001
    if d >= 40:
        return 0.0
    nx, ny = dx / d, dy / d
    push = (40 - d) / 2
    a.x -= nx * push
    a.y -= ny * push
    b.x += nx * push
    b.y += ny * push
    rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if rel < 0:
        imp = -rel * 0.55
        a.vx -= nx * imp
        a.vy -= ny * imp
        b.vx += nx * imp
        b.vy += ny * imp
        return -rel
    return 0.0


# ------------------------------------------------------------------ AI-bot
class AIDriver:
    def __init__(self, car, track, cfg, skill, others, target, wet):
        self.car, self.track, self.cfg = car, track, cfg
        self.others = others           # alle andere auto's (om uit te wijken)
        self.target = target           # de speler (voor inhaalhulp / afremmen)
        self.line_off = random.uniform(-38, 38)
        self.stuck = 0.0
        vmax = car.base_vmax
        n = track.n
        corner = cfg["ai_corner"] * (1 - (1 - skill) * 0.8) * (0.93 if wet else 1.0)
        allowed = []
        for i in range(n):
            R = 1 / max(track.kappa[i], 1 / 3000)
            v = TURN_RATE * R / (1 + TURN_RATE * TURN_LOSS * R / vmax)
            allowed.append(min(vmax, v * corner))
        decel = BRAKE * 0.65
        for _ in range(3):                           # tijdig afremmen voor bochten
            for i in reversed(range(n)):
                j = (i + 1) % n
                allowed[i] = min(allowed[i], math.sqrt(allowed[j] ** 2 + 2 * decel * DS))
        self.allowed = allowed
        # rechte stukken (ruim vooruit geen remmen nodig): daar mag nitro gebruikt worden
        self.straight = [all(allowed[(i + k) % n] >= 0.97 * vmax for k in range(0, 52, 2))
                         for i in range(n)]

    def control(self):
        c, t, cfg = self.car, self.track, self.cfg
        vf = c.forward_speed
        look = int((75 + abs(vf) * 0.22) / DS) + 1
        j = (c.idx + look) % t.n
        tx = t.pts[j][0] + t.normals[j][0] * self.line_off
        ty = t.pts[j][1] + t.normals[j][1] * self.line_off
        diff = wrap_rad(math.atan2(ty - c.y, tx - c.x) - c.heading)
        steer = clamp(diff * 2.6, -1, 1)

        # uitwijken voor auto's vlak voor je
        fx, fy = math.cos(c.heading), math.sin(c.heading)
        rx, ry = -fy, fx
        slow_for_car = False
        for o in self.others:
            dx, dy = o.x - c.x, o.y - c.y
            fw = dx * fx + dy * fy
            if 0 < fw < 120:
                lat = dx * rx + dy * ry
                if abs(lat) < 38:
                    side = -1 if lat > 0 else 1
                    if abs(lat) < 3:
                        side = 1 if self.line_off < 0 else -1
                    steer += side * (1 - fw / 120) * 1.1
                    if fw < 55 and vf > o.forward_speed + 40:
                        slow_for_car = True
        steer = clamp(steer, -1, 1)

        # snelheid: rubber-banding (inhalen / afremmen) afhankelijk van moeilijkheid
        mult = 1.0
        gap = self.target.progress - c.progress
        if cfg["rubber"] and gap > 0:
            mult += clamp(gap / 160, 0, 1) * cfg["rubber"]
        if cfg["mercy"]:
            mult -= clamp((-gap - 120) / 250, 0, 1) * cfg["mercy"]
        c.vmax = c.base_vmax * max(0.5, mult)

        target = self.allowed[(c.idx + 2) % t.n] * mult
        if not c.on_road:
            target *= 0.8
        boost = False
        if (cfg["nitro"] and c.nitro > 30 and self.straight[c.idx] and abs(diff) < 0.15
                and c.on_road and not slow_for_car):
            boost = True
            target = c.base_vmax * 1.18
        throttle = vf < target
        brake = vf > target * 1.06 or slow_for_car
        if abs(diff) > 1.0:
            throttle, brake, boost = vf < 120, False, False
        return throttle, brake, steer, boost


# ------------------------------------------------------------------ minimap
class MiniMap:
    def __init__(self, pts, bw, bh, pad=14, line=5):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.minx, self.miny = min(xs), min(ys)
        sw, sh = max(xs) - self.minx, max(ys) - self.miny
        self.scale = min((bw - 2 * pad) / sw, (bh - 2 * pad) / sh)
        self.pad = pad
        self.w = int(sw * self.scale + 2 * pad)
        self.h = int(sh * self.scale + 2 * pad)
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (10, 14, 22, 165), s.get_rect(), border_radius=16)
        pygame.draw.rect(s, (255, 255, 255, 40), s.get_rect(), 2, border_radius=16)
        mp = [self.to_map(x, y) for x, y in pts[::3]]
        pygame.draw.lines(s, (0, 0, 0, 200), True, mp, line + 4)
        pygame.draw.lines(s, (235, 235, 240), True, mp, line)
        sx, sy = self.to_map(*pts[0])
        pygame.draw.circle(s, (255, 220, 60), (int(sx), int(sy)), line + 2)
        pygame.draw.circle(s, (20, 20, 20), (int(sx), int(sy)), line + 2, 2)
        self.surf = s

    def to_map(self, x, y):
        return ((x - self.minx) * self.scale + self.pad, (y - self.miny) * self.scale + self.pad)


# ------------------------------------------------------------------ confetti
class Confetti:
    def __init__(self):
        self.p = []

    def update(self, dt, spawn=True):
        if spawn:
            for _ in range(3):
                self.p.append([random.uniform(0, W), -10, random.uniform(-40, 40),
                               random.uniform(120, 260), random.choice(PALETTE + ACCENTS),
                               random.uniform(6, 11), random.uniform(0, TAU)])
        for q in self.p:
            q[6] += dt * 7
            q[0] += (q[2] + math.sin(q[6]) * 40) * dt
            q[1] += q[3] * dt
        self.p = [q for q in self.p if q[1] < H + 20][-300:]

    def draw(self, surf):
        for x, y, _, _, col, size, ph in self.p:
            w = max(2, int(abs(math.cos(ph)) * size))
            pygame.draw.rect(surf, col, (int(x), int(y), w, int(size * 0.7)))


# ------------------------------------------------------------------ race
class Race:
    def __init__(self, raw, level, opts, car_cfg, field, grid):
        self.level = level
        cfg = self.cfg = LEVELS[level]
        self.laps = opts["laps"]
        self.wet = bool(opts["weather"])
        self.grip = 0.72 if self.wet else 1.0
        self.track = Track(raw)
        self.track.render()
        t = self.track

        info = {"Jij": (dict(color=tuple(car_cfg["color"]), accent=tuple(car_cfg["accent"]),
                             body=car_cfg["body"]), car_params(car_cfg["stats"]), 1.0)}
        for f in field:
            look = dict(color=f["color"], accent=f["accent"], body=f["body"])
            prm = dict(vmax=cfg["ai_vmax"] * f["skill"], accel=BASE_ACCEL, turn=1.0, nitro=100)
            info[f["name"]] = (look, prm, f["skill"])

        self.cars = []
        for slot, name in enumerate(grid):
            row, col = divmod(slot, 2)
            idx = t.n - 6 - 5 * row - (2 if col else 0)
            look, prm, _ = info[name]
            self.cars.append(Car(t, idx, 30 if col else -30, look, prm, name, name == "Jij"))
        self.player = next(c for c in self.cars if c.is_player)
        self.drivers = []
        for c in self.cars:
            if not c.is_player:
                others = [o for o in self.cars if o is not c]
                self.drivers.append(AIDriver(c, t, cfg, info[c.name][2], others, self.player, self.wet))

        self.minimap = MiniMap(t.pts, 240, 200)
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        self.top = pygame.Surface((W, H), pygame.SRCALPHA)
        self.mark = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(self.mark, (10, 10, 12, 70), (3, 3), 3)
        self.particles = []
        self.rain = [[random.uniform(0, W), random.uniform(0, H), random.uniform(700, 1000)]
                     for _ in range(170)] if self.wet else []
        self.confetti = Confetti()
        self.state = "countdown"
        self.countdown = 3.0
        self.go_t = 0.0
        self.time = 0.0
        self.shake = 0.0
        self.banner = None
        self._was_boost = False
        self.cam_x = clamp(self.player.x - W / 2, 0, t.w - W)
        self.cam_y = clamp(self.player.y - H / 2, 0, t.h - H)
        self.dial = make_dial(200)

    # ---- hulpjes
    def ranking(self):
        return sorted(self.cars, key=lambda c: (0, c.finish_time) if c.finished else (1, -c.progress))

    def say(self, title, sub="", col=(255, 255, 255)):
        self.banner = [title, sub, col, 0.0]

    def visible(self, car, m=100):
        return (abs(car.x - (self.cam_x + W / 2)) < W / 2 + m
                and abs(car.y - (self.cam_y + H / 2)) < H / 2 + m)

    def spawn(self, x, y, vx, vy, life, size, col, kind=0):
        self.particles.append([x, y, vx, vy, 0.0, life, size, col, kind])

    # ---- logica
    def update(self, dt, keys):
        dt = min(dt, 0.05)
        t, p = self.track, self.player
        if self.state == "countdown":
            self.countdown -= dt
            if self.countdown <= 0:
                self.state, self.go_t = "race", 1.2
        else:
            self.time += dt
            self.go_t = max(0, self.go_t - dt)
            if self.state == "race" and not p.finished:
                thr = keys[pygame.K_UP] or keys[pygame.K_w]
                brk = keys[pygame.K_DOWN] or keys[pygame.K_s]
                steer = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
                hand = keys[pygame.K_SPACE]
                boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            else:                                   # klaar met racen: uitrollen
                thr, steer, hand, boost = False, 0, False, False
                brk = p.forward_speed > 30
            p.physics(t, dt, thr, brk, steer, hand, boost, self.grip)
            for d in self.drivers:
                a_thr, a_brk, a_steer, a_boost = d.control()
                d.car.physics(t, dt, a_thr, a_brk, a_steer, False, a_boost, self.grip)

            cars = self.cars
            for i in range(len(cars)):
                for j in range(i + 1, len(cars)):
                    imp = collide(cars[i], cars[j])
                    if imp > 20:
                        a, b = cars[i], cars[j]
                        if self.visible(a):
                            mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                            for _ in range(int(min(14, imp / 12))):
                                ang = random.uniform(0, TAU)
                                sp = random.uniform(80, 280)
                                self.spawn(mx, my, math.cos(ang) * sp, math.sin(ang) * sp,
                                           random.uniform(0.2, 0.45), random.uniform(2, 3.5),
                                           random.choice([(255, 220, 110), (255, 160, 60)]), 1)
                        if a.is_player or b.is_player:
                            self.shake = max(self.shake, min(9, imp * 0.045))

            for c in cars:
                c.update_progress(t)
                laps = max(0, int(c.progress // t.n))
                if laps > c.laps:
                    c.laps = laps
                    lt = self.time - c.last_lap_t
                    c.last_lap_t = self.time
                    c.lap_times.append(lt)
                    if c.is_player and laps < self.laps:
                        best = len(c.lap_times) > 1 and lt <= min(c.lap_times)
                        if laps == self.laps - 1:
                            self.say("LAATSTE RONDE!", fmt(lt), (255, 120, 90))
                        elif best:
                            self.say("BESTE RONDE!", fmt(lt), (190, 120, 255))
                        else:
                            self.say(f"RONDE {laps + 1} / {self.laps}", fmt(lt))
                if c.laps >= self.laps and not c.finished:
                    c.finished, c.finish_time = True, self.time
            for c in cars:
                self._effects(c, dt, c.is_player and hand)

            # bots die vastzitten terugzetten
            for d in self.drivers:
                a = d.car
                if math.hypot(a.vx, a.vy) < 35:
                    d.stuck += dt
                    if d.stuck > 2.0:
                        a.respawn(t)
                        d.stuck = 0
                else:
                    d.stuck = 0

            if p.boosting and not self._was_boost:
                self.shake = max(self.shake, 3.5)
            self._was_boost = p.boosting
            if not p.on_road and math.hypot(p.vx, p.vy) > 200:
                self.shake = max(self.shake, 1.6)

            if p.finished and self.state == "race":
                self.state = "finished"
                self.say("FINISH!", "", (255, 220, 70))

        if self.state == "finished" and self.ranking()[0] is p:
            self.confetti.update(dt)
        elif self.confetti.p:
            self.confetti.update(dt, spawn=False)

        # deeltjes
        damp = max(0.0, 1 - 3.2 * dt)
        for q in self.particles:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] += dt
            if q[8] == 1:
                q[2] *= damp
                q[3] *= damp
        self.particles = [q for q in self.particles if q[4] < q[5]][-520:]
        for d in self.rain:
            d[1] += d[2] * dt
            d[0] -= 140 * dt
            if d[1] > H:
                d[0], d[1] = random.uniform(0, W + 150), -20
            if d[0] < -20:
                d[0] = W + 20
        self.shake *= max(0.0, 1 - 7 * dt)
        if self.banner:
            self.banner[3] += dt
            if self.banner[3] > 2.6:
                self.banner = None

        # camera
        tx = p.x + p.vx * 0.28 - W / 2
        ty = p.y + p.vy * 0.28 - H / 2
        k = min(1, dt * 5)
        self.cam_x = clamp(self.cam_x + (tx - self.cam_x) * k, 0, t.w - W)
        self.cam_y = clamp(self.cam_y + (ty - self.cam_y) * k, 0, t.h - H)

    def _effects(self, car, dt, hand):
        if not self.visible(car, 150):
            return
        fx, fy = math.cos(car.heading), math.sin(car.heading)
        rx, ry = -fy, fx
        speed = math.hypot(car.vx, car.vy)
        wheels = [(car.x - fx * 18 + rx * s * 10, car.y - fy * 18 + ry * s * 10) for s in (-1, 1)]
        if car.slip > 72 and car.on_road:                       # bandensporen
            for wx, wy in wheels:
                self.track.world.blit(self.mark, (wx - 3, wy - 3))
        if car.slip > 85 or (hand and speed > 150):             # rook
            for wx, wy in wheels:
                if random.random() < 0.5:
                    self.spawn(wx, wy, random.uniform(-25, 25), random.uniform(-25, 25),
                               random.uniform(0.5, 0.9), random.uniform(5, 9), (225, 225, 230))
        if hand and speed > 200 and car.on_road:                # driftvonken
            for wx, wy in wheels:
                if random.random() < 0.35:
                    self.spawn(wx, wy, -fx * 90 + random.uniform(-70, 70),
                               -fy * 90 + random.uniform(-70, 70), random.uniform(0.15, 0.35),
                               random.uniform(1.5, 2.5), (255, 190, 90), 1)
        if not car.on_road and speed > 90:                      # stof/gras
            for wx, wy in wheels:
                if random.random() < 0.6:
                    self.spawn(wx, wy, random.uniform(-40, 40), random.uniform(-40, 40),
                               random.uniform(0.4, 0.8), random.uniform(5, 10), (150, 130, 90))
        if self.wet and car.on_road and speed > 200:            # opspattend water
            for wx, wy in wheels:
                if random.random() < 0.4:
                    self.spawn(wx, wy, random.uniform(-30, 30), random.uniform(-30, 30),
                               random.uniform(0.3, 0.6), random.uniform(4, 7), (170, 190, 215))
        if car.boosting:                                        # nitro-vlammen
            ex, ey = car.x - fx * 30, car.y - fy * 30
            for _ in range(2):
                self.spawn(ex + random.uniform(-3, 3), ey + random.uniform(-3, 3),
                           -fx * random.uniform(140, 240) + car.vx * 0.3,
                           -fy * random.uniform(140, 240) + car.vy * 0.3,
                           random.uniform(0.12, 0.26), random.uniform(5, 9),
                           random.choice([(255, 170, 60), (110, 170, 255), (255, 240, 180)]), 2)

    # ---- tekenen
    def draw(self, screen, A):
        t, p = self.track, self.player
        sx = sy = 0.0
        if self.shake > 0.3:
            sx, sy = random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)
        cx = int(clamp(self.cam_x + sx, 0, t.w - W))
        cy = int(clamp(self.cam_y + sy, 0, t.h - H))
        screen.blit(t.world, (0, 0), pygame.Rect(cx, cy, W, H))

        self.fx.fill((0, 0, 0, 0))
        for x, y, _, _, age, life, size, col, kind in self.particles:
            px, py = int(x - cx), int(y - cy)
            if not (-30 < px < W + 30 and -30 < py < H + 30):
                continue
            u = age / life
            if kind == 0:                                       # rook / stof
                pygame.draw.circle(self.fx, (*col, int(150 * (1 - u))), (px, py), int(size * (1 + u * 1.6)))
            elif kind == 1:                                     # vonken
                pygame.draw.circle(self.fx, (*col, int(255 * (1 - u))), (px, py), max(1, int(size * (1 - u * 0.6))))
            else:                                               # vlammen
                pygame.draw.circle(self.fx, (*col, int(230 * (1 - u))), (px, py), max(1, int(size * (1 - u * 0.7))))
        screen.blit(self.fx, (0, 0))

        for c in self.cars:
            if not c.is_player:
                c.draw(screen, cx, cy)
        p.draw(screen, cx, cy)

        # bovenlaag: regen, donker, snelheidslijnen
        used = False
        self.top.fill((0, 0, 0, 0))
        if self.wet:
            self.top.fill((8, 14, 34, 78))
            for x, y, sp in self.rain:
                pygame.draw.line(self.top, (190, 205, 235, 130), (x, y), (x + 3, y - sp * 0.022), 1)
            used = True
        speed = math.hypot(p.vx, p.vy)
        if speed > 330 or p.boosting:
            k = clamp((speed - 330) / 260, 0, 1)
            if p.boosting:
                k = max(k, 0.8)
            col = (170, 205, 255, int(70 + 90 * k)) if p.boosting else (255, 255, 255, int(40 + 70 * k))
            for _ in range(int(8 + 16 * k)):
                a = random.uniform(0, TAU)
                r1 = random.uniform(260, 420)
                r2 = r1 + random.uniform(60, 170) * (0.6 + k)
                pygame.draw.line(self.top, col,
                                 (W / 2 + math.cos(a) * r1 * 1.4, H / 2 + math.sin(a) * r1 * 0.8),
                                 (W / 2 + math.cos(a) * r2 * 1.4, H / 2 + math.sin(a) * r2 * 0.8), 2)
            used = True
        if used:
            screen.blit(self.top, (0, 0))
        if self.wet and "cone" in GLOW:                         # koplampen in de regen
            cone = GLOW["cone"]
            for c in self.cars:
                if -200 < c.x - cx < W + 200 and -200 < c.y - cy < H + 200:
                    rot = pygame.transform.rotozoom(cone, -math.degrees(c.heading), 1)
                    px = c.x - cx + math.cos(c.heading) * 10
                    py = c.y - cy + math.sin(c.heading) * 10
                    screen.blit(rot, rot.get_rect(center=(px, py)), special_flags=pygame.BLEND_RGB_ADD)

        screen.blit(A["vignette"], (0, 0))
        self._hud(screen, A)

    def _hud(self, screen, A):
        f = A["fonts"]
        p = self.player
        order = self.ranking()
        pos = order.index(p)

        # links boven: ronde / tijd
        panel(screen, (20, 20, 270, 118))
        text(screen, f["s"], "RONDE", (38, 30), (160, 175, 200))
        text(screen, f["l"], f"{min(p.laps + 1, self.laps)}/{self.laps}", (38, 46))
        text(screen, f["s"], "TIJD", (170, 30), (160, 175, 200))
        text(screen, f["m"], fmt(p.finish_time if p.finished else self.time), (170, 48))
        best = min(p.lap_times) if p.lap_times else None
        text(screen, f["s"], f"BESTE RONDE  {fmt(best)}", (38, 104), (200, 210, 230))

        # links: tussenstand
        rows = len(order)
        panel(screen, (20, 148, 210, 36 + rows * 26))
        text(screen, f["s"], "STAND", (36, 154), (160, 175, 200))
        for i, c in enumerate(order):
            y = 184 + i * 26
            pygame.draw.circle(screen, (255, 255, 255), (40, y + 11), 8)
            pygame.draw.circle(screen, c.color, (40, y + 11), 6)
            col = (255, 220, 70) if c.is_player else (215, 222, 238)
            text(screen, f["s"], f"{i + 1}. {c.name}", (56, y), col)

        # midden boven: positie
        medal = [(255, 220, 70), (215, 220, 230), (225, 150, 90)]
        pcol = medal[pos] if pos < 3 else (255, 255, 255)
        panel(screen, (W // 2 - 95, 20, 190, 96))
        text(screen, f["s"], "POSITIE", (W // 2, 28), (160, 175, 200), "midtop")
        text(screen, f["l"], str(pos + 1), (W // 2 - 10, 76), pcol, "midright")
        text(screen, f["m"], f"/{rows}", (W // 2 - 4, 80), (190, 200, 220), "midleft")
        if pos > 0:
            gap = (order[pos - 1].progress - p.progress) * DS / 10
            text(screen, f["s"], f"-{gap:.0f} m", (W // 2, 100), (255, 120, 110), "midtop")
        elif rows > 1:
            gap = (p.progress - order[1].progress) * DS / 10
            text(screen, f["s"], f"+{gap:.0f} m", (W // 2, 100), (110, 235, 140), "midtop")

        # rechts boven: minimap
        mm = self.minimap
        mx, my = W - 20 - mm.w, 20
        screen.blit(mm.surf, (mx, my))
        for c in sorted(self.cars, key=lambda c: c.is_player):
            qx, qy = mm.to_map(c.x, c.y)
            r = 7 if c.is_player else 5
            pygame.draw.circle(screen, (255, 255, 255), (int(mx + qx), int(my + qy)), r + 2)
            pygame.draw.circle(screen, c.color, (int(mx + qx), int(my + qy)), r)

        # rechts onder: snelheidsmeter
        dx, dy = W - 220, H - 220
        screen.blit(self.dial, (dx, dy))
        kmh = clamp(abs(p.forward_speed) * 0.5, 0, 300)
        ang = math.radians(135 + 270 * kmh / 300)
        c = 100
        pygame.draw.line(screen, (255, 90, 70), (dx + c, dy + c),
                         (dx + c + math.cos(ang) * 72, dy + c + math.sin(ang) * 72), 4)
        pygame.draw.circle(screen, (30, 32, 40), (dx + c, dy + c), 9)
        pygame.draw.circle(screen, (255, 255, 255), (dx + c, dy + c), 9, 2)
        text(screen, f["m"], f"{kmh:.0f}", (dx + c, dy + 140), anchor="midtop")
        text(screen, f["s"], "km/h", (dx + c, dy + 172), (160, 175, 200), "midtop")

        # onder: nitro-meter
        bw, bh = 300, 18
        bx, by = W // 2 - bw // 2, H - 52
        panel(screen, (bx - 12, by - 26, bw + 24, bh + 40), 140, 12)
        text(screen, f["s"], "NITRO  (SHIFT)", (W // 2, by - 22), (160, 175, 200), "midtop", False)
        pygame.draw.rect(screen, (30, 36, 52), (bx, by, bw, bh), border_radius=9)
        frac = p.nitro / p.nitro_cap
        if frac > 0.01:
            col = (255, 230, 120) if p.boosting else (80, 160, 255)
            pygame.draw.rect(screen, col, (bx, by, max(8, int(bw * frac)), bh), border_radius=9)
        pygame.draw.rect(screen, (255, 255, 255), (bx, by, bw, bh), 2, border_radius=9)

        # waarschuwingen
        if self.state == "race":
            t = self.track
            tvx, tvy = math.cos(t.headings[p.idx]), math.sin(t.headings[p.idx])
            if p.vx * tvx + p.vy * tvy < -60 and pygame.time.get_ticks() // 350 % 2 == 0:
                text(screen, f["l"], "VERKEERDE RICHTING!", (W // 2, 140), (255, 80, 70), "midtop")
            elif not p.on_road and pygame.time.get_ticks() // 400 % 2 == 0:
                text(screen, f["m"], "BUITEN HET CIRCUIT", (W // 2, 130), (255, 200, 80), "midtop")
            if self.time < 9:
                panel(screen, (20, H - 70, 640, 48), 120)
                text(screen, f["s"], "Pijltjes/WASD rijden  -  SHIFT nitro  -  SPATIE handrem  -  T terugzetten  -  ESC pauze",
                     (36, H - 56), (210, 220, 240))

        # banner (ronde / beste ronde / finish)
        if self.banner:
            title, sub, col, age = self.banner
            a = clamp(min(age / 0.2, (2.6 - age) / 0.6), 0, 1)
            panel(screen, (W // 2 - 220, 190, 440, 100 if sub else 70), int(170 * a))
            img = f["l"].render(title, True, col)
            img.set_alpha(int(255 * a))
            screen.blit(img, img.get_rect(midtop=(W // 2, 198)))
            if sub:
                img = f["m"].render(sub, True, (230, 235, 245))
                img.set_alpha(int(255 * a))
                screen.blit(img, img.get_rect(midtop=(W // 2, 250)))

        # startlichten
        if self.state == "countdown" or (self.state == "race" and self.go_t > 0):
            panel(screen, (W // 2 - 110, 150, 220, 80))
            lit = (3 - math.ceil(max(self.countdown, 0)) + 1) if self.state == "countdown" else 3
            for i in range(3):
                col = (50, 50, 55)
                if self.state == "race":
                    col = (60, 230, 90)
                elif i < lit:
                    col = (240, 40, 40)
                pygame.draw.circle(screen, col, (W // 2 - 60 + i * 60, 190), 22)
                pygame.draw.circle(screen, (0, 0, 0), (W // 2 - 60 + i * 60, 190), 22, 3)
            if self.state == "race":
                text(screen, f["xl"], "GO!", (W // 2, 250), (110, 255, 140), "midtop")


# ------------------------------------------------------------------ tegenstanders
def make_field(n, level, avoid_color):
    """Maak n bots met eigen naam, kleur, model en rijvaardigheid."""
    names = random.sample(BOT_NAMES, n)
    colors = [c for c in PALETTE if col_dist(c, avoid_color) > 90]
    random.shuffle(colors)
    spread = max(0.012, 0.035 - 0.005 * (level - 1))
    skills = [1 - spread * i - random.uniform(0, 0.008) for i in range(n)]
    random.shuffle(skills)
    field = []
    for i in range(n):
        field.append(dict(name=names[i], color=colors[i % len(colors)],
                          accent=random.choice(ACCENTS), body=random.randrange(len(BODY_NAMES)),
                          skill=skills[i]))
    return field


# ------------------------------------------------------------------ muis-interface
class UI:
    """Eenvoudige 'immediate mode' knoppen: tekenen en tegelijk registreren voor klikken."""

    def __init__(self, fonts):
        self.f = fonts
        self.buttons = []
        self.prev = []
        self.mouse = (0, 0)
        self.down = False
        self.hand = False

    def begin(self):
        self.prev, self.buttons = self.buttons, []
        self.mouse = pygame.mouse.get_pos()
        self.down = pygame.mouse.get_pressed()[0]

    def end(self):
        hover = any(r.collidepoint(self.mouse) for r, _ in self.buttons)
        if hover != self.hand:
            self.hand = hover
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hover else pygame.SYSTEM_CURSOR_ARROW)
            except Exception:
                pass

    def click(self, pos):
        for r, fn in reversed(self.prev):
            if r.collidepoint(pos):
                fn()
                return True
        return False

    def hit(self, rect, fn):
        """Onzichtbaar klikgebied."""
        self.buttons.append((pygame.Rect(rect), fn))

    def button(self, surf, rect, label, fn, selected=False, accent=(90, 160, 255),
               enabled=True, font="m"):
        r = pygame.Rect(rect)
        hover = enabled and r.collidepoint(self.mouse)
        if hover and self.down:
            r = r.move(0, 2)
        if not enabled:
            base = (24, 28, 38)
        elif selected:
            base = (46, 60, 96)
        elif hover:
            base = (54, 70, 108)
        else:
            base = (30, 38, 58)
        pygame.draw.rect(surf, base, r, border_radius=14)
        if selected:
            pygame.draw.rect(surf, accent, r, 3, border_radius=14)
        elif hover:
            pygame.draw.rect(surf, (160, 185, 240), r, 2, border_radius=14)
        else:
            pygame.draw.rect(surf, (80, 92, 120), r, 2, border_radius=14)
        if label:
            col = (255, 255, 255) if enabled else (105, 112, 130)
            text(surf, self.f[font], label, r.center, col, "center", False)
        if enabled:
            self.buttons.append((pygame.Rect(rect), fn))
        return hover

    def swatch(self, surf, rect, color, selected, fn):
        r = pygame.Rect(rect)
        hover = r.collidepoint(self.mouse)
        pygame.draw.rect(surf, color, r, border_radius=10)
        if selected:
            pygame.draw.rect(surf, (255, 255, 255), r.inflate(6, 6), 3, border_radius=12)
        elif hover:
            pygame.draw.rect(surf, (190, 205, 240), r.inflate(4, 4), 2, border_radius=11)
        else:
            pygame.draw.rect(surf, (0, 0, 0), r, 2, border_radius=10)
        self.buttons.append((r, fn))


def make_assets():
    def font(sz, bold=True):
        return pygame.font.SysFont("segoeui,arial,helvetica", sz, bold=bold)
    GLOW["red"] = make_glow(44, (255, 40, 30), 2.0)
    GLOW["blue"] = make_glow(70, (70, 140, 255), 2.0)
    GLOW["spot"] = make_glow(260, (70, 90, 150), 1.6)
    GLOW["cone"] = make_cone()
    return {
        "fonts": {"s": font(18), "m": font(28), "l": font(46), "xl": font(84)},
        "vignette": make_vignette(),
        "menu_bg": make_menu_bg(),
        "hue": make_hue_strip(600, 26),
    }


# ------------------------------------------------------------------ applicatie
class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED)
        pygame.display.set_caption("Top-down Racer 2 - Grand Prix")
        self.clock = pygame.time.Clock()
        self.A = make_assets()
        self.f = self.A["fonts"]
        self.ui = UI(self.f)
        self.save = load_save()
        self.state = "main"
        self.mode = "race"
        self.garage_from = "main"
        self.race = None
        self.paused = False
        self.cur_raw = None
        self.field = []
        self.gp = None
        self.now = 0.0
        self.dt = 0.0
        self.big_cache = {}
        self.hue_drag = False
        self.confetti = Confetti()
        self.streaks = [[random.uniform(0, W), random.uniform(0, H), random.uniform(60, 220),
                         random.uniform(300, 900)] for _ in range(26)]
        self.raw = self.mm = self.stats = None
        self.new_preview(False)

    # ---- algemeen
    def quit(self):
        write_save(self.save)
        pygame.quit()
        sys.exit()

    def show_loading(self, msg):
        self.screen.blit(self.A["menu_bg"], (0, 0))
        text(self.screen, self.f["l"], msg, (W // 2, H // 2), anchor="center")
        pygame.display.flip()
        pygame.event.pump()

    def new_preview(self, loading=True):
        if loading:
            self.show_loading("Circuit genereren...")
        self.raw = generate_centerline(self.save["level"])
        self.mm = MiniMap(self.raw, 360, 300, pad=24, line=8)
        self.stats = (len(self.raw) * DS / 10000, count_bends(self.raw))        # 10 px = 1 m
        self.preview_fresh = True

    def car_big(self, car):
        key = (tuple(car["color"]), tuple(car["accent"]), car["body"])
        if key not in self.big_cache:
            if len(self.big_cache) > 60:
                self.big_cache.clear()
            self.big_cache[key] = make_car_big(*key)
        return self.big_cache[key]

    def goto(self, state):
        write_save(self.save)
        self.state = state

    def open_setup(self, mode):
        self.mode = mode
        self.goto("setup")

    def open_garage(self, frm):
        self.garage_from = frm
        self.goto("garage")

    # ---- races starten / afronden
    def start_session(self):
        s = self.save
        write_save(s)
        pcol = tuple(s["car"]["color"])
        self.field = make_field(s["bots"], s["level"], pcol)
        if self.mode == "gp":
            names = ["Jij"] + [f["name"] for f in self.field]
            colors = {"Jij": pcol}
            colors.update({f["name"]: f["color"] for f in self.field})
            self.gp = dict(total=s["gp_races"], done=0, points={n: 0 for n in names},
                           colors=colors, last=None)
        else:
            self.gp = None
        self.begin_race("preview")

    def make_grid(self):
        names = ["Jij"] + [f["name"] for f in self.field]
        random.shuffle(names)
        if self.gp and self.gp["done"] > 0:                  # kampioenschapsleider op pole
            names.sort(key=lambda n: -self.gp["points"][n])
        return names

    def begin_race(self, track):
        """track: 'preview' (het voorbeeldcircuit), 'new' (nieuw circuit) of 'same'."""
        self.show_loading("Circuit wordt gebouwd...")
        s = self.save
        if track == "preview":
            self.cur_raw = self.raw
        elif track == "new":
            self.cur_raw = generate_centerline(s["level"])
        laps = s["laps_gp"] if self.mode == "gp" else s["laps_q"]
        self.race = Race(self.cur_raw, s["level"], dict(laps=laps, weather=s["weather"]),
                         s["car"], self.field, self.make_grid())
        self.state = "race"
        self.paused = False

    def leave_race(self):
        self.race = None
        self.paused = False
        self.gp = None
        self.goto("main")

    def results_continue(self):
        if self.mode == "gp":
            self.finish_gp_race()
        else:
            self.begin_race("same")

    def finish_gp_race(self):
        gp = self.gp
        order = self.race.ranking()
        last = []
        for i, c in enumerate(order):
            pts = POINTS[i] if i < len(POINTS) else 0
            gp["points"][c.name] += pts
            last.append((c.name, c.color, pts))
        gp["last"] = last
        gp["done"] += 1
        self.race = None
        self.state = "gp_final" if gp["done"] >= gp["total"] else "gp_standings"

    def next_gp_race(self):
        self.begin_race("new")

    def new_gp(self):
        self.mode = "gp"
        self.start_session()

    # ---- invoer
    def handle(self, e):
        if e.type == pygame.QUIT:
            self.quit()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ui.click(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.hue_drag = False
        elif e.type == pygame.KEYDOWN:
            self.on_key(e.key)

    def on_key(self, key):
        enter = key in (pygame.K_RETURN, pygame.K_KP_ENTER)
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        st = self.state
        if st == "main":
            if key == pygame.K_1:
                self.open_setup("race")
            elif key == pygame.K_2:
                self.open_setup("gp")
            elif key == pygame.K_3:
                self.open_garage("main")
            elif key in (pygame.K_4, pygame.K_ESCAPE):
                self.quit()
        elif st == "setup":
            if key == pygame.K_ESCAPE:
                self.goto("main")
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                self.set_level(key - pygame.K_0)
            elif key == pygame.K_n:
                self.new_preview()
            elif key == pygame.K_g:
                self.open_garage("setup")
            elif enter or key == pygame.K_SPACE:
                self.start_session()
        elif st == "garage":
            if key == pygame.K_ESCAPE or enter:
                self.goto(self.garage_from)
        elif st == "race":
            r = self.race
            if key == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif self.paused:
                if key == pygame.K_r:
                    self.begin_race("same")
                elif key == pygame.K_m:
                    self.leave_race()
            elif key == pygame.K_r:
                self.begin_race("same")
            elif key == pygame.K_m:
                self.leave_race()
            elif key == pygame.K_t and r.state == "race":
                r.player.respawn(r.track)
            elif enter and r.state == "finished":
                self.results_continue()
        elif st == "gp_standings":
            if enter or key == pygame.K_SPACE:
                self.next_gp_race()
            elif key == pygame.K_ESCAPE:
                self.leave_race()
        elif st == "gp_final":
            if key in (pygame.K_ESCAPE,) or enter:
                self.leave_race()

    def set_level(self, k):
        if k != self.save["level"]:
            self.save["level"] = k
            self.new_preview()

    def adjust(self, key, d, lo, hi):
        self.save[key] = int(clamp(self.save[key] + d, lo, hi))

    def set_weather(self, v):
        self.save["weather"] = v

    # ---- hoofdlus
    def run(self):
        while True:
            self.dt = self.clock.tick(FPS) / 1000
            self.now += self.dt
            self.ui.begin()
            for e in pygame.event.get():
                self.handle(e)
            self.update(self.dt)
            self.draw()
            self.ui.end()
            pygame.display.flip()

    def update(self, dt):
        if self.state == "race" and self.race and not self.paused:
            self.race.update(dt, pygame.key.get_pressed())
        elif self.state == "gp_final":
            champ = max(self.gp["points"], key=self.gp["points"].get)
            self.confetti.update(dt, spawn=(champ == "Jij"))

    def draw(self):
        st = self.state
        if st == "race":
            self.draw_race()
        elif st == "main":
            self.draw_main()
        elif st == "setup":
            self.draw_setup()
        elif st == "garage":
            self.draw_garage()
        elif st == "gp_standings":
            self.draw_gp_standings()
        elif st == "gp_final":
            self.draw_gp_final()

    # ---- gedeelde tekenhulp
    def draw_bg(self):
        scr = self.screen
        scr.blit(self.A["menu_bg"], (0, 0))
        for s in self.streaks:                               # voorbijrazende snelheidslijnen
            s[0] += s[3] * self.dt
            if s[0] - s[2] > W:
                s[0], s[1] = -20, random.uniform(0, H)
            pygame.draw.line(scr, (52, 66, 100), (s[0] - s[2], s[1]), (s[0], s[1]), 2)

    def draw_stage(self, rect, car, scale=1.5):
        scr = self.screen
        r = pygame.Rect(rect)
        panel(scr, r, 150, 22)
        spot = GLOW["spot"]
        scr.blit(spot, spot.get_rect(center=r.center), special_flags=pygame.BLEND_RGB_ADD)
        rot = pygame.transform.rotozoom(self.car_big(car), (self.now * 32) % 360, scale)
        scr.blit(rot, rot.get_rect(center=(r.centerx, r.centery + int(math.sin(self.now * 2) * 4))))

    # ---- hoofdmenu
    def draw_main(self):
        scr, f, ui, s = self.screen, self.f, self.ui, self.save
        self.draw_bg()
        text(scr, f["xl"], "TOP-DOWN RACER", (60, 46))
        text(scr, f["m"], "Grand Prix editie  -  race tegen tot 7 AI-bots", (64, 148), (170, 185, 215))
        items = [("SNELLE RACE", lambda: self.open_setup("race")),
                 ("GRAND PRIX", lambda: self.open_setup("gp")),
                 ("GARAGE", lambda: self.open_garage("main")),
                 ("AFSLUITEN", self.quit)]
        for i, (lab, fn) in enumerate(items):
            ui.button(scr, (60, 235 + i * 96, 430, 78), lab, fn)
        self.draw_stage((560, 150, 660, 430), s["car"])
        text(scr, f["s"], "JOUW AUTO", (590, 168), (160, 175, 200))
        lvl = LEVELS[s["level"]]
        text(scr, f["m"], f"{BODY_NAMES[s['car']['body']]}", (590, 520))
        text(scr, f["s"], f"Moeilijkheid: {lvl['name']}   -   {s['bots']} tegenstander(s)",
             (592, 552), lvl["color"])
        text(scr, f["s"], "Klik met de muis, of gebruik de toetsen 1-4   -   F11 volledig scherm",
             (60, H - 44), (150, 165, 195))

    # ---- instellingen voor een race / grand prix
    def stepper(self, x, y, key, lo, hi, label, w=300):
        scr, ui = self.screen, self.ui
        v = self.save[key]
        ui.button(scr, (x, y, 56, 56), "-", lambda: self.adjust(key, -1, lo, hi), enabled=v > lo)
        pygame.draw.rect(scr, (18, 24, 38), (x + 64, y, w - 128, 56), border_radius=14)
        pygame.draw.rect(scr, (80, 92, 120), (x + 64, y, w - 128, 56), 2, border_radius=14)
        text(scr, self.f["m"], label(v), (x + w // 2, y + 28), anchor="center", shadow=False)
        ui.button(scr, (x + w - 56, y, 56, 56), "+", lambda: self.adjust(key, 1, lo, hi), enabled=v < hi)

    def draw_setup(self):
        scr, f, ui, s = self.screen, self.f, self.ui, self.save
        gp = self.mode == "gp"
        self.draw_bg()
        text(scr, f["l"], "GRAND PRIX" if gp else "SNELLE RACE", (60, 30))
        if gp:
            text(scr, f["s"], "Punten per positie: 25-18-15-12-10-8-6-4   -   elke race een nieuw circuit",
                 (400, 52), (170, 185, 215))

        text(scr, f["s"], "MOEILIJKHEID", (60, 108), (160, 175, 200))
        for k, cfg in LEVELS.items():
            r = pygame.Rect(60, 134 + (k - 1) * 84, 410, 74)
            sel = k == s["level"]
            ui.button(scr, r, "", lambda k=k: self.set_level(k), selected=sel, accent=cfg["color"])
            pygame.draw.circle(scr, cfg["color"], (r.x + 40, r.centery), 22)
            text(scr, f["m"], str(k), (r.x + 40, r.centery), (20, 20, 24), "center", False)
            text(scr, f["m"], cfg["name"], (r.x + 80, r.y + 8), (255, 255, 255) if sel else (200, 210, 230))
            text(scr, f["s"], cfg["desc"], (r.x + 80, r.y + 44), (170, 185, 215))

        x = 500
        text(scr, f["s"], "TEGENSTANDERS", (x, 108), (160, 175, 200))
        self.stepper(x, 134, "bots", 1, MAX_BOTS, lambda v: f"{v} bot" if v == 1 else f"{v} bots")
        lkey = "laps_gp" if gp else "laps_q"
        text(scr, f["s"], "RONDES PER RACE", (x, 218), (160, 175, 200))
        self.stepper(x, 244, lkey, 1, 10, lambda v: f"{v} ronden" if v > 1 else "1 ronde")
        text(scr, f["s"], "WEER", (x, 328), (160, 175, 200))
        ui.button(scr, (x, 354, 144, 56), "Droog", lambda: self.set_weather(0), selected=s["weather"] == 0)
        ui.button(scr, (x + 156, 354, 144, 56), "Regen", lambda: self.set_weather(1), selected=s["weather"] == 1)
        if gp:
            text(scr, f["s"], "AANTAL RACES", (x, 438), (160, 175, 200))
            self.stepper(x, 464, "gp_races", 2, 8, lambda v: f"{v} races")
        else:
            text(scr, f["s"], "Regen = minder grip, maar koplampen en spetters.", (x, 450), (150, 165, 195))
        ui.button(scr, (x, 590, 300, 80), "START", self.start_session, accent=(110, 255, 140))

        ui.button(scr, (60, 614, 190, 56), "TERUG", lambda: self.goto("main"))
        ui.button(scr, (260, 614, 210, 56), "GARAGE", lambda: self.open_garage("setup"))

        # voorbeeld van het circuit
        panel(scr, (830, 108, 390, 410), 150, 22)
        text(scr, f["s"], "VOORBEELD VAN HET CIRCUIT", (850, 122), (160, 175, 200))
        scr.blit(self.mm.surf, self.mm.surf.get_rect(center=(1025, 300)))
        text(scr, f["s"], f"Lengte  {self.stats[0]:.2f} km", (852, 468))
        text(scr, f["s"], f"Bochten  {self.stats[1]}", (1060, 468))
        ui.button(scr, (830, 534, 390, 56), "NIEUW CIRCUIT", self.new_preview)
        text(scr, f["s"], "1-5 moeilijkheid  -  N nieuw circuit  -  ENTER start  -  ESC terug",
             (830, 614), (150, 165, 195))

    # ---- garage
    def set_color(self, c):
        self.save["car"]["color"] = list(c)

    def set_accent(self, c):
        self.save["car"]["accent"] = list(c)

    def set_body(self, b):
        self.save["car"]["body"] = b

    def tune(self, i, d):
        st = self.save["car"]["stats"]
        nv = st[i] + d
        if nv < 0 or nv > STAT_MAX:
            return
        if d > 0 and sum(st) >= STAT_BUDGET:
            return
        st[i] = nv

    def reset_car(self):
        self.save["car"] = json.loads(json.dumps(DEFAULTS["car"]))

    def random_car(self):
        car = self.save["car"]
        car["color"] = list(random.choice(PALETTE) if random.random() < 0.5 else hsv(random.random()))
        car["accent"] = list(random.choice(ACCENTS))
        car["body"] = random.randrange(len(BODY_NAMES))
        st = [0, 0, 0, 0]
        for _ in range(STAT_BUDGET):
            opts = [i for i in range(4) if st[i] < STAT_MAX]
            st[random.choice(opts)] += 1
        car["stats"] = st

    def draw_garage(self):
        scr, f, ui = self.screen, self.f, self.ui
        car = self.save["car"]
        self.draw_bg()
        text(scr, f["l"], "GARAGE", (60, 30))

        self.draw_stage((60, 100, 520, 420), car)
        text(scr, f["s"], BODY_NAMES[car["body"]].upper(), (82, 118), (160, 175, 200))
        ui.button(scr, (60, 536, 250, 56), "WILLEKEURIG", self.random_car)
        ui.button(scr, (330, 536, 250, 56), "RESET", self.reset_car)
        ui.button(scr, (60, 614, 260, 60), "OPSLAAN & TERUG", lambda: self.goto(self.garage_from),
                  accent=(110, 255, 140))

        x = 620
        text(scr, f["s"], "CARROSSERIE", (x, 100), (160, 175, 200))
        for i, name in enumerate(BODY_NAMES):
            ui.button(scr, (x + i * 203, 124, 193, 52), name, lambda i=i: self.set_body(i),
                      selected=car["body"] == i)

        text(scr, f["s"], "KLEUR  (kies er een, of sleep over de kleurenbalk)", (x, 192), (160, 175, 200))
        for i, c in enumerate(PALETTE):
            ui.swatch(scr, (x + i * 50, 218, 42, 42), c, list(c) == car["color"], lambda c=c: self.set_color(c))
        hue_rect = pygame.Rect(x, 272, 600, 26)
        scr.blit(self.A["hue"], hue_rect.topleft)
        pygame.draw.rect(scr, (255, 255, 255), hue_rect, 2)
        ui.hit(hue_rect, lambda: setattr(self, "hue_drag", True))
        if self.hue_drag:
            if ui.down:
                mx = clamp(ui.mouse[0] - hue_rect.x, 0, hue_rect.w - 1)
                car["color"] = list(hsv(mx / hue_rect.w))
            else:
                self.hue_drag = False

        text(scr, f["s"], "ACCENTKLEUR", (x, 316), (160, 175, 200))
        for i, c in enumerate(ACCENTS):
            ui.swatch(scr, (x + i * 50, 342, 42, 42), c, list(c) == car["accent"], lambda c=c: self.set_accent(c))

        st = car["stats"]
        left = STAT_BUDGET - sum(st)
        text(scr, f["s"], f"TUNING   -   punten over: {left}", (x, 406),
             (255, 220, 70) if left else (160, 175, 200))
        prm = car_params(st)
        effects = [f"{prm['vmax'] * 0.5:.0f} km/h", f"{(prm['accel'] / BASE_ACCEL - 1) * 100:+.0f}%",
                   f"{(prm['turn'] - 1) * 100:+.0f}%", f"{prm['nitro']:.0f}"]
        for i, name in enumerate(STAT_NAMES):
            y = 432 + i * 52
            text(scr, f["m"], name, (x, y + 4))
            ui.button(scr, (x + 196, y, 44, 44), "-", lambda i=i: self.tune(i, -1), enabled=st[i] > 0)
            for sgm in range(STAT_MAX):
                r = pygame.Rect(x + 246 + sgm * 35, y + 8, 30, 28)
                on = sgm < st[i]
                pygame.draw.rect(scr, (90, 170, 255) if on else (34, 42, 62), r, border_radius=6)
                pygame.draw.rect(scr, (255, 255, 255) if on else (80, 92, 120), r, 2, border_radius=6)
            ui.button(scr, (x + 246 + STAT_MAX * 35 + 6, y, 44, 44), "+", lambda i=i: self.tune(i, 1),
                      enabled=st[i] < STAT_MAX and left > 0)
            text(scr, f["s"], effects[i], (x + 600, y + 22), (200, 210, 230), "midright")

    # ---- race + overlays
    def draw_race(self):
        r = self.race
        r.draw(self.screen, self.A)
        if r.state == "finished":
            self.draw_results()
        if self.paused:
            self.draw_pause()

    def dim(self, a=140):
        d = pygame.Surface((W, H), pygame.SRCALPHA)
        d.fill((0, 0, 0, a))
        self.screen.blit(d, (0, 0))

    def draw_pause(self):
        scr, f, ui = self.screen, self.f, self.ui
        self.dim(160)
        panel(scr, (W // 2 - 220, 170, 440, 380), 225)
        text(scr, f["l"], "PAUZE", (W // 2, 190), anchor="midtop")
        ui.button(scr, (W // 2 - 190, 280, 380, 64), "HERVATTEN", lambda: setattr(self, "paused", False),
                  accent=(110, 255, 140))
        ui.button(scr, (W // 2 - 190, 358, 380, 64), "OPNIEUW", lambda: self.begin_race("same"))
        ui.button(scr, (W // 2 - 190, 436, 380, 64), "STOP GRAND PRIX" if self.gp else "NAAR MENU",
                  self.leave_race)

    def draw_results(self):
        scr, f, ui, r = self.screen, self.f, self.ui, self.race
        gp = self.mode == "gp"
        self.dim(140)
        order = r.ranking()
        p = r.player
        rank = order.index(p) + 1
        panel(scr, (W // 2 - 340, 60, 680, 610), 228)
        title = "GEWONNEN!" if rank == 1 else (f"PODIUM  -  P{rank}" if rank <= 3 else f"P{rank}")
        col = (255, 220, 70) if rank == 1 else ((215, 220, 230) if rank <= 3 else (255, 150, 130))
        text(scr, f["xl"] if rank == 1 else f["l"], title, (W // 2, 78 if rank == 1 else 98), col, "midtop")
        cx = W // 2
        for i, c in enumerate(order):
            y = 196 + i * 36
            if c.is_player:
                hl = pygame.Surface((640, 34), pygame.SRCALPHA)
                pygame.draw.rect(hl, (255, 220, 70, 40), hl.get_rect(), border_radius=8)
                scr.blit(hl, (cx - 320, y - 3))
            text(scr, f["s"], f"{i + 1}.", (cx - 300, y + 3), (200, 210, 230))
            pygame.draw.circle(scr, (255, 255, 255), (cx - 252, y + 14), 9)
            pygame.draw.circle(scr, c.color, (cx - 252, y + 14), 7)
            text(scr, f["m"], c.name, (cx - 232, y - 2), (255, 220, 70) if c.is_player else (255, 255, 255))
            if gp:
                pts = POINTS[i] if i < len(POINTS) else 0
                text(scr, f["s"], f"+{pts} pt", (cx + 130, y + 3), (255, 220, 70), "topright")
            if c.finished:
                t = fmt(c.finish_time) if i == 0 else f"+{c.finish_time - order[0].finish_time:.1f}s"
                text(scr, f["s"], t, (cx + 310, y + 3), (230, 235, 245), "topright")
            else:
                text(scr, f["s"], f"rijdt nog  ({min(c.laps + 1, r.laps)}/{r.laps})", (cx + 310, y + 3),
                     (150, 165, 195), "topright")
        best = min(p.lap_times) if p.lap_times else None
        text(scr, f["s"], f"Jouw tijd  {fmt(p.finish_time)}      Beste ronde  {fmt(best)}",
             (cx, 196 + len(order) * 36 + 12), (200, 210, 230), "midtop")
        if gp:
            ui.button(scr, (cx - 160, 590, 320, 64), "VERDER", self.results_continue, accent=(110, 255, 140))
        else:
            ui.button(scr, (cx - 320, 590, 310, 64), "OPNIEUW", lambda: self.begin_race("same"),
                      accent=(110, 255, 140))
            ui.button(scr, (cx + 10, 590, 310, 64), "MENU", self.leave_race)
        r.confetti.draw(scr)

    # ---- Grand Prix schermen
    def draw_table(self, x, y, w, rows, title, key_pts=True, bar_max=None):
        """rows: lijst van (naam, kleur, getal-tekst, getal-voor-balk)."""
        scr, f = self.screen, self.f
        panel(scr, (x, y, w, 60 + len(rows) * 46 + 14), 170, 20)
        text(scr, f["s"], title, (x + 22, y + 18), (160, 175, 200))
        for i, (name, col, label, val) in enumerate(rows):
            yy = y + 50 + i * 46
            me = name == "Jij"
            if me:
                hl = pygame.Surface((w - 24, 40), pygame.SRCALPHA)
                pygame.draw.rect(hl, (255, 220, 70, 40), hl.get_rect(), border_radius=8)
                scr.blit(hl, (x + 12, yy - 2))
            text(scr, f["m"], f"{i + 1}.", (x + 24, yy + 2), (200, 210, 230))
            pygame.draw.circle(scr, (255, 255, 255), (x + 86, yy + 18), 11)
            pygame.draw.circle(scr, col, (x + 86, yy + 18), 9)
            text(scr, f["m"], name, (x + 108, yy + 2), (255, 220, 70) if me else (255, 255, 255))
            if bar_max:
                bw = int((w - 330) * val / bar_max)
                if bw > 0:
                    pygame.draw.rect(scr, col, (x + 250, yy + 10, bw, 16), border_radius=8)
            text(scr, f["m"], label, (x + w - 24, yy + 2), (255, 255, 255), "topright")

    def draw_gp_standings(self):
        scr, f, ui, gp = self.screen, self.f, self.ui, self.gp
        self.draw_bg()
        text(scr, f["l"], f"GRAND PRIX  -  RACE {gp['done']} VAN {gp['total']} KLAAR", (60, 28))
        last = [(n, c, f"+{p}", p) for n, c, p in gp["last"]]
        self.draw_table(60, 110, 540, last, "UITSLAG VAN DEZE RACE")
        tot = sorted(gp["points"].items(), key=lambda kv: -kv[1])
        top = max(1, tot[0][1])
        rows = [(n, gp["colors"][n], f"{p}", p) for n, p in tot]
        self.draw_table(640, 110, 580, rows, "KAMPIOENSCHAP", bar_max=top)
        ui.button(scr, (W // 2 - 190, 622, 380, 68), "VOLGENDE RACE", self.next_gp_race, accent=(110, 255, 140))
        ui.button(scr, (60, 634, 200, 56), "STOPPEN", self.leave_race)

    def draw_gp_final(self):
        scr, f, ui, gp = self.screen, self.f, self.ui, self.gp
        self.draw_bg()
        tot = sorted(gp["points"].items(), key=lambda kv: -kv[1])
        champ = tot[0][0]
        text(scr, f["l"], "EINDSTAND GRAND PRIX", (60, 28))
        text(scr, f["m"], "Jij bent kampioen!" if champ == "Jij" else f"Kampioen: {champ}", (64, 90),
             (255, 220, 70) if champ == "Jij" else (200, 210, 230))

        # podium
        slots = [(1, 190, 440, (215, 220, 230)), (0, 350, 390, (255, 220, 70)), (2, 510, 485, (225, 150, 90))]
        for idx, cxp, top, col in slots:
            if idx >= len(tot):
                continue
            name, pts = tot[idx]
            pygame.draw.rect(scr, (30, 38, 58), (cxp - 70, top, 140, 640 - top), border_radius=10)
            pygame.draw.rect(scr, col, (cxp - 70, top, 140, 640 - top), 3, border_radius=10)
            text(scr, f["xl"], str(idx + 1), (cxp, top + 8), col, "midtop")
            text(scr, f["s"], f"{pts} punten", (cxp, top + 104), (230, 235, 245), "midtop")
            look = self.look_of(name)
            spr = pygame.transform.rotate(pygame.transform.smoothscale(self.car_big(look), (110, 55)), 90)
            scr.blit(spr, spr.get_rect(midbottom=(cxp, top - 30)))
            text(scr, f["m"], name, (cxp, top - 26), (255, 220, 70) if name == "Jij" else (255, 255, 255), "midtop")

        rows = [(n, gp["colors"][n], f"{p}", p) for n, p in tot]
        self.draw_table(720, 100, 500, rows, "KAMPIOENSCHAP", bar_max=max(1, tot[0][1]))
        ui.button(scr, (720, 634, 240, 58), "MENU", self.leave_race)
        ui.button(scr, (980, 634, 240, 58), "NIEUWE GP", self.new_gp, accent=(110, 255, 140))
        self.confetti.draw(scr)

    def look_of(self, name):
        if name == "Jij":
            return self.save["car"]
        for f in self.field:
            if f["name"] == name:
                return dict(color=f["color"], accent=f["accent"], body=f["body"])
        return self.save["car"]


def main():
    App().run()


if __name__ == "__main__":
    main()
