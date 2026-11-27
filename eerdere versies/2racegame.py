"""
TOP-DOWN RACER  -  singleplayer tegen een AI-bot
================================================
Elk circuit wordt willekeurig gegenereerd. Hoe hoger de moeilijkheid,
hoe meer en scherpere bochten, en hoe sneller/slimmer de bot.

Installeren:   py -m pip install pygame-ce
Starten:       py racegame.py

Besturing
    Pijltje omhoog / W      gas
    Pijltje omlaag / S      remmen / achteruit
    Links / rechts / A / D  sturen
    SPATIE                  handrem (driften)
    T                       terugzetten op het circuit
    R                       race opnieuw   M / ESC   menu
    F11                     volledig scherm
"""
import math
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
LAPS = 5

TURN_RATE = 3.3         # stuursnelheid (rad/s)
TURN_LOSS = 0.38        # minder wendbaar bij hoge snelheid
PLAYER_VMAX = 560
ACCEL = 430
BRAKE = 720

LEVELS = {
    1: dict(name="Makkelijk", desc="Brede, rustige bochten", K=5, A0=0.30, R=850,
            min_r=260, ai_vmax=450, ai_corner=0.80, color=(90, 210, 120)),
    2: dict(name="Normaal", desc="Veel bochten, wisselende ritmes", K=7, A0=0.34, R=1050,
            min_r=200, ai_vmax=510, ai_corner=0.88, color=(255, 200, 70)),
    3: dict(name="Moeilijk", desc="Extreem veel scherpe bochten", K=11, A0=0.36, R=1250,
            min_r=150, ai_vmax=545, ai_corner=0.93, color=(255, 90, 80)),
}


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


# ------------------------------------------------------------------ auto
def make_car_sprite(color):
    big = pygame.Surface((240, 120), pygame.SRCALPHA)
    dark = (24, 24, 28)
    shade = tuple(int(c * 0.72) for c in color)
    light = tuple(min(255, int(c * 1.2) + 25) for c in color)
    for rect in [(30, 4, 56, 26), (30, 90, 56, 26), (158, 6, 46, 22), (158, 92, 46, 22)]:
        pygame.draw.rect(big, dark, rect, border_radius=8)
    pygame.draw.rect(big, dark, (6, 20, 20, 80), border_radius=4)           # achtervleugel
    pygame.draw.rect(big, color, (6, 16, 20, 8))
    pygame.draw.rect(big, color, (6, 96, 20, 8))
    body = [(22, 34), (120, 28), (176, 38), (228, 54), (228, 66), (176, 82), (120, 92), (22, 86)]
    pygame.draw.polygon(big, color, body)
    pygame.draw.polygon(big, shade, [(22, 62), (228, 62), (228, 66), (176, 82), (120, 92), (22, 86)])
    pygame.draw.polygon(big, light, [(30, 37), (120, 32), (172, 41), (220, 54), (120, 46), (30, 47)])
    pygame.draw.polygon(big, (245, 245, 245), [(50, 57), (228, 57), (228, 63), (50, 63)])
    pygame.draw.rect(big, dark, (222, 22, 10, 76), border_radius=3)         # voorvleugel
    pygame.draw.rect(big, color, (222, 18, 10, 8))
    pygame.draw.rect(big, color, (222, 94, 10, 8))
    pygame.draw.ellipse(big, (24, 30, 46), (92, 42, 64, 36))                # cockpit
    pygame.draw.ellipse(big, (80, 105, 140), (100, 46, 30, 12))
    pygame.draw.circle(big, (250, 250, 250), (122, 60), 11)                 # helm
    pygame.draw.circle(big, light, (122, 60), 5)
    return pygame.transform.smoothscale(big, (60, 30))


class Car:
    def __init__(self, track, idx, offset, color, vmax, name):
        p = track.pts[idx]
        nx, ny = track.normals[idx]
        self.x, self.y = p[0] + nx * offset, p[1] + ny * offset
        self.heading = track.headings[idx]
        self.vx = self.vy = 0.0
        self.vmax = vmax
        self.accel = ACCEL
        self.name = name
        self.color = color
        self.idx = idx
        self.progress = idx - track.n          # negatief: nog voor de startlijn
        self.laps = 0
        self.lap_times = []
        self.last_lap_t = 0.0
        self.finished = False
        self.finish_time = None
        self.slip = 0.0
        self.on_road = True
        self.sprite = make_car_sprite(color)
        self.shadow = pygame.mask.from_surface(self.sprite).to_surface(
            setcolor=(0, 0, 0, 95), unsetcolor=(0, 0, 0, 0))

    @property
    def forward_speed(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    def physics(self, track, dt, throttle, brake, steer, hand=False):
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        vf = self.vx * fx + self.vy * fy
        grip_turn = clamp(vf / 140, -1, 1)
        turn = TURN_RATE * (1 - TURN_LOSS * min(1, abs(vf) / self.vmax))
        self.heading += steer * turn * grip_turn * dt * (1.25 if hand else 1.0)

        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        vf = self.vx * fx + self.vy * fy
        vl = self.vx * rx + self.vy * ry

        on = track.on_road(self.x, self.y)
        acc = self.accel * (1.0 if on else 0.55)
        if throttle:
            vf += acc * dt
        if brake:
            if vf > 20:
                vf -= BRAKE * dt
            else:
                vf -= acc * 0.5 * dt
        drag = self.accel / self.vmax + (0 if on else 1.6)
        vf -= vf * drag * dt
        if not throttle and not brake:
            vf -= math.copysign(min(abs(vf), 90 * dt), vf)
        if hand:
            vf -= vf * 0.7 * dt
        vf = max(vf, -self.vmax * 0.3)
        grip = 12.0 if on else 6.0
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
        ang = -math.degrees(self.heading)
        sh = pygame.transform.rotozoom(self.shadow, ang, 1)
        screen.blit(sh, sh.get_rect(center=(self.x - cx + 7, self.y - cy + 9)))
        sp = pygame.transform.rotozoom(self.sprite, ang, 1)
        screen.blit(sp, sp.get_rect(center=(self.x - cx, self.y - cy)))


def collide(a, b):
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy) or 0.001
    if d < 40:
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


# ------------------------------------------------------------------ AI-bot
class AIDriver:
    def __init__(self, car, track, cfg):
        self.car, self.track = car, track
        self.line_off = random.uniform(-20, 20)
        self.stuck = 0.0
        vmax = car.vmax
        n = track.n
        allowed = []
        for i in range(n):
            R = 1 / max(track.kappa[i], 1 / 3000)
            v = TURN_RATE * R / (1 + TURN_RATE * TURN_LOSS * R / vmax)
            allowed.append(min(vmax, v * cfg["ai_corner"]))
        decel = BRAKE * 0.65
        for _ in range(3):                           # tijdig afremmen voor bochten
            for i in reversed(range(n)):
                j = (i + 1) % n
                allowed[i] = min(allowed[i], math.sqrt(allowed[j] ** 2 + 2 * decel * DS))
        self.allowed = allowed

    def control(self):
        c, t = self.car, self.track
        vf = c.forward_speed
        look = int((75 + abs(vf) * 0.22) / DS) + 1
        j = (c.idx + look) % t.n
        tx = t.pts[j][0] + t.normals[j][0] * self.line_off
        ty = t.pts[j][1] + t.normals[j][1] * self.line_off
        diff = wrap_rad(math.atan2(ty - c.y, tx - c.x) - c.heading)
        steer = clamp(diff * 2.6, -1, 1)
        target = self.allowed[(c.idx + 2) % t.n]
        if not c.on_road:
            target *= 0.8
        throttle = vf < target
        brake = vf > target * 1.06
        if abs(diff) > 1.0:
            throttle, brake = vf < 120, False
        return throttle, brake, steer


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


# ------------------------------------------------------------------ UI-helpers
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


# ------------------------------------------------------------------ race
class Race:
    def __init__(self, raw, level):
        self.level = level
        cfg = self.cfg = LEVELS[level]
        self.track = Track(raw)
        self.track.render()
        t = self.track
        self.player = Car(t, t.n - 6, -30, (225, 40, 40), PLAYER_VMAX, "Jij")
        self.ai_car = Car(t, t.n - 11, 30, (50, 120, 235), cfg["ai_vmax"], "AI")
        self.ai = AIDriver(self.ai_car, t, cfg)
        self.minimap = MiniMap(t.pts, 240, 200)
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        self.mark = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(self.mark, (10, 10, 12, 70), (3, 3), 3)
        self.particles = []
        self.state = "countdown"
        self.countdown = 3.0
        self.go_t = 0.0
        self.time = 0.0
        self.cam_x = clamp(self.player.x - W / 2, 0, t.w - W)
        self.cam_y = clamp(self.player.y - H / 2, 0, t.h - H)
        self.dial = make_dial(200)
        self.player_won = None

    # ---- logica
    def update(self, dt, keys):
        dt = min(dt, 0.05)
        t, p, a = self.track, self.player, self.ai_car
        if self.state == "countdown":
            self.countdown -= dt
            if self.countdown <= 0:
                self.state, self.go_t = "race", 1.2
        elif self.state == "race":
            self.time += dt
            self.go_t = max(0, self.go_t - dt)
            thr = keys[pygame.K_UP] or keys[pygame.K_w]
            brk = keys[pygame.K_DOWN] or keys[pygame.K_s]
            steer = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            hand = keys[pygame.K_SPACE]
            p.physics(t, dt, thr, brk, steer, hand)
            a.physics(t, dt, *self.ai.control())
            collide(p, a)
            for c in (p, a):
                c.update_progress(t)
                laps = max(0, int(c.progress // t.n))
                if laps > c.laps:
                    c.laps = laps
                    c.lap_times.append(self.time - c.last_lap_t)
                    c.last_lap_t = self.time
                if c.laps >= LAPS and not c.finished:
                    c.finished, c.finish_time = True, self.time
            self._effects(p, dt, hand)
            self._effects(a, dt, False)
            # AI vast? terugzetten
            if math.hypot(a.vx, a.vy) < 35:
                self.ai.stuck += dt
                if self.ai.stuck > 2.0:
                    a.respawn(t)
                    self.ai.stuck = 0
            else:
                self.ai.stuck = 0
            if p.finished:
                self.state = "finished"
                self.player_won = not a.finished

        # deeltjes
        for q in self.particles:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] += dt
        self.particles = [q for q in self.particles if q[4] < q[5]][-320:]

        # camera
        tx = p.x + p.vx * 0.28 - W / 2
        ty = p.y + p.vy * 0.28 - H / 2
        k = min(1, dt * 5)
        self.cam_x = clamp(self.cam_x + (tx - self.cam_x) * k, 0, t.w - W)
        self.cam_y = clamp(self.cam_y + (ty - self.cam_y) * k, 0, t.h - H)

    def _effects(self, car, dt, hand):
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
                    self.particles.append([wx, wy, random.uniform(-25, 25), random.uniform(-25, 25),
                                           0, random.uniform(0.5, 0.9), random.uniform(5, 9),
                                           (225, 225, 230)])
        if not car.on_road and speed > 90:                      # stof/gras
            for wx, wy in wheels:
                if random.random() < 0.6:
                    self.particles.append([wx, wy, random.uniform(-40, 40), random.uniform(-40, 40),
                                           0, random.uniform(0.4, 0.8), random.uniform(5, 10),
                                           (150, 130, 90)])

    # ---- tekenen
    def draw(self, screen, A):
        cx, cy = int(self.cam_x), int(self.cam_y)
        screen.blit(self.track.world, (0, 0), pygame.Rect(cx, cy, W, H))

        self.fx.fill((0, 0, 0, 0))
        for x, y, _, _, age, life, size, col in self.particles:
            u = age / life
            pygame.draw.circle(self.fx, (*col, int(150 * (1 - u))),
                               (int(x - cx), int(y - cy)), int(size * (1 + u * 1.6)))
        screen.blit(self.fx, (0, 0))

        self.ai_car.draw(screen, cx, cy)
        self.player.draw(screen, cx, cy)
        screen.blit(A["vignette"], (0, 0))
        self._hud(screen, A)

    def _hud(self, screen, A):
        f = A["fonts"]
        p, a = self.player, self.ai_car

        # links boven: ronde / tijd
        panel(screen, (20, 20, 270, 118))
        text(screen, f["s"], "RONDE", (38, 30), (160, 175, 200))
        text(screen, f["l"], f"{min(p.laps + 1, LAPS)}/{LAPS}", (38, 46))
        text(screen, f["s"], "TIJD", (170, 30), (160, 175, 200))
        text(screen, f["m"], fmt(self.time), (170, 48))
        best = min(p.lap_times) if p.lap_times else None
        text(screen, f["s"], f"BESTE RONDE  {fmt(best)}", (38, 104), (200, 210, 230))

        # midden boven: positie
        ahead = p.progress >= a.progress
        gap = abs(p.progress - a.progress) * DS / 10
        panel(screen, (W // 2 - 85, 20, 170, 96))
        text(screen, f["s"], "POSITIE", (W // 2, 28), (160, 175, 200), "midtop")
        text(screen, f["l"], "1" if ahead else "2", (W // 2 - 14, 76),
             (255, 220, 70) if ahead else (255, 255, 255), "midright")
        text(screen, f["m"], "/2", (W // 2 - 8, 80), (190, 200, 220), "midleft")
        gcol = (110, 235, 140) if ahead else (255, 120, 110)
        text(screen, f["s"], f"{'+' if ahead else '-'}{gap:.0f} m", (W // 2, 100), gcol, "midtop")

        # rechts boven: minimap
        mm = self.minimap
        mx, my = W - 20 - mm.w, 20
        screen.blit(mm.surf, (mx, my))
        for car, col, r in ((a, (70, 140, 255), 6), (p, (255, 60, 60), 7)):
            qx, qy = mm.to_map(car.x, car.y)
            pygame.draw.circle(screen, (255, 255, 255), (int(mx + qx), int(my + qy)), r + 2)
            pygame.draw.circle(screen, col, (int(mx + qx), int(my + qy)), r)

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

        # waarschuwingen
        if self.state == "race":
            t = self.track
            tvx, tvy = math.cos(t.headings[p.idx]), math.sin(t.headings[p.idx])
            if p.vx * tvx + p.vy * tvy < -60 and pygame.time.get_ticks() // 350 % 2 == 0:
                text(screen, f["l"], "VERKEERDE RICHTING!", (W // 2, 170), (255, 80, 70), "midtop")
            elif not p.on_road and pygame.time.get_ticks() // 400 % 2 == 0:
                text(screen, f["m"], "BUITEN HET CIRCUIT", (W // 2, 160), (255, 200, 80), "midtop")
            if self.time < 9:
                panel(screen, (20, H - 70, 470, 48), 120)
                text(screen, f["s"], "Pijltjes/WASD rijden  -  SPATIE handrem  -  T terugzetten",
                     (36, H - 56), (210, 220, 240))

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

        # resultaat
        if self.state == "finished":
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            screen.blit(dim, (0, 0))
            panel(screen, (W // 2 - 270, 190, 540, 320), 215)
            win = self.player_won
            text(screen, f["xl"], "GEWONNEN!" if win else "VERLOREN", (W // 2, 210),
                 (255, 220, 70) if win else (255, 110, 100), "midtop")
            text(screen, f["m"], f"Jouw tijd:   {fmt(p.finish_time)}", (W // 2, 330), anchor="midtop")
            text(screen, f["m"], f"Beste ronde: {fmt(min(p.lap_times) if p.lap_times else None)}",
                 (W // 2, 368), anchor="midtop")
            ai_t = fmt(a.finish_time) if a.finished else "nog bezig"
            text(screen, f["m"], f"AI:  {ai_t}", (W // 2, 406), (170, 200, 255), "midtop")
            text(screen, f["s"], "ENTER / R = opnieuw   -   M = menu", (W // 2, 460),
                 (190, 200, 220), "midtop")


# ------------------------------------------------------------------ menu
def draw_menu(screen, A, level, mm, stats, now):
    f = A["fonts"]
    screen.blit(A["menu_bg"], (0, 0))
    text(screen, f["xl"], "TOP-DOWN RACER", (60, 40))
    text(screen, f["m"], "Singleplayer  -  race tegen de AI op een willekeurig circuit", (64, 142),
         (170, 185, 215))
    for k, cfg in LEVELS.items():
        r = pygame.Rect(60, 210 + (k - 1) * 112, 470, 96)
        sel = k == level
        panel(screen, r, 210 if sel else 120, 18, border=False)
        pygame.draw.rect(screen, cfg["color"] if sel else (70, 80, 100), r, 3 if sel else 2, border_radius=18)
        pygame.draw.circle(screen, cfg["color"], (r.x + 48, r.centery), 26)
        text(screen, f["l"], str(k), (r.x + 48, r.centery), (20, 20, 24), "center", False)
        text(screen, f["m"], cfg["name"], (r.x + 96, r.y + 16), (255, 255, 255) if sel else (190, 200, 220))
        text(screen, f["s"], cfg["desc"], (r.x + 96, r.y + 54), (170, 185, 215))
    # voorbeeld van het circuit
    panel(screen, (570, 130, 650, 470), 150, 22)
    screen.blit(mm.surf, mm.surf.get_rect(center=(895, 335)))
    text(screen, f["s"], "VOORBEELD VAN HET CIRCUIT", (595, 146), (160, 175, 200))
    text(screen, f["m"], f"Lengte  {stats[0]:.2f} km", (600, 548))
    text(screen, f["m"], f"Bochten  {stats[1]}", (900, 548))
    pulse = 190 + int(65 * math.sin(now * 4))
    text(screen, f["m"], "ENTER = start", (60, 570), (pulse, pulse, 215))
    text(screen, f["s"], "1/2/3 moeilijkheid   -   N nieuw circuit   -   F11 volledig scherm   -   ESC stoppen",
         (60, H - 50), (150, 165, 195))


def make_assets():
    def font(sz, bold=True):
        return pygame.font.SysFont("segoeui,arial,helvetica", sz, bold=bold)
    return {
        "fonts": {"s": font(18), "m": font(28), "l": font(46), "xl": font(84)},
        "vignette": make_vignette(),
        "menu_bg": make_menu_bg(),
    }


def show_loading(screen, A, msg):
    screen.blit(A["menu_bg"], (0, 0))
    text(screen, A["fonts"]["l"], msg, (W // 2, H // 2), anchor="center")
    pygame.display.flip()
    pygame.event.pump()


# ------------------------------------------------------------------ main
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED)
    pygame.display.set_caption("Top-down Racer vs AI")
    clock = pygame.time.Clock()
    A = make_assets()

    level = 2
    state = "menu"
    race = None
    raw = mm = stats = None

    def new_preview():
        nonlocal raw, mm, stats
        raw = generate_centerline(level)
        mm = MiniMap(raw, 600, 400, pad=30, line=9)
        stats = (len(raw) * DS / 10000, count_bends(raw))          # 10 px = 1 m

    def start_race():
        nonlocal race, state
        show_loading(screen, A, "Circuit wordt gebouwd...")
        race = Race(raw, level)
        state = "race"

    new_preview()

    while True:
        dt = clock.tick(FPS) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            if state == "menu":
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    level = e.key - pygame.K_0
                    new_preview()
                elif e.key == pygame.K_n:
                    new_preview()
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    start_race()
            else:
                if e.key in (pygame.K_ESCAPE, pygame.K_m):
                    state, race = "menu", None
                elif e.key == pygame.K_r or (e.key == pygame.K_RETURN and race.state == "finished"):
                    start_race()
                elif e.key == pygame.K_t and race.state == "race":
                    race.player.respawn(race.track)

        if state == "menu":
            draw_menu(screen, A, level, mm, stats, pygame.time.get_ticks() / 1000)
        else:
            race.update(dt, pygame.key.get_pressed())
            race.draw(screen, A)
        pygame.display.flip()


if __name__ == "__main__":
    main()
