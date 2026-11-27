"""
ma_core.py  -  gedeelde basis voor MONSTER ARENA
Instellingen, hulpfuncties, tekst (chroom/vuur-letters), gloed-effecten,
zelf gesynthetiseerd geluid + muziek en het bewaarbestand.
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
FONT_FILE = os.path.join(DIR, "arena_font.otf")
SHEET_FILE = os.path.join(DIR, "cars_sheet.png")
SAVE_FILE = os.path.join(DIR, "monster_arena_save.json")

FIRE, GOLD, HOT, RED = (255, 150, 30), (255, 214, 70), (255, 90, 40), (235, 50, 40)
STEEL, WHITE, CYAN, LIME, PINK = (170, 180, 196), (245, 240, 230), (90, 220, 255), (150, 240, 70), (255, 90, 200)
BOT_NAMES = ["CRUSHER", "MAD DOG", "T-REX", "BIG TONY", "VIPER", "RHINO", "HAMMER", "GRIZZLY"]

DEFAULTS = dict(preset=0, truck=dict(body=0, paint=0, accent=2, decal=1, wheels=1, extra=1, stats=[5, 5, 5, 5]),
                arena=0, time=120, bots=3, volume=7, music=1, scan=0, hs={})


# ------------------------------------------------------------------ hulpfuncties
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def dim(c, k):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


def lite(c, k):
    return mix(c, (255, 255, 255), k)


def dark(c, k):
    return mix(c, (0, 0, 0), k)


def wrap_rad(a):
    return (a + math.pi) % TAU - math.pi


def fmt_pts(p):
    return f"{int(p):,}".replace(",", ".")


def fmt_time(t):
    t = max(0.0, t)
    return f"{int(t // 60)}:{t % 60:04.1f}"


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            got = json.load(f)
        for k in data:
            if k in got and type(got[k]) is type(data[k]):
                data[k] = got[k]
        for k, v in DEFAULTS["truck"].items():
            if type(data["truck"].get(k)) is not type(v):
                data["truck"][k] = v
    except Exception:
        pass
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


# ------------------------------------------------------------------ tekst
_FONTS, _TEXT, _CHROME = {}, {}, {}


def font(size, italic=True):
    key = (size, italic)
    if key not in _FONTS:
        try:
            f = pygame.font.Font(FONT_FILE, size)
        except Exception:
            f = pygame.font.SysFont("impact,arialblack,arial", size, bold=True)
        f.set_italic(italic)
        _FONTS[key] = f
    return _FONTS[key]


def render(s, size, color=(255, 255, 255), italic=True):
    key = (s, size, color, italic)
    img = _TEXT.get(key)
    if img is None:
        if len(_TEXT) > 900:
            _TEXT.clear()
        img = font(size, italic).render(s, True, color)
        _TEXT[key] = img
    return img


def text(surf, s, size, pos, color=WHITE, anchor="topleft", italic=True, shadow=(0, 0, 0), off=2):
    img = render(s, size, color, italic)
    rect = img.get_rect(**{anchor: pos})
    if shadow is not None:
        surf.blit(render(s, size, shadow, italic), rect.move(off, off))
    surf.blit(img, rect)
    return rect


# kleurverlopen voor de grote letters: (boven, midden, onder-donker, onderrand, omlijning)
G_FIRE = ((255, 250, 190), (255, 200, 40), (225, 40, 20), (255, 170, 60), (40, 6, 0))
G_STEEL = ((255, 255, 255), (170, 184, 204), (60, 66, 84), (210, 220, 236), (10, 12, 20))
G_GOLD = ((255, 255, 220), (255, 214, 70), (190, 110, 10), (255, 236, 150), (40, 20, 0))
G_ICE = ((255, 255, 255), (130, 220, 255), (20, 70, 170), (200, 240, 255), (4, 14, 40))
G_LIME = ((250, 255, 210), (160, 240, 60), (20, 120, 30), (210, 255, 150), (4, 30, 6))
G_PINK = ((255, 255, 255), (255, 130, 210), (170, 10, 110), (255, 210, 240), (40, 0, 30))


def chrome(s, size, grad=G_FIRE, o=3, italic=True):
    """Arcade-letters: metalen kleurverloop met een 'horizon' in het midden en een dikke rand."""
    key = (s, size, grad, o, italic)
    if key in _CHROME:
        return _CHROME[key]
    top, mid, low, edge, outline = grad
    f = font(size, italic)
    white = f.render(s, True, (255, 255, 255))
    w, h = white.get_size()
    g = pygame.Surface((w, h), pygame.SRCALPHA)
    hz = int(h * 0.56)
    for y in range(h):
        c = mix(top, mid, y / max(1, hz)) if y < hz else mix(low, edge, ((y - hz) / max(1, h - hz)) ** 1.5)
        pygame.draw.line(g, (*c, 255), (0, y), (w, y))
    white.blit(g, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out = pygame.Surface((w + 2 * o + 6, h + 2 * o + 6), pygame.SRCALPHA)
    sh = f.render(s, True, (0, 0, 0))
    sh.set_alpha(160)
    out.blit(sh, (o + 6, o + 6))
    ol = f.render(s, True, outline)
    for dx in range(-o, o + 1):
        for dy in range(-o, o + 1):
            if dx * dx + dy * dy <= o * o + 1:
                out.blit(ol, (o + dx, o + dy))
    out.blit(white, (o, o))
    if len(_CHROME) > 260:
        _CHROME.clear()
    _CHROME[key] = out
    return out


def panel(surf, rect, tint=(16, 10, 8), alpha=205, edge=FIRE, w=2, cut=12):
    """Paneel met afgeschuinde hoeken (staalplaat-look)."""
    r = pygame.Rect(rect)
    pts = [(cut, 0), (r.w, 0), (r.w, r.h - cut), (r.w - cut, r.h), (0, r.h), (0, cut)]
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.polygon(s, (*tint, alpha), pts)
    if edge:
        pygame.draw.polygon(s, (*edge, 255), pts, w)
        for px, py in ((cut + 6, 7), (r.w - 9, 7), (r.w - cut - 6, r.h - 8), (8, r.h - 8)):      # klinknagels
            pygame.draw.circle(s, dim(edge, 0.6), (px, py), 2)
    surf.blit(s, r.topleft)


def hazard(surf, rect, t=0.0, c1=(244, 196, 20), c2=(16, 14, 12)):
    """Geel-zwarte waarschuwingsstrepen (schuivend)."""
    r = pygame.Rect(rect)
    clip = surf.get_clip()
    surf.set_clip(r)
    pygame.draw.rect(surf, c2, r)
    off = int(t) % 44
    for x in range(r.x - 66 + off, r.right + 44, 44):
        pygame.draw.polygon(surf, c1, [(x, r.bottom), (x + 22, r.bottom), (x + 22 + r.h, r.y), (x + r.h, r.y)])
    surf.set_clip(clip)


# ------------------------------------------------------------------ gloed
_GLOW = {}


def glow(size, color, power=2.0):
    """Zachte ronde gloed op zwart. Teken hem met special_flags=pygame.BLEND_RGB_ADD."""
    key = (size, color, power)
    g = _GLOW.get(key)
    if g is None:
        if len(_GLOW) > 400:
            _GLOW.clear()
        g = pygame.Surface((size, size))
        R = size / 2
        for r in range(int(R), 0, -1):
            v = (1 - r / R) ** power
            pygame.draw.circle(g, (int(color[0] * v), int(color[1] * v), int(color[2] * v)), (size // 2, size // 2), r)
        _GLOW[key] = g
    return g


def add_glow(surf, x, y, size, color, power=2.0):
    surf.blit(glow(size, color, power), (int(x - size / 2), int(y - size / 2)), special_flags=pygame.BLEND_RGB_ADD)


def soft(radius, color, a_max=70):
    """Zachte vlek met alpha (voor schaduw / lichtplassen op de wereld)."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(24):
        t = i / 24
        pygame.draw.circle(s, (*color, int(a_max * t * t)), (radius, radius), int(radius * (1 - t) + 2))
    return s


def make_vignette(strength=150):
    small = pygame.Surface((160, 90), pygame.SRCALPHA)
    for y in range(90):
        for x in range(160):
            d = math.hypot((x - 80) / 80, (y - 45) / 45)
            small.set_at((x, y), (0, 0, 0, int(strength * clamp((d - 0.55) / 0.75, 0, 1) ** 2)))
    return pygame.transform.smoothscale(small, (W, H))


def make_edge_glow(color):
    small = pygame.Surface((160, 90))
    for y in range(90):
        for x in range(160):
            d = math.hypot((x - 80) / 80, (y - 45) / 45)
            small.set_at((x, y), dim(color, clamp((d - 0.6) / 0.7, 0, 1) ** 1.6))
    return pygame.transform.smoothscale(small, (W, H))


def make_scanlines():
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 3):
        pygame.draw.line(s, (0, 0, 0, 50), (0, y), (W, y))
    return s


# ------------------------------------------------------------------ geluid
SR = 22050


class Sfx:
    """Alle geluiden en de muziek worden zelf berekend: er zijn geen geluidsbestanden nodig.
    Is er geen geluidskaart, dan blijft het spel gewoon stil."""
    N_ENG = 8
    CH_DIRT, CH_BOTS, CH_CROWD, CH_MUSIC, N_RES = 8, 9, 10, 11, 12

    def __init__(self):
        self.ok = False
        self.volume = 0.7
        self.music_on = True
        self.snd = {}
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512, allowedchanges=0)
            pygame.mixer.set_num_channels(30)
            pygame.mixer.set_reserved(self.N_RES)
            self.chs = [pygame.mixer.Channel(i) for i in range(self.N_RES)]
            self.rng = random.Random(11)
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
        # V8-motor: 8 lussen met stijgende toonhoogte; ruw door de ongelijke 'cilinders'
        N = 5512
        nz = self._noise(N, 0.5)
        self.eng = []
        for k in range(self.N_ENG):
            f = 30 * (190 / 30) ** (k / (self.N_ENG - 1))
            cyc = max(1, round(f * N / SR))
            buf = []
            for i in range(N):
                ph = tp * cyc * i / N
                v = (sin(ph) * 0.55 + sin(2 * ph + 0.4) * 0.4 + sin(3 * ph) * 0.3 + sin(0.5 * ph) * 0.35
                     + sin(4.5 * ph) * 0.16 + nz[i] * 0.12)
                buf.append(math.tanh(v * 2.2) * 0.55)
            self.eng.append(self._sound(buf))
        d = self._lowpass(self._lowpass(self._noise(SR), 0.12), 0.5)        # banden op zand
        self.dirt = self._sound([clamp(v * 7.0, -1, 1) * 0.6 for v in d])
        c = self._lowpass(self._noise(SR * 2), 0.18)                         # publiek (ruis die golft)
        self.crowd = self._sound([c[i] * (0.7 + 0.3 * sin(tp * 0.5 * i / SR) * sin(tp * 3.1 * i / SR)) * 3.0 for i in range(SR * 2)])

        nz1, nz2, nz3 = self._noise(SR * 2, 0.6), self._noise(SR * 2, 0.2), self._noise(SR * 2, 0.9)

        def mk(dur, fn):
            return self._sound([fn(i / SR, i) for i in range(int(SR * dur))])

        sq = lambda x: 1.0 if sin(x) > 0 else -1.0                          # noqa: E731  blokgolf
        sn = self.snd
        sn["hit"] = mk(0.35, lambda t, i: sin(tp * 70 * t) * exp(-t * 18) * 0.8 + sin(tp * 380 * t) * exp(-t * 35) * 0.25
                       + nz1[i] * exp(-t * 16) * 0.6)
        sn["bump"] = mk(0.22, lambda t, i: sin(tp * 55 * t) * exp(-t * 22) * 0.9 + nz2[i] * exp(-t * 20) * 1.2)
        sn["thud"] = mk(0.45, lambda t, i: sin(tp * (110 - 110 * t) * t) * exp(-t * 8) * 0.9 + nz2[i] * exp(-t * 14) * 1.4)
        sn["jump"] = mk(0.45, lambda t, i: (sin(tp * (160 + 290 * t) * t) * 0.3 + (nz3[i] - nz1[i]) * 0.35) * sin(math.pi * t / 0.45))
        sn["boost"] = mk(0.9, lambda t, i: (nz3[i] - nz1[i]) * 0.8 * min(1.0, t / 0.06) * exp(-t * 2.6)
                         + sin(tp * (90 + 55 * t) * t) * 0.25 * exp(-t * 2.6))
        sn["crush"] = mk(0.5, lambda t, i: nz1[i] * exp(-t * 9) * 0.9 + (nz3[i] - nz1[i]) * exp(-t * 22) * 0.7
                         + sin(tp * 190 * t + 6 * sin(tp * 37 * t)) * exp(-t * 12) * 0.4)
        sn["boom"] = mk(1.1, lambda t, i: sin(tp * (95 * exp(-t * 5) + 28) * t) * exp(-t * 3.2) * 1.0
                        + nz2[i] * exp(-t * 4.5) * 1.6 + nz3[i] * exp(-t * 30) * 0.6)
        sn["smash"] = mk(0.25, lambda t, i: nz1[i] * exp(-t * 20) + sin(tp * 240 * t) * exp(-t * 30) * 0.4)
        sn["cheer"] = mk(1.6, lambda t, i: (nz1[i] * 0.8 + nz3[i] * 0.25) * sin(math.pi * min(1.0, t / 1.6)) ** 0.7
                         * (0.75 + 0.25 * sin(tp * 6 * t)))
        sn["horn"] = mk(0.7, lambda t, i: (((t * 233) % 1.0) + ((t * 277) % 1.0) + ((t * 349) % 1.0) - 1.5) * 0.3
                        * min(1, t * 30) * min(1, (0.7 - t) * 12))
        sn["trick"] = mk(0.3, lambda t, i: sq(tp * (523 if t < 0.08 else 784 if t < 0.16 else 1047) * t) * exp(-(t % 0.08) * 8) * 0.3)
        sn["big"] = mk(0.6, lambda t, i: sq(tp * (523, 659, 784, 1047, 1319)[min(4, int(t / 0.08))] * t)
                       * exp(-(t % 0.08 if t < 0.4 else t - 0.4) * 6) * 0.3)
        sn["pickup"] = mk(0.25, lambda t, i: sin(tp * (700 + 2400 * t) * t) * exp(-t * 9) * 0.5)
        sn["fire"] = mk(0.6, lambda t, i: (nz2[i] * 1.4 + nz1[i] * 0.4) * min(1, t * 25) * exp(-t * 5))
        sn["fail"] = mk(0.4, lambda t, i: sq(tp * (220 - 240 * t) * t) * exp(-t * 6) * 0.35)
        sn["beep"] = mk(0.22, lambda t, i: sin(tp * 440 * t) * min(1, t * 80) * exp(-t * 6) * 0.7)
        sn["go"] = mk(0.55, lambda t, i: (sin(tp * 880 * t) + 0.4 * sin(tp * 1320 * t)) * min(1, t * 80) * exp(-t * 4) * 0.55)
        sn["move"] = mk(0.05, lambda t, i: sq(tp * 700 * t) * exp(-t * 60) * 0.35)
        sn["ok"] = mk(0.22, lambda t, i: sq(tp * (440 if t < 0.07 else 660) * t) * exp(-t * 9) * 0.35)
        sn["back"] = mk(0.14, lambda t, i: sq(tp * (420 - 1000 * t) * t) * exp(-t * 14) * 0.3)
        notes = (392.0, 523.0, 659.0, 784.0, 1047.0)
        sn["finish"] = mk(1.3, lambda t, i: (sin(tp * notes[min(4, int(t / 0.13))] * t) + 0.3 * sq(tp * notes[min(4, int(t / 0.13))] * t))
                          * exp(-((t % 0.13) if t < 0.52 else t - 0.52) * 3.5) * 0.4)
        self.music = self._make_music()

    def _make_music(self):
        """Hardrock-riff van 8 maten (138 BPM): vervormde powerchords, bas en drums."""
        step = SR * 60 // 138 // 4
        total = step * 16 * 8
        out = [0.0] * total
        E = 82.41

        def hz(semi):
            return E * 2 ** (semi / 12)
        # per maat: grondtoon + ritme (1 = aanslag op deze 16e, 2 = lange aanslag)
        riff = [(0, "1.1.2...1.1.2..."), (0, "1.1.2...1.112..."), (3, "1.1.2...1.1.2..."), (5, "2...2...1.1.1.1."),
                (0, "1.1.2...1.1.2..."), (0, "1.1.2...1.112..."), (8, "2...1.1.2...1.1."), (7, "2...2...2.2.2.22")]
        nz = self._noise(step * 4, 1.0)

        def add(pos, n, fn):
            for i in range(min(n, total - pos)):
                out[pos + i] += fn(i)

        for bar, (root, pat) in enumerate(riff):
            f0, f5, f8 = hz(root) / SR, hz(root + 7) / SR, hz(root + 12) / SR
            fb = hz(root - 12) / SR
            for s in range(16):
                p = (bar * 16 + s) * step
                if pat[s] != ".":
                    n = step * (4 if pat[s] == "2" else 2)
                    mute = 0.55 if pat[s] == "1" else 0.22
                    add(p, n, lambda i: math.tanh((((i * f0) % 1.0) + ((i * f5) % 1.0) + ((i * f8) % 1.0) - 1.5) * 3.0)
                        * 0.2 * math.exp(-i / n * mute * 5))
                    add(p, n, lambda i: math.sin(TAU * i * fb) * 0.3 * math.exp(-i / n * 2))
                if s % 8 == 0 or (bar % 2 == 1 and s == 10):                 # kick
                    add(p, step * 2, lambda i: math.sin(TAU * (140 * math.exp(-i / 800) + 44) * i / SR) * math.exp(-i / 1500) * 0.75)
                if s % 8 == 4:                                               # snare
                    add(p, step * 2, lambda i: nz[i] * math.exp(-i / 700) * 0.42 + math.sin(TAU * 190 * i / SR) * math.exp(-i / 400) * 0.3)
                if s % 2 == 0:                                               # hi-hat
                    add(p, step // 2, lambda i: nz[i + 900] * math.exp(-i / 150) * 0.11)
        return self._sound(out, 0.85)

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
            self.chs[self.CH_MUSIC].set_volume(0.55 * self.volume * duck if self.music_on else 0.0)

    def start_loops(self):
        if not self.ok:
            return
        for k in range(self.N_ENG):
            self.chs[k].play(self.eng[k], loops=-1)
            self.chs[k].set_volume(0)
        self.chs[self.CH_DIRT].play(self.dirt, loops=-1)
        self.chs[self.CH_BOTS].play(self.eng[3], loops=-1)
        self.chs[self.CH_CROWD].play(self.crowd, loops=-1)
        for c in (self.CH_DIRT, self.CH_BOTS, self.CH_CROWD):
            self.chs[c].set_volume(0)

    def stop_loops(self):
        if self.ok:
            for c in list(range(self.N_ENG)) + [self.CH_DIRT, self.CH_BOTS, self.CH_CROWD]:
                self.chs[c].stop()

    def loops(self, rpm=0.0, power=0.0, boosting=False, dirt=0.0, bots=0.0, crowd=0.0, mute=False):
        """Geluiden die continu doorlopen; alle waarden tussen 0 en 1."""
        if not self.ok:
            return
        v = 0.0 if mute else self.volume
        p = clamp(rpm, 0, 1) * (self.N_ENG - 1)
        base = (0.22 + 0.45 * power) * (1.3 if boosting else 1.0)
        for k in range(self.N_ENG):
            self.chs[k].set_volume(min(1.0, max(0.0, 1 - abs(k - p)) * base * v))
        self.chs[self.CH_DIRT].set_volume(min(1.0, dirt * 0.5 * v))
        self.chs[self.CH_BOTS].set_volume(min(1.0, bots * 0.3 * v))
        self.chs[self.CH_CROWD].set_volume(min(1.0, (0.10 + crowd * 0.45) * v))
