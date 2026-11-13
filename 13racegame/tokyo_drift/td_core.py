"""
td_core.py  -  gedeelde basis voor TOKYO DRIFT
Instellingen, hulpfuncties, lettertypes (met Japanse tekens), gloed-effecten,
auto-afbeeldingen, geluid + muziek (uit de mappen sounds en music) en het bewaarbestand.
"""
import json
import math
import os
import random

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
SOUND_DIR = os.path.join(DIR, "sounds")                  # alle geluidseffecten (.wav)
MUSIC_DIR = os.path.join(DIR, "music")                   # menu.ogg + de race-mix
MENU_MUSIC = os.path.join(MUSIC_DIR, "menu.ogg")         # Trackmania Turbo DS soundtrack
MUSIC_TYPES = (".mp3", ".ogg", ".wav", ".flac", ".opus")

# De race-muziek is 1 lang bestand: "It's 2001 and you're drifting in tokyo".
# Zet dat bestand in de map music (de naam moet "2001" bevatten).
# Hieronder staat de tracklist: (titel, starttijd in seconden). Elke race start op een ander nummer.
RACE_TRACKS = [
    ("Press Enter", 0), ("Distance", 240), ("Video Girl", 398), ("ASI", 605),
    ("Drift", 842), ("Text Me Back", 1070), ("2001", 1310), ("Soft Reboot", 1550),
    ("Daytime Lantern", 1789), ("Just Drive", 2024), ("Easy Muwi", 2263), ("Digital Crush", 2503),
    ("Shonen Heart", 2647), ("No Signal, No Goodbye", 2844), ("Shibuya Sunset", 3083), ("Offline Forever", 3274),
]

SOUND_NAMES = ["boost", "blowoff", "hit", "bump", "pop", "beep", "go", "move", "ok", "back",
               "bank", "clip", "fail", "lap", "finish"]


def find_race_music():
    """Zoekt het mix-bestand in de map music. Geeft None als het er niet is."""
    if os.path.isdir(MUSIC_DIR):
        for name in sorted(os.listdir(MUSIC_DIR)):
            if "2001" in name and name.lower().endswith(MUSIC_TYPES):
                return os.path.join(MUSIC_DIR, name)
    return None


class Sfx:
    """Alle geluiden komen uit bestanden in de mappen sounds en music.
    De motor bestaat uit 24 lussen van een echte DeLorean V6, elk op een ander toerental;
    het spel mengt tussen de twee lussen die het dichtst bij het toerental liggen.
    Is er geen geluidskaart of ontbreken de bestanden, dan blijft het spel gewoon stil."""
    N_ENG = 24
    CH_SKID, CH_BOTS, CH_RAIN, CH_NITRO, N_RES = 24, 25, 26, 27, 28

    def __init__(self):
        self.ok = False            # geluidseffecten geladen?
        self.music_ok = False      # muziek kan spelen?
        self.volume = 0.7
        self.music_on = True
        self.snd = {}
        self.now_playing = None    # "menu" of "race"
        self.race_file = None
        self.todo = []             # nummers die nog niet gespeeld zijn
        self.rng = random.Random() # eigen toeval, zodat de volgorde elke keer anders is
        self.rpm = 0.0             # vloeiend gemaakte waarden voor de motor
        self.power = 0.0
        self.nitro_vol = 0.0
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(44)
            pygame.mixer.set_reserved(self.N_RES)
            self.chs = [pygame.mixer.Channel(i) for i in range(self.N_RES)]
            self.music_ok = True
            self.race_file = find_race_music()
            self._load()
            self.ok = True
        except Exception as err:
            print("Geluid uit:", err)

    def _load(self):
        def wav(name):
            return pygame.mixer.Sound(os.path.join(SOUND_DIR, name + ".wav"))
        self.eng = [wav(f"engine_{k:02d}") for k in range(self.N_ENG)]
        self.skid, self.rain, self.nitro = wav("skid"), wav("rain"), wav("nitro")
        for name in SOUND_NAMES:
            self.snd[name] = wav(name)

    # ---- losse geluiden
    def play(self, name, vol=1.0):
        if self.ok and self.volume > 0 and name in self.snd:
            s = self.snd[name]
            s.set_volume(min(1.0, vol * self.volume))
            s.play()

    # ---- muziek
    def _start_music(self, path, start=0.0, loops=0):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=loops, start=start, fade_ms=600)
            return True
        except Exception as err:
            print("Muziek kan niet spelen:", path, err)
            return False

    def play_menu_music(self):
        if self.music_ok and self.now_playing != "menu" and os.path.exists(MENU_MUSIC):
            if self._start_music(MENU_MUSIC, loops=-1):
                self.now_playing = "menu"
        self.update_music()

    def play_race_music(self):
        """Start een ander nummer uit de mix. Geeft de titel terug (of None als het bestand er niet is)."""
        if not self.music_ok or not self.race_file:
            return None                                  # geen mix gevonden: de menu-muziek speelt verder
        if not self.todo:                                # alles gehad: opnieuw schudden
            self.todo = list(RACE_TRACKS)
            self.rng.shuffle(self.todo)
        title, start = self.todo.pop()
        if not self._start_music(self.race_file, start=start):
            return None
        self.now_playing = "race"
        self.update_music()
        return title

    def update_music(self, duck=1.0):
        if not self.music_ok:
            return
        if self.now_playing == "race" and not pygame.mixer.music.get_busy():
            self.play_race_music()                       # de mix is afgelopen: volgend nummer
        pygame.mixer.music.set_volume(0.7 * self.volume * duck if self.music_on else 0.0)

    # ---- geluiden die blijven doorlopen (motor, banden, regen, nitro)
    def start_loops(self):
        if not self.ok:
            return
        for k in range(self.N_ENG):
            self.chs[k].play(self.eng[k], loops=-1)
        self.chs[self.CH_SKID].play(self.skid, loops=-1)
        self.chs[self.CH_BOTS].play(self.eng[9], loops=-1)
        self.chs[self.CH_RAIN].play(self.rain, loops=-1)
        self.chs[self.CH_NITRO].play(self.nitro, loops=-1)
        for ch in self.chs:
            ch.set_volume(0)
        self.rpm = self.power = self.nitro_vol = 0.0

    def stop_loops(self):
        if self.ok:
            for ch in self.chs:
                ch.stop()

    def loops(self, rpm=0.0, power=0.0, boosting=False, skid=0.0, bots=0.0, rain=0.0, mute=False):
        """Wordt elk beeld opgeroepen; alle waarden liggen tussen 0 en 1."""
        if not self.ok:
            return
        v = 0.0 if mute else self.volume
        # het toerental en het gas volgen vloeiend, zo klinkt schakelen niet als een sprong
        self.rpm += (clamp(rpm, 0, 1) - self.rpm) * 0.18
        self.power += (power - self.power) * 0.15
        self.nitro_vol += ((1.0 if boosting else 0.0) - self.nitro_vol) * 0.12
        pos = self.rpm * (self.N_ENG - 1)                # welke lus hoort bij dit toerental
        loud = (0.35 + 0.55 * self.power) * (1.0 + 0.15 * self.nitro_vol) * v
        for k in range(self.N_ENG):
            near = max(0.0, 1 - abs(k - pos))            # 1 = precies deze lus, 0 = te ver weg
            self.chs[k].set_volume(min(1.0, math.sqrt(near) * loud))
        self.chs[self.CH_SKID].set_volume(min(1.0, skid * 0.4 * v))
        self.chs[self.CH_BOTS].set_volume(min(1.0, bots * 0.22 * v))
        self.chs[self.CH_RAIN].set_volume(min(1.0, rain * 0.3 * v))
        self.chs[self.CH_NITRO].set_volume(min(1.0, self.nitro_vol * 0.4 * v))
