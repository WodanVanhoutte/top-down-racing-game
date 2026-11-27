"""
td_core.py  -  gedeelde basis voor TOKYO DRIFT
Instellingen, hulpfuncties, lettertypes (met Japanse tekens), gloed-effecten,
auto-afbeeldingen, zelf gesynthetiseerd geluid + muziek en het bewaarbestand.
"""
import json
import math
import os
import random
from array import array

import pygame

# ------------------------------------------------------------------ instellingen
W, H = 1280, 720
FPS = 60
TAU = math.pi * 2
DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(DIR, "tokyo_jp.otf")        # Noto Sans CJK JP (Japanse tekens)
SHEET_FILE = os.path.join(DIR, "cars_sheet.png")
SAVE_FILE = os.path.join(DIR, "tokyo_drift_save.json")

# neonkleuren
PINK, CYAN, PURPLE, ORANGE = (255, 60, 160), (60, 230, 255), (200, 70, 255), (255, 150, 40)
GREEN, RED, YELLOW, WHITE = (90, 255, 150), (255, 70, 70), (255, 230, 80), (235, 235, 255)
NEON = [PINK, CYAN, PURPLE, ORANGE, GREEN, RED, YELLOW, WHITE]
NEON_NAMES = ["ピンク PINK", "シアン CYAN", "紫 PURPLE", "橙 ORANGE", "緑 GREEN", "赤 RED", "黄 YELLOW", "白 WHITE"]

# de auto's uit cars_sheet.png die je kan kiezen: (sheet-index, Japanse naam, naam, [top, accel, drift, nitro])
CARS = [
    (26, "ハチロク", "HACHIROKU", [5, 6, 9, 5]),
    (13, "雷", "KAMINARI", [6, 7, 7, 5]),
    (29, "忍者", "NINJA", [7, 6, 6, 6]),
    (7, "侍", "SAMURAI", [8, 6, 5, 6]),
    (33, "鬼", "ONI", [7, 8, 6, 7]),
    (15, "龍", "RYU", [6, 5, 8, 8]),
    (31, "桜", "SAKURA", [8, 7, 7, 4]),
    (16, "将軍", "SHOGUN", [9, 8, 4, 7]),
    (0, "彗星", "SUISEI", [9, 9, 5, 5]),
    (22, "波", "NAMI", [5, 8, 8, 7]),
]
STAT_NAMES = [("最高速", "TOPSNELHEID"), ("加速", "ACCELERATIE"), ("ドリフト", "DRIFT"), ("ニトロ", "NITRO")]
SHEET_COLS, CELL_W, CELL_H = 10, 208, 112
BOT_NAMES = ["TAKUMI", "KEISUKE", "RYOSUKE", "MAKO", "KENJI", "AKIRA", "REI", "HIRO"]

DEFAULTS = dict(car=0, glow=1, laps=3, bots=3, weather=0, volume=7, music=1, scan=1, course=0,
                best={})          # best["<mode>-<course>"] = score of tijd


# ------------------------------------------------------------------ hulpfuncties
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def dim(c, k):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


def wrap_rad(a):
    return (a + math.pi) % TAU - math.pi


def fmt_time(t):
    if t is None:
        return "--:--.--"
    return f"{int(t // 60)}:{t % 60:05.2f}"


def fmt_pts(p):
    return f"{int(p):,}".replace(",", ".")


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            got = json.load(f)
        for k in data:
            if k in got and type(got[k]) is type(data[k]):
                data[k] = got[k]
    except Exception:
        pass
    data["car"] = int(clamp(data["car"], 0, len(CARS) - 1))
    data["glow"] = int(clamp(data["glow"], 0, len(NEON) - 1))
    data["laps"] = int(clamp(data["laps"], 1, 9))
    data["bots"] = int(clamp(data["bots"], 1, 5))
    data["volume"] = int(clamp(data["volume"], 0, 10))
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


# ------------------------------------------------------------------ tekst
_FONTS = {}
_TEXT = {}
HAS_JP = os.path.exists(FONT_FILE)
JP_SYSFONTS = ("yugothicui,yugothic,meiryoui,meiryo,msgothic,hiraginosans,notosanscjkjp,"
               "notosansjp,takaoexgothic,ipagothic,vlgothic")


def font(size, bold=False, italic=False):
    """Lettertype met Japanse tekens. Vet/cursief wordt door pygame nagebootst."""
    global HAS_JP
    key = (size, bold, italic)
    if key not in _FONTS:
        f = None
        if os.path.exists(FONT_FILE):
            try:
                f = pygame.font.Font(FONT_FILE, size)
            except Exception:
                f = None
        if f is None:
            path = pygame.font.match_font(JP_SYSFONTS)
            HAS_JP = bool(path)
            f = pygame.font.Font(path, size) if path else pygame.font.SysFont("arial", size)
        f.set_bold(bold)
        f.set_italic(italic)
        _FONTS[key] = f
    return _FONTS[key]


def J(jp, lat):
    """Japanse tekst, of de reserve-tekst als er geen Japans lettertype is."""
    return jp if HAS_JP else lat


def JB(jp, lat):
    """Japans + Nederlands naast elkaar (of alleen Nederlands zonder Japans lettertype)."""
    return f"{jp}  {lat}" if HAS_JP else lat


def render(s, size, color=(255, 255, 255), bold=False, italic=False):
    """Tekst als afbeelding (met cache, want tekst tekenen is traag)."""
    key = (s, size, color, bold, italic)
    img = _TEXT.get(key)
    if img is None:
        if len(_TEXT) > 900:
            _TEXT.clear()
        img = font(size, bold, italic).render(s, True, color)
        _TEXT[key] = img
    return img


def text(surf, s, size, pos, color=(255, 255, 255), anchor="topleft", bold=False, italic=False,
         shadow=(0, 0, 0), off=2):
    img = render(s, size, color, bold, italic)
    rect = img.get_rect(**{anchor: pos})
    if shadow is not None:
        surf.blit(render(s, size, shadow, bold, italic), rect.move(off, off))
    surf.blit(img, rect)
    return rect


def vtext(s, size, color, bold=False):
    """Verticale tekst (teken per teken onder elkaar), zoals op Japanse uithangborden."""
    imgs = [font(size, bold).render(ch, True, color) for ch in s]
    w = max(i.get_width() for i in imgs)
    step = int(size * 1.04)
    out = pygame.Surface((w, step * len(imgs) + 4), pygame.SRCALPHA)
    for k, im in enumerate(imgs):
        out.blit(im, (w // 2 - im.get_width() // 2, k * step))
    return out


_CHROME = {}


def chrome(s, size, top=(255, 255, 255), mid=(120, 190, 255), low=(20, 40, 140), edge=(255, 250, 200),
           outline=(10, 0, 40), o=3, italic=True):
    """90s arcade-tekst: chroom kleurverloop met een 'horizon' in het midden en een dikke rand."""
    key = (s, size, top, mid, low, edge, outline, o, italic)
    if key in _CHROME:
        return _CHROME[key]
    f = font(size, True, italic)
    white = f.render(s, True, (255, 255, 255))
    w, h = white.get_size()
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    hz = int(h * 0.56)
    for y in range(h):
        if y < hz:
            c = mix(top, mid, y / max(1, hz))
        else:
            c = mix(low, edge, ((y - hz) / max(1, h - hz)) ** 1.5)
        pygame.draw.line(grad, (*c, 255), (0, y), (w, y))
    white.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out = pygame.Surface((w + 2 * o + 6, h + 2 * o + 6), pygame.SRCALPHA)
    dark = f.render(s, True, (0, 0, 0))
    dark.set_alpha(150)
    out.blit(dark, (o + 6, o + 6))
    ol = f.render(s, True, outline)
    for dx in range(-o, o + 1):
        for dy in range(-o, o + 1):
            if dx * dx + dy * dy <= o * o + 1:
                out.blit(ol, (o + dx, o + dy))
    out.blit(white, (o, o))
    if len(_CHROME) > 300:
        _CHROME.clear()
    _CHROME[key] = out
    return out


def panel(surf, rect, tint=(8, 6, 24), alpha=190, edge=CYAN, w=2):
    r = pygame.Rect(rect)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    s.fill((*tint, alpha))
    surf.blit(s, r.topleft)
    if edge:
        pygame.draw.rect(surf, edge, r, w)
        pygame.draw.rect(surf, dim(edge, 0.35), r.inflate(6, 6), 1)


# ------------------------------------------------------------------ gloed
_GLOW = {}


def glow(size, color, power=2.0):
    """Zachte ronde gloed op zwart. Teken hem met special_flags=pygame.BLEND_RGB_ADD."""
    key = (size, color, power)
    g = _GLOW.get(key)
    if g is None:
        g = pygame.Surface((size, size))
        R = size / 2
        for r in range(int(R), 0, -1):
            v = (1 - r / R) ** power
            pygame.draw.circle(g, (int(color[0] * v), int(color[1] * v), int(color[2] * v)), (size // 2, size // 2), r)
        _GLOW[key] = g
    return g


def add_glow(surf, x, y, size, color, power=2.0):
    surf.blit(glow(size, color, power), (int(x - size / 2), int(y - size / 2)), special_flags=pygame.BLEND_RGB_ADD)


def make_cone(L=190):
    """Koplampbundel, wijst naar rechts vanuit het midden van de afbeelding."""
    s = pygame.Surface((L * 2, L * 2))
    for k in range(26, 0, -1):
        t = k / 26
        v = (1 - t) ** 1.6 * 0.5
        hw = 0.50 * t + 0.05
        pts = [(L + 14, L), (L + L * t, L - L * t * hw), (L + L * t * 1.04, L), (L + L * t, L + L * t * hw)]
        pygame.draw.polygon(s, (int(255 * v), int(240 * v), int(200 * v)), pts)
    return s


def make_vignette():
    small = pygame.Surface((160, 90), pygame.SRCALPHA)
    for y in range(90):
        for x in range(160):
            d = math.hypot((x - 80) / 80, (y - 45) / 45)
            a = int(150 * clamp((d - 0.55) / 0.75, 0, 1) ** 2)
            small.set_at((x, y), (0, 0, 8, a))
    return pygame.transform.smoothscale(small, (W, H))


def make_edge_glow(color):
    """Gekleurde schermrand (additief), bv. blauw tijdens nitro."""
    small = pygame.Surface((160, 90))
    for y in range(90):
        for x in range(160):
            d = math.hypot((x - 80) / 80, (y - 45) / 45)
            v = clamp((d - 0.62) / 0.7, 0, 1) ** 1.6
            small.set_at((x, y), dim(color, v))
    return pygame.transform.smoothscale(small, (W, H))


def make_scanlines():
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 3):
        pygame.draw.line(s, (0, 0, 0, 58), (0, y), (W, y))
    return s


# ------------------------------------------------------------------ auto-afbeeldingen
class CarArt:
    """Knipt de auto's uit cars_sheet.png (neus wijst naar rechts)."""

    def __init__(self):
        sheet = pygame.image.load(SHEET_FILE).convert_alpha()
        self.big, self.spr, self.col = {}, {}, {}
        for i in range(38):
            col, row = i % SHEET_COLS, i // SHEET_COLS
            cell = sheet.subsurface((col * CELL_W, row * CELL_H, CELL_W, CELL_H)).copy()
            big = cell.subsurface(cell.get_bounding_rect()).copy()
            self.big[i] = big
            k = clamp(big.get_width() * 0.34, 52, 62) / big.get_width()
            self.spr[i] = pygame.transform.smoothscale(big, (round(big.get_width() * k), round(big.get_height() * k)))
            self.col[i] = pygame.transform.average_color(big, big.get_rect().inflate(-60, -40))[:3]


def car_params(stats):
    """Zet de 4 statistieken (0-10) om naar rij-eigenschappen."""
    return dict(vmax=455 + stats[0] * 15, accel=350 + stats[1] * 17, drift=stats[2], nitro=70 + stats[3] * 8)


# ------------------------------------------------------------------ geluid
SR = 22050


class Sfx:
    """Alle geluiden en de muziek worden zelf berekend: er zijn geen geluidsbestanden nodig.
    Is er geen geluidskaart, dan blijft het spel gewoon stil."""
    N_ENG = 8
    CH_SKID, CH_BOTS, CH_RAIN, CH_MUSIC, N_RES = 8, 9, 10, 11, 12

    def __init__(self):
        self.ok = False
        self.volume = 0.7
        self.music_on = True
        self.snd = {}
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512, allowedchanges=0)
            pygame.mixer.set_num_channels(28)
            pygame.mixer.set_reserved(self.N_RES)
            self.chs = [pygame.mixer.Channel(i) for i in range(self.N_RES)]
            self.rng = random.Random(7)
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    @staticmethod
    def _sound(samples, gain=1.0):
        pk = max(max(samples), -min(samples)) or 1.0
        k = gain * 0.95 / pk if pk * gain > 0.95 else gain
        return pygame.mixer.Sound(buffer=array("h", [int(v * k * 30000) for v in samples]).tobytes())

    @staticmethod
    def _lowpass(x, a):
        y, out = 0.0, []
        for v in x:
            y += a * (v - y)
            out.append(y)
        return out

    def _noise(self, n, a=1.0):
        x = [self.rng.uniform(-1, 1) for _ in range(n)]
        return x if a >= 1.0 else self._lowpass(x, a)

    def _build(self):
        tp, sin, exp = TAU, math.sin, math.exp
        # motor: 8 lussen met stijgende toonhoogte, het spel mengt ertussen
        N = 5512
        nz = self._noise(N, 0.5)
        self.eng = []
        for k in range(self.N_ENG):
            f = 42 * (250 / 42) ** (k / (self.N_ENG - 1))
            cyc = max(1, round(f * N / SR))
            buf = []
            for i in range(N):
                ph = tp * cyc * i / N
                v = sin(ph) * 0.5 + sin(2 * ph) * 0.34 + sin(3 * ph) * 0.22 + sin(4 * ph) * 0.14 + nz[i] * 0.08
                buf.append(math.tanh(v * 1.6) * 0.55)
            self.eng.append(self._sound(buf))
        N2 = SR // 2                                             # bandenkrijs
        nz = self._noise(N2, 0.7)
        self.skid = self._sound([0.3 * sin(tp * 1400 * i / SR + 3 * sin(tp * 8 * i / SR))
                                 + 0.18 * sin(tp * 2100 * i / SR) + 0.25 * nz[i] for i in range(N2)])
        r = self._noise(SR)                                      # regen
        lp = self._lowpass(r, 0.25)
        self.rain = self._sound([(r[i] - lp[i]) * 0.5 for i in range(SR)])

        nz1, nz2, nz3 = self._noise(SR, 0.6), self._noise(SR, 0.2), self._noise(SR, 0.9)

        def mk(dur, fn):
            return self._sound([fn(i / SR, i) for i in range(int(SR * dur))])

        sn = self.snd
        sn["hit"] = mk(0.35, lambda t, i: sin(tp * 70 * t) * exp(-t * 18) * 0.8 + sin(tp * 380 * t) * exp(-t * 35) * 0.25
                       + nz1[i] * exp(-t * 16) * 0.6)
        sn["bump"] = mk(0.22, lambda t, i: sin(tp * 55 * t) * exp(-t * 22) * 0.9 + nz2[i] * exp(-t * 20) * 1.2)
        sn["boost"] = mk(0.9, lambda t, i: (nz3[i] - nz1[i]) * 0.8 * min(1.0, t / 0.06) * exp(-t * 2.6)
                         + sin(tp * (90 + 55 * t) * t) * 0.25 * exp(-t * 2.6))
        sn["pop"] = mk(0.16, lambda t, i: nz2[i] * exp(-t * 30) * 1.6 + sin(tp * 90 * t) * exp(-t * 25) * 0.6)
        sn["beep"] = mk(0.22, lambda t, i: sin(tp * 440 * t) * min(1, t * 80) * exp(-t * 6) * 0.7)
        sn["go"] = mk(0.55, lambda t, i: (sin(tp * 880 * t) + 0.4 * sin(tp * 1320 * t)) * min(1, t * 80) * exp(-t * 4) * 0.55)
        sn["move"] = mk(0.05, lambda t, i: (1 if sin(tp * 900 * t) > 0 else -1) * exp(-t * 60) * 0.35)
        sn["ok"] = mk(0.22, lambda t, i: (1 if sin(tp * (660 if t < 0.07 else 990) * t) > 0 else -1) * exp(-t * 9) * 0.35)
        sn["back"] = mk(0.14, lambda t, i: (1 if sin(tp * (520 - 1200 * t) * t) > 0 else -1) * exp(-t * 14) * 0.3)
        sn["bank"] = mk(0.34, lambda t, i: sin(tp * (700 + 2600 * t) * t) * exp(-t * 7) * 0.45)
        sn["clip"] = mk(0.3, lambda t, i: (sin(tp * 1320 * t) + sin(tp * 1980 * t) * 0.5) * exp(-t * 12) * 0.5)
        sn["fail"] = mk(0.4, lambda t, i: (1 if sin(tp * (220 - 240 * t) * t) > 0 else -1) * exp(-t * 6) * 0.35)
        sn["lap"] = mk(0.4, lambda t, i: (sin(tp * 660 * t) if t < 0.15 else sin(tp * 880 * t))
                       * exp(-(t if t < 0.15 else t - 0.15) * 9) * 0.6)
        notes = (523.0, 659.0, 784.0, 1047.0, 1319.0)

        def fanfare(t, i):
            k = min(4, int(t / 0.13))
            lt = t - k * 0.13
            return (sin(tp * notes[k] * lt) + 0.3 * sin(tp * notes[k] * 2 * lt)) * min(1, lt * 120) \
                * exp(-lt * (5 if k < 4 else 2.2)) * 0.5
        sn["finish"] = mk(1.2, fanfare)
        self.music = self._make_music()

    def _make_music(self):
        """Eurobeat-achtige lus van 8 maten (150 BPM): bas, arpeggio, melodie en drums."""
        step = SR * 60 // 150 // 4                                # lengte van een 16e noot
        total = step * 16 * 8
        out = [0.0] * total
        A = 110.0

        def hz(semi):
            return A * 2 ** (semi / 12)
        chords = [(0, 3, 7), (-4, 0, 3), (-2, 2, 5), (-5, -2, 2), (0, 3, 7), (-4, 0, 3), (-2, 2, 5), (-5, -1, 2)]
        hook = [12, None, 15, 12, 19, None, 17, 15, 14, None, 15, 17, 14, None, 12, None]
        nz = self._noise(step * 2, 1.0)

        def add(pos, n, fn):
            for i in range(min(n, total - pos)):
                out[pos + i] += fn(i)

        for bar in range(8):
            root, third, fifth = chords[bar]
            for s in range(16):
                p = (bar * 16 + s) * step
                f = hz(root - 12 + (12 if s % 2 else 0)) / SR      # bas: octaaf-sprongen
                add(p, step, lambda i: (((i * f) % 1.0) * 2 - 1) * 0.30 * (1 - i / step) ** 0.6)
                f2 = hz((root, third, fifth, third + 12)[s % 4] + 12) / SR   # arpeggio (blokgolf)
                add(p, step, lambda i: (0.11 if (i * f2) % 1.0 < 0.5 else -0.11) * (1 - i / step))
                if s % 2 == 0:                                      # melodie
                    note = hook[(bar % 2) * 8 + s // 2]
                    if note is not None:
                        f3 = hz(note + 12) / SR
                        add(p, step * 2, lambda i: (0.5 * math.sin(TAU * i * f3) + (0.12 if (i * f3) % 1.0 < 0.3 else -0.12))
                            * 0.34 * math.exp(-i / step * 0.9))
                if s % 4 == 0:                                      # kick
                    add(p, step * 2, lambda i: math.sin(TAU * (150 * math.exp(-i / 900) + 45) * i / SR)
                        * math.exp(-i / 1500) * 0.7)
                if s % 4 == 2:                                      # hi-hat
                    add(p, step // 2, lambda i: nz[i] * math.exp(-i / 180) * 0.16)
                if s % 8 == 4:                                      # clap
                    add(p, step, lambda i: nz[i + 500] * math.exp(-i / 500) * 0.30)
        return self._sound(out, 0.8)

    # ---- afspelen
    def play(self, name, vol=1.0):
        if self.ok and self.volume > 0 and name in self.snd:
            s = self.snd[name]
            s.set_volume(min(1.0, vol * self.volume))
            s.play()

    def start_music(self):
        if self.ok and not self.chs[self.CH_MUSIC].get_busy():
            self.chs[self.CH_MUSIC].play(self.music, loops=-1)
        self.update_music()

    def update_music(self, duck=1.0):
        if self.ok:
            self.chs[self.CH_MUSIC].set_volume(0.6 * self.volume * duck if self.music_on else 0.0)

    def start_loops(self):
        if not self.ok:
            return
        for k in range(self.N_ENG):
            self.chs[k].play(self.eng[k], loops=-1)
            self.chs[k].set_volume(0)
        self.chs[self.CH_SKID].play(self.skid, loops=-1)
        self.chs[self.CH_BOTS].play(self.eng[3], loops=-1)
        self.chs[self.CH_RAIN].play(self.rain, loops=-1)
        for c in (self.CH_SKID, self.CH_BOTS, self.CH_RAIN):
            self.chs[c].set_volume(0)

    def stop_loops(self):
        if self.ok:
            for c in list(range(self.N_ENG)) + [self.CH_SKID, self.CH_BOTS, self.CH_RAIN]:
                self.chs[c].stop()

    def loops(self, rpm=0.0, power=0.0, boosting=False, skid=0.0, bots=0.0, rain=0.0, mute=False):
        """Geluiden die continu doorlopen; alle waarden tussen 0 en 1."""
        if not self.ok:
            return
        v = 0.0 if mute else self.volume
        p = clamp(rpm, 0, 1) * (self.N_ENG - 1)
        base = (0.2 + 0.45 * power) * (1.3 if boosting else 1.0)
        for k in range(self.N_ENG):
            self.chs[k].set_volume(min(1.0, max(0.0, 1 - abs(k - p)) * base * v))
        self.chs[self.CH_SKID].set_volume(min(1.0, skid * 0.5 * v))
        self.chs[self.CH_BOTS].set_volume(min(1.0, bots * 0.3 * v))
        self.chs[self.CH_RAIN].set_volume(min(1.0, rain * 0.3 * v))
