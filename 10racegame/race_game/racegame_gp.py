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
    GARAGE        kies uit 38 auto's, geef ze een kleurtint en tune alles vrij
    OMGEVING      kies bij de instellingen: Natuur, Stad, OFF-ROAD (zand, sprongen, modder)
                  of SNELWEG (4 rijstroken met verkeer; jij kiest hoeveel auto's er rijden)
                  of TOKYO (neonstad bij nacht: hier is DRIFTEN het doel, je krijgt punten voor je slijphoek)
    GELUID        motor, bandenkrijs, botsingen, sprongen... (volume in de instellingen)
    ARENA         monstertrucks die stunts doen: sprong, backflip, frontflip, wheelie, 360-draai...
                  Bouw je eigen truck, haal highscores (freestyle) of battle tegen bots.

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
from array import array

import pygame

# ------------------------------------------------------------------ instellingen
W, H = 1280, 720
FPS = 60
TAU = math.pi * 2

ROAD_W = 170            # breedte van het asfalt
HALF = ROAD_W / 2
DS = 12                 # afstand tussen punten van de middenlijn (px)
WALL_LIMIT = HALF - 8   # off-road: zo ver mag het midden van een auto van de middenlijn
ENV_NAMES = ["Natuur", "Stad", "Off-road", "Snelweg", "Tokyo"]
ENV_HIGHWAY = 3
ENV_TOKYO = 4
TK_HALF = 118                                    # Tokyo: extra breed asfalt om te driften

# snelweg: 4 rijstroken in dezelfde richting + vluchtstrook, met vangrail erlangs
HW_LANES = 4
HW_LANE_W = 56                                   # breedte van een rijstrook (px)
HW_LANE_HALF = HW_LANES * HW_LANE_W / 2          # halve breedte van de rijstroken
HW_HALF = HW_LANE_HALF + 22                      # halve breedte van het asfalt incl. vluchtstrook
HW_LANE_C = [(k - (HW_LANES - 1) / 2) * HW_LANE_W for k in range(HW_LANES)]   # midden per strook
HW_R = 1750                                      # grootte van de snelwegring
MAX_TRAFFIC = 40                                 # maximaal aantal burgerauto's
CIVIL_MODELS = [10, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25, 26, 27, 29, 34, 36, 37]   # 'gewone' auto's uit de sheet
# per moeilijkheid: de snelweg krijgt steeds iets meer bochten (maar blijft ruim)
HW_LEVELS = {1: dict(K=3, A0=0.14, min_r=560), 2: dict(K=4, A0=0.17, min_r=500),
             3: dict(K=5, A0=0.20, min_r=440), 4: dict(K=6, A0=0.22, min_r=400),
             5: dict(K=7, A0=0.24, min_r=360)}

TURN_RATE = 3.3         # stuursnelheid (rad/s)
TURN_LOSS = 0.38        # minder wendbaar bij hoge snelheid
BASE_ACCEL = 430
BRAKE = 720
NITRO_USE = 32          # nitro per seconde verbruikt
NITRO_REGEN = 9         # nitro per seconde bijgeladen

POINTS = [25, 18, 15, 12, 10, 8, 6, 4]      # Grand Prix punten per positie
MAX_BOTS = 7
STAT_MAX = 10                               # tuning: elk onderdeel vrij van 0 tot 10
STAT_NAMES = ["Topsnelheid", "Acceleratie", "Wendbaarheid", "Nitro"]
SHEET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars_sheet.png")
SHEET_COLS, CELL_W, CELL_H = 10, 208, 112      # indeling van cars_sheet.png
NUM_CARS = 38                                  # aantal auto's in de sheet
TINT_STEPS = 24                                # kleurtint-standen in de garage

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

# arena (monstertrucks)
TRUCK_STYLES = ["Pickup", "Muscle", "Beast", "Buggy"]
TRUCK_DECALS = ["Geen", "Vlammen", "Racestrepen", "Geblokt", "Bliksem"]
TRUCK_WHEELS = ["Normaal", "Groot", "Gigantisch"]
TRUCK_STATS = ["Topsnelheid", "Vering (hoogte)", "Flip-snelheid", "Nitro"]
ARENA_MODES = ["FREESTYLE", "BATTLE"]
ARENA_MAX_BOTS = 5
ARENA_TIME_MIN, ARENA_TIME_MAX = 60, 300

PALETTE = [(225, 40, 40), (255, 140, 30), (250, 205, 40), (140, 210, 50),
           (40, 170, 80), (30, 185, 170), (60, 190, 240), (50, 120, 235),
           (140, 80, 220), (240, 90, 170), (235, 235, 240), (45, 48, 56)]
ACCENTS = [(245, 245, 245), (20, 20, 24), (250, 205, 40), (225, 40, 40),
           (50, 120, 235), (255, 140, 30), (40, 170, 80), (170, 175, 190)]
BOT_NAMES = ["Viper", "Blitz", "Nova", "Turbo", "Apex", "Drift", "Rocket", "Comet",
             "Falcon", "Storm"]

DEFAULTS = dict(level=2, bots=3, laps_q=5, laps_gp=3, weather=0, env=0, volume=7, gp_races=4, traffic=12,
                car=dict(model=0, tint=0, stats=[5, 5, 5, 5]),
                truck=dict(style=0, color=0, accent=2, decal=1, wheels=1, lights=1, stats=[5, 5, 5, 5]),
                arena_mode=0, arena_bots=3, arena_time=120,
                hs=dict(free=[], battle=[], stunt=0, stunt_name=""))


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


def mix(a, b, t):
    """Meng twee kleuren (t = 0 -> a, t = 1 -> b)."""
    t = clamp(t, 0.0, 1.0)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def car_params(stats):
    """Vertaal de tuningpunten naar echte eigenschappen."""
    s, a, h, n = stats
    return dict(vmax=450 + 22 * s, accel=BASE_ACCEL * (0.8 + 0.04 * a),
                turn=0.85 + 0.03 * h, nitro=60 + 8 * n)


# ------------------------------------------------------------------ opslaan / laden
def sanitize(d):
    d["level"] = int(clamp(int(d["level"]), 1, 5))
    d["bots"] = int(clamp(int(d["bots"]), 1, MAX_BOTS))
    d["laps_q"] = int(clamp(int(d["laps_q"]), 1, 10))
    d["laps_gp"] = int(clamp(int(d["laps_gp"]), 1, 10))
    d["weather"] = 1 if int(d["weather"]) else 0
    d["env"] = int(clamp(int(d["env"]), 0, len(ENV_NAMES) - 1))
    d["traffic"] = int(clamp(int(d["traffic"]), 0, MAX_TRAFFIC))
    d["volume"] = int(clamp(int(d["volume"]), 0, 10))
    d["gp_races"] = int(clamp(int(d["gp_races"]), 2, 8))
    d["arena_mode"] = 1 if int(d["arena_mode"]) else 0
    d["arena_bots"] = int(clamp(int(d["arena_bots"]), 1, ARENA_MAX_BOTS))
    d["arena_time"] = int(clamp(round(int(d["arena_time"]) / 30) * 30, ARENA_TIME_MIN, ARENA_TIME_MAX))
    tr = d["truck"]
    tr["style"] = int(clamp(int(tr["style"]), 0, len(TRUCK_STYLES) - 1))
    tr["color"] = int(clamp(int(tr["color"]), 0, len(PALETTE) - 1))
    tr["accent"] = int(clamp(int(tr["accent"]), 0, len(ACCENTS) - 1))
    tr["decal"] = int(clamp(int(tr["decal"]), 0, len(TRUCK_DECALS) - 1))
    tr["wheels"] = int(clamp(int(tr["wheels"]), 0, len(TRUCK_WHEELS) - 1))
    tr["lights"] = 1 if int(tr["lights"]) else 0
    tst = [int(clamp(int(v), 0, STAT_MAX)) for v in list(tr["stats"])[:4]]
    while len(tst) < 4:
        tst.append(5)
    tr["stats"] = tst
    hs = d["hs"]
    for k in ("free", "battle"):
        hs[k] = sorted((int(v) for v in hs.get(k, [])), reverse=True)[:5]
    hs["stunt"] = max(0, int(hs.get("stunt", 0)))
    hs["stunt_name"] = str(hs.get("stunt_name", ""))[:40]
    car = d["car"]
    car["model"] = int(clamp(int(car["model"]), 0, NUM_CARS - 1))
    car["tint"] = int(clamp(int(car["tint"]), 0, TINT_STEPS - 1))
    st = [int(clamp(int(v), 0, STAT_MAX)) for v in list(car["stats"])[:4]]
    while len(st) < 4:
        st.append(5)
    if sum(st) == 12 and max(st) <= 6:          # oud opslagformaat (puntenbudget) -> standaard
        st = [5, 5, 5, 5]
    car["stats"] = st


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        for k in data:
            if isinstance(data[k], dict) and isinstance(raw.get(k), dict):
                data[k].update(raw[k])
            elif k in raw:
                data[k] = raw[k]
        if "city" in raw and "env" not in raw:            # oud opslagformaat
            data["env"] = 1 if raw["city"] else 0
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


def _valid(pts, min_r, road_w=ROAD_W):
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
    sep2 = (road_w + 80) ** 2
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


def generate_highway_centerline(level):
    """Lange, ruime snelwegring met zachte bochten (de bochten nemen toe met de moeilijkheid)."""
    cfg = HW_LEVELS[level]
    a0 = cfg["A0"]
    for attempt in range(800):
        if attempt and attempt % 80 == 0:
            a0 *= 0.85
        raw = _polar_curve(cfg["K"], a0, HW_R)
        if raw is None:
            continue
        pts = _resample(raw, DS)
        if len(pts) < 400 or not _valid(pts, cfg["min_r"], 2 * HW_HALF + 20):
            continue
        return _straightest_start(pts)
    return _straightest_start(_resample(_polar_curve(0, 0, HW_R), DS))


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


# ------------------------------------------------------------------ TOKYO: drift-kaart bij nacht
# Het Japans lettertype (tokyo_jp.otf = Noto Sans CJK JP, SIL Open Font License) staat naast dit bestand.
# Ontbreekt het? Dan wordt een Japans systeemfont gebruikt, en anders Engelse tekst.
TK_FONT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokyo_jp.otf")
JP_SYSFONTS = ("yugothicui,yugothic,meiryoui,meiryo,msgothic,hiraginosans,hiraginokakugothicpro,"
               "notosanscjkjp,notosansjp,takaoexgothic,ipagothic,vlgothic")
TK_LEVELS = {1: dict(K=6, A0=0.34, R=1000, min_r=200), 2: dict(K=7, A0=0.35, R=1150, min_r=200),
             3: dict(K=9, A0=0.36, R=1300, min_r=180), 4: dict(K=11, A0=0.38, R=1400, min_r=160),
             5: dict(K=13, A0=0.40, R=1500, min_r=145)}
NEON = [(255, 60, 160), (60, 230, 255), (200, 70, 255), (255, 150, 40), (90, 255, 150),
        (255, 70, 70), (255, 230, 80), (235, 235, 255)]
# (Japans, Engelse reserve-tekst): echte winkel- en wijknamen uit Tokyo
TK_SIGNS = [("ラーメン", "RAMEN"), ("居酒屋", "IZAKAYA"), ("焼肉", "YAKINIKU"), ("寿司", "SUSHI"),
            ("カラオケ", "KARAOKE"), ("パチンコ", "PACHINKO"), ("薬局", "PHARMACY"), ("ホテル", "HOTEL"),
            ("喫茶", "KISSA"), ("麻雀", "MAHJONG"), ("酒", "SAKE"), ("営業中", "OPEN"), ("24時間", "24H"),
            ("歌舞伎町", "KABUKICHO"), ("新宿", "SHINJUKU"), ("渋谷", "SHIBUYA"), ("秋葉原", "AKIHABARA"),
            ("原宿", "HARAJUKU"), ("銀座", "GINZA"), ("池袋", "IKEBUKURO"), ("六本木", "ROPPONGI"),
            ("上野", "UENO"), ("ゲーム", "GAME"), ("カフェ", "CAFE"), ("焼鳥", "YAKITORI"),
            ("天ぷら", "TEMPURA"), ("うどん", "UDON"), ("牛丼", "GYUDON"), ("中華", "CHUKA"),
            ("電気", "DENKI"), ("東京", "TOKYO"), ("おでん", "ODEN"), ("たこ焼き", "TAKOYAKI"),
            ("ようこそ", "WELCOME"), ("湯", "SENTO"), ("ゲームセンター", "ARCADE")]
_JP = {}
_TKG = {}


def jp_font(size):
    """Font met Japanse tekens (of None als er geen is)."""
    if size not in _JP:
        f = None
        if os.path.exists(TK_FONT_FILE):
            try:
                f = pygame.font.Font(TK_FONT_FILE, size)
            except Exception:
                f = None
        if f is None:
            try:
                path = pygame.font.match_font(JP_SYSFONTS)
                f = pygame.font.Font(path, size) if path else None
            except Exception:
                f = None
        _JP[size] = f
    return _JP[size]


def jp_surf(jp, lat, size, color, vertical=False):
    """Tekst als afbeelding. Zonder Japans font: de Engelse reserve-tekst."""
    f = jp_font(size)
    s = jp
    if f is None:
        f, s, vertical = pygame.font.SysFont("segoeui,arial", size, bold=True), lat, False
    if vertical and len(s) > 1:
        imgs = [f.render(ch, True, color) for ch in s]
        w = max(i.get_width() for i in imgs)
        step = int(size * 1.02)
        out = pygame.Surface((w, step * len(imgs) + 4), pygame.SRCALPHA)
        for k, im in enumerate(imgs):
            out.blit(im, (w // 2 - im.get_width() // 2, k * step))
        return out
    return f.render(s, True, color)


def tk_glow(size, color, power=2.0):
    k = (size, color, power)
    if k not in _TKG:
        _TKG[k] = make_glow(size, color, power)
    return _TKG[k]


def add_glow(world, x, y, size, color, power=2.0):
    g = tk_glow(size, color, power)
    world.blit(g, (int(x - size / 2), int(y - size / 2)), special_flags=pygame.BLEND_RGB_ADD)


def neon_sign(jp, lat, size, color, vertical=False):
    """Neon uithangbord: donker bord met gloeiende rand en gloeiende letters."""
    core = mix(color, (255, 255, 255), 0.55)
    txt = jp_surf(jp, lat, size, color, vertical)
    tw, th = txt.get_size()
    pad, m = 6, 5
    w, h = tw + 2 * pad + 2 * m, th + 2 * pad + 2 * m
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    board = pygame.Rect(m, m, w - 2 * m, h - 2 * m)
    for k, a in ((4, 28), (3, 46), (2, 70), (1, 100)):
        pygame.draw.rect(out, (*color, a), board.inflate(2 * k, 2 * k), 2, border_radius=6)
    pygame.draw.rect(out, (10, 8, 20, 240), board, border_radius=5)
    pygame.draw.rect(out, (*core, 255), board, 2, border_radius=5)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        g = txt.copy()
        g.set_alpha(70)
        out.blit(g, (m + pad + dx, m + pad + dy))
    out.blit(jp_surf(jp, lat, size, core, vertical), (m + pad, m + pad))
    return out


def road_paint(jp, lat, size, ang, color=(214, 214, 200), alpha=215, stretch=1.9):
    """Tekst die op het asfalt geschilderd is: uitgerekt in rijrichting (zoals op Japanse wegen)."""
    txt = jp_surf(jp, lat, size, color)
    sw, sh = txt.get_size()
    txt = pygame.transform.smoothscale(txt, (sw, int(sh * stretch)))
    rot = pygame.transform.rotate(txt, ang)
    rot.set_alpha(alpha)
    return rot


def make_tokyo_tile(size=256):
    t = pygame.Surface((size, size))
    t.fill((20, 22, 32))
    for _ in range(2200):
        d = random.randint(-7, 7)
        c = (clamp(24 + d, 0, 255), clamp(26 + d, 0, 255), clamp(38 + d, 0, 255))
        pygame.draw.circle(t, c, (random.randrange(size), random.randrange(size)), random.randint(1, 2))
    return t


def draw_tk_building(world, x, y, bw, bh):
    """Gebouw bij nacht: dak met installaties, verlichte raamstroken en een neonbord."""
    x0, y0 = int(x - bw / 2), int(y - bh / 2)
    pygame.draw.rect(world, (6, 6, 12), (x0 + 12, y0 + 16, bw + 8, bh + 10), border_radius=4)       # schaduw
    fh = random.randint(18, 26)                                                                    # gevel (zuidkant)
    fw = random.randint(10, 16)                                                                    # gevel (oostkant)
    pygame.draw.rect(world, (16, 18, 30), (x0, y0 + bh - 4, bw, fh + 4))
    pygame.draw.rect(world, (12, 14, 24), (x0 + bw - 4, y0 + 6, fw + 4, bh + fh - 6))
    lit = random.choice([(255, 226, 150), (190, 230, 255), (255, 205, 130), (255, 240, 210)])
    for wx in range(x0 + 5, x0 + bw - 8, 11):                                                      # ramen zuidgevel
        for wy in range(y0 + bh + 2, y0 + bh + fh - 3, 10):
            col = lit if random.random() < 0.55 else (26, 30, 46)
            pygame.draw.rect(world, col, (wx, wy, 6, 6))
    for wy in range(y0 + 12, y0 + bh + fh - 6, 11):                                                # ramen oostgevel
        col = lit if random.random() < 0.5 else (22, 26, 40)
        pygame.draw.rect(world, mix(col, (0, 0, 0), 0.3), (x0 + bw + 2, wy, 6, 6))
    roof = random.choice([(54, 58, 78), (62, 66, 86), (46, 50, 70), (72, 62, 74), (48, 64, 76), (58, 56, 66)])
    pygame.draw.rect(world, roof, (x0, y0, bw, bh), border_radius=3)
    pygame.draw.rect(world, mix(roof, (150, 160, 190), 0.35), (x0, y0, bw, bh), 2, border_radius=3)
    pygame.draw.rect(world, mix(roof, (0, 0, 0), 0.25), (x0 + 6, y0 + 6, bw - 12, bh - 12), 1)
    for _ in range(random.randint(1, 4)):                                                          # airco's
        ax, ay = random.randint(x0 + 8, x0 + bw - 24), random.randint(y0 + 8, y0 + bh - 22)
        pygame.draw.rect(world, (96, 100, 112), (ax, ay, 16, 12), border_radius=2)
        pygame.draw.circle(world, (36, 38, 48), (ax + 8, ay + 6), 4)
    kind = random.random()
    if kind < 0.18 and min(bw, bh) > 80:                                                           # watertank
        tx, ty = x0 + bw // 2 + random.randint(-12, 12), y0 + bh // 2 + random.randint(-10, 10)
        pygame.draw.circle(world, (30, 32, 42), (tx + 5, ty + 6), 15)
        pygame.draw.circle(world, (120, 126, 140), (tx, ty), 15)
        pygame.draw.circle(world, (170, 176, 190), (tx - 3, ty - 3), 8)
    elif kind < 0.26 and min(bw, bh) > 90:                                                         # helikopterplatform
        tx, ty = x0 + bw // 2, y0 + bh // 2
        pygame.draw.circle(world, (40, 44, 58), (tx, ty), 26)
        pygame.draw.circle(world, (230, 200, 60), (tx, ty), 26, 2)
        f = pygame.font.SysFont("arial", 26, bold=True)
        img = f.render("H", True, (230, 200, 60))
        world.blit(img, img.get_rect(center=(tx, ty)))
    elif kind < 0.40:                                                                              # zonnepanelen
        for k in range(3):
            pygame.draw.rect(world, (30, 50, 96), (x0 + 10 + k * 22, y0 + bh - 34, 18, 22))
            pygame.draw.rect(world, (90, 120, 190), (x0 + 10 + k * 22, y0 + bh - 34, 18, 22), 1)
    # neonborden (liggend aan de gevel en staand aan de rand)
    col = random.choice(NEON)
    if random.random() < 0.8:
        jp, lat = random.choice(TK_SIGNS)
        sg = neon_sign(jp, lat, random.choice([15, 17, 19]), col)
        sx, sy = x0 + bw // 2, y0 + bh + fh // 2
        if sg.get_width() > bw:
            sg = pygame.transform.smoothscale(sg, (bw - 4, max(10, int(sg.get_height() * (bw - 4) / sg.get_width()))))
        world.blit(sg, sg.get_rect(center=(sx, sy + 2)))
        add_glow(world, sx, sy, 150, tuple(int(c * 0.30) for c in col), 1.8)
    if random.random() < 0.65 and bh > 70:
        col2 = random.choice(NEON)
        jp, lat = random.choice(TK_SIGNS[:30])
        sg = neon_sign(jp, lat, 17, col2, vertical=True)
        side = random.choice((0, 1))
        sx = x0 - 2 if side == 0 else x0 + bw + 6
        sy = y0 + bh // 2 + random.randint(-12, 12)
        world.blit(sg, sg.get_rect(center=(sx, sy)))
        add_glow(world, sx, sy, 130, tuple(int(c * 0.28) for c in col2), 1.8)


def draw_sakura(world, x, y, r):
    """Kersenbloesemboom (sakura) van bovenaf."""
    pygame.draw.circle(world, (6, 6, 12), (x + 8, y + 10), int(r * 0.95))
    for k in range(7):
        a = TAU * k / 7 + random.uniform(-0.2, 0.2)
        pygame.draw.circle(world, (140, 80, 116), (int(x + math.cos(a) * r * 0.5), int(y + math.sin(a) * r * 0.5)),
                           int(r * 0.55))
    for k in range(6):
        a = TAU * k / 6 + random.uniform(-0.3, 0.3)
        pygame.draw.circle(world, (206, 128, 168), (int(x + math.cos(a) * r * 0.38), int(y + math.sin(a) * r * 0.38)),
                           int(r * 0.42))
    for _ in range(int(r * 1.2)):
        a, d = random.uniform(0, TAU), random.uniform(0, r * 0.85)
        pygame.draw.circle(world, random.choice([(255, 196, 220), (240, 170, 205), (255, 220, 235)]),
                           (int(x + math.cos(a) * d), int(y + math.sin(a) * d)), random.randint(1, 3))


def make_torii(length, ang):
    """Rode torii-poort dwars over de weg (wordt BOVEN de auto's getekend)."""
    length = int(length)
    th = 30
    gate = pygame.Surface((length, th), pygame.SRCALPHA)
    pygame.draw.rect(gate, (24, 10, 12), (0, 7, length, 10))                                      # schaduwkant
    pygame.draw.rect(gate, (196, 30, 34), (0, 4, length, 14), border_radius=3)                    # kasagi
    pygame.draw.rect(gate, (236, 74, 66), (0, 4, length, 4), border_radius=2)
    pygame.draw.rect(gate, (22, 20, 24), (0, 0, length, 5), border_radius=2)                      # zwarte dakrand
    pygame.draw.rect(gate, (170, 24, 30), (length * 0.12, 20, length * 0.76, 6))                  # nuki
    for px in (length * 0.1, length * 0.9):
        pygame.draw.circle(gate, (26, 12, 14), (int(px), 15), 9)
        pygame.draw.circle(gate, (200, 34, 38), (int(px), 14), 8)
        pygame.draw.circle(gate, (240, 90, 80), (int(px) - 2, 12), 3)
    shadow = pygame.Surface(gate.get_size(), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 90))
    gr, sr = pygame.transform.rotate(gate, ang), pygame.transform.rotate(shadow, ang)
    r = gr.get_rect()
    pad = 40
    out = pygame.Surface((r.w + 2 * pad, r.h + 2 * pad), pygame.SRCALPHA)
    out.blit(sr, (pad + 14, pad + 20))
    out.blit(gr, (pad, pad))
    return out


def make_footbridge(length, ang):
    """Voetgangersbrug (歩道橋) met verlichte leuningen, boven de auto's."""
    length, bh = int(length), 30
    deck = pygame.Surface((length, bh), pygame.SRCALPHA)
    deck.fill((74, 78, 92))
    pygame.draw.rect(deck, (130, 136, 152), deck.get_rect(), 2)
    pygame.draw.rect(deck, (60, 220, 255), (0, 0, length, 3))
    pygame.draw.rect(deck, (255, 90, 170), (0, bh - 3, length, 3))
    for x in range(14, length - 20, 26):
        pygame.draw.line(deck, (104, 110, 126), (x, 4), (x, bh - 4), 2)
    shadow = pygame.Surface(deck.get_size(), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 90))
    dr, sr = pygame.transform.rotate(deck, ang), pygame.transform.rotate(shadow, ang)
    r = dr.get_rect()
    pad = 40
    out = pygame.Surface((r.w + 2 * pad, r.h + 2 * pad), pygame.SRCALPHA)
    out.blit(sr, (pad + 16, pad + 22))
    out.blit(dr, (pad, pad))
    return out


def generate_tokyo_centerline(level):
    """Vloeiend drift-circuit: ruime, brede bochten met enkele krappe haarspelden."""
    cfg = TK_LEVELS[level]
    a0 = cfg["A0"]
    for attempt in range(900):
        if attempt and attempt % 90 == 0:
            a0 *= 0.88
        raw = _polar_curve(cfg["K"], a0, cfg["R"])
        if raw is None:
            continue
        pts = _resample(raw, DS)
        if len(pts) < 300 or not _valid(pts, cfg["min_r"], 2 * TK_HALF + 30):
            continue
        return _straightest_start(pts)
    return _straightest_start(_resample(_polar_curve(0, 0, cfg["R"]), DS))


# ------------------------------------------------------------------ circuit-object
class Track:
    def __init__(self, raw, env=0):
        self.env = env
        self.dirt = env == 2
        self.highway = env == ENV_HIGHWAY
        self.tokyo = env == ENV_TOKYO
        self.night = self.tokyo                             # nacht: koplampen altijd aan
        self.half = HW_HALF if self.highway else (TK_HALF if self.tokyo else HALF)   # halve breedte van het asfalt
        self.wall_limit = (self.half - 8) if (self.highway or self.tokyo) else WALL_LIMIT
        self.overlays = []                                  # dingen die BOVEN de auto's getekend worden (viaducten)
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
        self.jumps, self.washboards, self.puddles = [], [], []
        self.jump_at = [False] * n
        self.zone = [0] * n
        self.dzone, self.dzones = [0] * n, []
        if self.dirt:
            self._plan_offroad()
        if self.tokyo:
            self._plan_tokyo()

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
        return self.near(x, y, self.half)

    def lateral(self, x, y, idx):
        """Zijdelingse afstand tot de middenlijn (positief = rechts van de rijrichting)."""
        n = self.n
        p, nr = self.pts[idx % n], self.normals[idx % n]
        return (x - p[0]) * nr[0] + (y - p[1]) * nr[1]

    # ---- tekenen van de hele wereld (1x)
    def render(self):
        if self.env == 1:
            self.render_city()
            return
        if self.env == 2:
            self.render_offroad()
            return
        if self.env == ENV_HIGHWAY:
            self.render_highway()
            return
        if self.env == ENV_TOKYO:
            self.render_tokyo()
            return
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

        self._draw_start(world, ip)

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


    def _draw_start(self, world, ip):
        cols = int(2 * self.half // 12)
        line = pygame.Surface((cols * 12, 24), pygame.SRCALPHA)
        for r in range(2):
            for c in range(cols):
                col = (245, 245, 245) if (r + c) % 2 == 0 else (20, 20, 24)
                pygame.draw.rect(line, col, (c * 12, r * 12, 12, 12))
        rot = pygame.transform.rotate(line, -(math.degrees(self.headings[0]) + 90))
        world.blit(rot, rot.get_rect(center=ip[0]))
        nx, ny = self.normals[0]
        for side in (-1, 1):
            px = int(self.pts[0][0] + nx * side * (self.half + 30))
            py = int(self.pts[0][1] + ny * side * (self.half + 30))
            pygame.draw.circle(world, (0, 0, 0), (px + 4, py + 5), 12)
            pygame.draw.circle(world, (40, 40, 48), (px, py), 12)
            pygame.draw.circle(world, (230, 50, 50), (px, py), 7)
            pygame.draw.circle(world, (255, 255, 255), (px - 2, py - 2), 3)

    # ---- off-road: sprongen, wasbord-stukken en modderpoelen plannen
    def _plan_offroad(self):
        n = self.n
        kap = self.kappa

        def wmax(i, a, b):
            return max(kap[(i + k) % n] for k in range(a, b))

        def gap(i, j):
            return min(abs(i - j), n - abs(i - j))

        # sprongen: op de rechtste stukken, ver uit elkaar en niet bij de start
        cand = sorted((wmax(i, -3, 34), i) for i in range(40, n - 40))
        want = max(2, min(5, n // 140))
        for _, i in cand:
            if len(self.jumps) >= want:
                break
            if all(gap(i, j) >= 90 for j in self.jumps):
                self.jumps.append(i)
        for i in self.jumps:
            self.jump_at[i] = True
        # wasbord (rij kleine hobbels)
        cand = sorted((wmax(i, 0, 10), i) for i in range(40, n - 40))
        for _, i in cand:
            if len(self.washboards) >= 3:
                break
            if all(gap(i, j) >= 60 for j in self.jumps + self.washboards):
                self.washboards.append(i)
        for i in self.washboards:
            for k in range(10):
                self.zone[(i + k) % n] = 1
        # modderpoelen
        tries = 0
        while len(self.puddles) < max(3, n // 55) and tries < 300:
            tries += 1
            i = random.randrange(40, n - 40)
            if any(gap(i, j) < 22 for j in self.jumps + self.washboards):
                continue
            off = random.uniform(-45, 45)
            px = self.pts[i][0] + self.normals[i][0] * off
            py = self.pts[i][1] + self.normals[i][1] * off
            if any(math.hypot(px - q[0], py - q[1]) < 140 for q in self.puddles):
                continue
            self.puddles.append((px, py, random.uniform(36, 54), i))

    def in_mud(self, x, y):
        for px, py, r, _ in self.puddles:
            if (x - px) ** 2 + (y - py) ** 2 < r * r:
                return True
        return False

    def center_dist(self, x, y, idx):
        """Afstand tot de middenlijn (en het dichtstbijzijnde punt) rond punt idx."""
        n, P = self.n, self.pts
        best, bp = 1e18, P[idx % n]
        for k in range(-2, 2):
            a, b = P[(idx + k) % n], P[(idx + k + 1) % n]
            abx, aby = b[0] - a[0], b[1] - a[1]
            t = clamp(((x - a[0]) * abx + (y - a[1]) * aby) / (abx * abx + aby * aby), 0.0, 1.0)
            qx, qy = a[0] + abx * t, a[1] + aby * t
            d = math.hypot(x - qx, y - qy)
            if d < best:
                best, bp = d, (qx, qy)
        return best, bp

    def _off(self, i, d):
        """Punt op afstand d (negatief = links) van de middenlijn bij punt i."""
        n = self.n
        p, nr = self.pts[i % n], self.normals[i % n]
        return (p[0] + nr[0] * d, p[1] + nr[1] * d)

    # ---- off-road wereld tekenen
    def render_offroad(self):
        w, h = self.w, self.h
        world = pygame.Surface((w, h)).convert()
        tile = make_dirt_tile()
        for y in range(0, h, 256):
            for x in range(0, w, 256):
                world.blit(tile, (x, y))
        for _ in range(130):                                        # duinen en kuilen
            r = random.randint(120, 340)
            s = pygame.Surface((2 * r, r), pygame.SRCALPHA)
            c = (236, 172, 104, 22) if random.random() < 0.5 else (120, 70, 34, 26)
            pygame.draw.ellipse(s, c, s.get_rect())
            world.blit(s, (random.randint(0, w) - r, random.randint(0, h) - r // 2))

        n = self.n
        ip = [(int(x), int(y)) for x, y in self.pts]
        for p in ip:
            pygame.draw.circle(world, (178, 114, 60), p, int(HALF + 36))     # opgewaaid stof
        for p in ip:
            pygame.draw.circle(world, (214, 158, 98), p, int(HALF + 10))     # vastgereden baan
        for off, col in ((-34, (190, 132, 78)), (-10, (198, 142, 86)), (14, (190, 132, 78)),
                         (36, (198, 142, 86))):                              # sporen van banden
            for i in range(0, n, 2):
                pygame.draw.line(world, col, self._off(i, off), self._off(i + 1, off), 3)
        for _ in range(n * 3):                                               # kiezels
            i = random.randrange(n)
            pygame.draw.circle(world, random.choice([(188, 130, 76), (226, 172, 112)]),
                               self._off(i, random.uniform(-HALF, HALF)), random.randint(1, 2))

        L = HALF + 2
        for i in self.jumps:                                                 # sprong (hellend vlak)
            for j in range(-3, 3):
                col = (mix((208, 150, 90), (246, 208, 144), (j + 3) / 3) if j < 0
                       else mix((150, 96, 52), (118, 72, 38), j / 2))
                pygame.draw.polygon(world, col, [self._off(i + j, -L), self._off(i + j + 1, -L),
                                                 self._off(i + j + 1, L), self._off(i + j, L)])
            pygame.draw.line(world, (255, 228, 176), self._off(i, -L), self._off(i, L), 4)
            hx, hy = math.cos(self.headings[i % n]), math.sin(self.headings[i % n])
            for m in (-3, -2, -1):                                           # gele pijlen
                px, py = self._off(i + m, 0)
                nx, ny = self.normals[i % n]
                pygame.draw.polygon(world, (255, 214, 60), [(px + hx * 9, py + hy * 9),
                                    (px - hx * 5 + nx * 14, py - hy * 5 + ny * 14),
                                    (px - hx * 5 - nx * 14, py - hy * 5 - ny * 14)])
            for sd in (-1, 1):                                               # pylonnen
                cx, cy = self._off(i - 3, sd * (HALF + 30))
                pygame.draw.circle(world, (60, 40, 28), (int(cx + 3), int(cy + 4)), 8)
                pygame.draw.circle(world, (255, 120, 30), (int(cx), int(cy)), 7)
                pygame.draw.circle(world, (255, 255, 255), (int(cx), int(cy)), 4)
        for i in self.washboards:                                            # wasbord
            for k in range(10):
                pygame.draw.line(world, (150, 96, 50), self._off(i + k, -HALF + 6),
                                 self._off(i + k, HALF - 6), 5)
                a, b = self._off(i + k, -HALF + 6), self._off(i + k, HALF - 6)
                hx, hy = math.cos(self.headings[(i + k) % n]), math.sin(self.headings[(i + k) % n])
                pygame.draw.line(world, (238, 190, 130), (a[0] + hx * 5, a[1] + hy * 5),
                                 (b[0] + hx * 5, b[1] + hy * 5), 3)
        for px, py, r, _ in self.puddles:                                    # modderpoelen
            px, py, r = int(px), int(py), int(r)
            pygame.draw.ellipse(world, (156, 104, 62), (px - r - 6, py - int(r * 0.8) - 6, 2 * r + 12, int(1.6 * r) + 12))
            pygame.draw.ellipse(world, (92, 58, 32), (px - r, py - int(r * 0.8), 2 * r, int(1.6 * r)))
            pygame.draw.ellipse(world, (118, 78, 46), (px - int(r * 0.7), py - int(r * 0.5), int(r * 1.3), int(r * 0.8)))
            pygame.draw.ellipse(world, (176, 140, 108), (px - int(r * 0.5), py - int(r * 0.45), int(r * 0.5), int(r * 0.2)))

        # rood-witte afscheiding (met schaduw)
        for side in (-1, 1):
            for i in range(n):
                sh = [self._off(i, side * (HALF + 4)), self._off(i + 1, side * (HALF + 4)),
                      self._off(i + 1, side * (HALF + 22)), self._off(i, side * (HALF + 22))]
                pygame.draw.polygon(world, (150, 96, 50), [(x + 9, y + 11) for x, y in sh])
        for side in (-1, 1):
            for i in range(n):
                col = (214, 66, 38) if (i // 2) % 2 == 0 else (242, 238, 230)
                pygame.draw.polygon(world, col, [self._off(i, side * (HALF + 4)), self._off(i + 1, side * (HALF + 4)),
                                                 self._off(i + 1, side * (HALF + 22)), self._off(i, side * (HALF + 22))])
                if (i // 2) % 2 == 1:
                    pygame.draw.line(world, (200, 196, 188), self._off(i, side * (HALF + 5)),
                                     self._off(i + 1, side * (HALF + 5)), 2)
        self._draw_start(world, ip)

        # tribunes, banden, palmen en rotsen
        for i, side in ((6, 1), (6, -1), (n // 3, 1), (2 * n // 3, -1)):
            stand = make_stand()
            ang = -math.degrees(self.headings[i % n])
            cx, cy = self._off(i, side * (HALF + 100))
            sh = pygame.Surface(stand.get_size(), pygame.SRCALPHA)
            sh.fill((0, 0, 0, 70))
            shr = pygame.transform.rotate(sh, ang)
            world.blit(shr, shr.get_rect(center=(cx + 10, cy + 12)))
            rot = pygame.transform.rotate(stand, ang)
            world.blit(rot, rot.get_rect(center=(cx, cy)))
        for i in range(10, n, 47):
            for side in (-1, 1):
                if random.random() < 0.5:
                    bx, by = self._off(i, side * (HALF + 36))
                    for k in range(2):
                        pygame.draw.circle(world, (20, 20, 22), (int(bx + 3), int(by + 3 - k * 6)), 11)
                        pygame.draw.circle(world, (46, 46, 52), (int(bx), int(by - k * 6)), 11)
                        pygame.draw.circle(world, (96, 96, 104), (int(bx), int(by - k * 6)), 5)
        for _ in range(int(w * h / 52000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            if not self.near(x, y, HALF + 95):
                draw_palm(world, x, y, random.randint(24, 36))
        for _ in range(int(w * h / 56000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            if not self.near(x, y, HALF + 80):
                draw_rock(world, x, y, random.randint(14, 34))
        self.world = world

    def render_highway(self):
        """Snelweg: 4 rijstroken, vluchtstrook, vangrail, berm met bomen en viaducten."""
        w, h = self.w, self.h
        world = pygame.Surface((w, h)).convert()
        tile = make_grass_tile()
        for y in range(0, h, 256):
            for x in range(0, w, 256):
                world.blit(tile, (x, y))
        for _ in range(140):                                   # zachte kleurvlekken (akkers)
            r = random.randint(160, 400)
            s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
            d = random.randint(-30, 30)
            pygame.draw.circle(s, (60 + d, 140 + d, 60 + d // 2, 26), (r, r), r)
            world.blit(s, (random.randint(0, w) - r, random.randint(0, h) - r))

        n, half, lh = self.n, self.half, HW_LANE_HALF
        ip = [(int(x), int(y)) for x, y in self.pts]
        for p in ip:
            pygame.draw.circle(world, (34, 104, 52), p, int(half + 62))      # talud
        for p in ip:
            pygame.draw.circle(world, (118, 150, 84), p, int(half + 34))     # grasberm
        for p in ip:
            pygame.draw.circle(world, (152, 148, 130), p, int(half + 16))    # grind onder de vangrail
        for p in ip:
            pygame.draw.circle(world, (88, 90, 98), p, int(half))            # vluchtstrook
        for p in ip:
            pygame.draw.circle(world, (60, 62, 70), p, int(lh))              # rijstroken
        for p in ip:                                                         # asfaltkorrel
            for _ in range(9):
                a = random.uniform(0, TAU)
                d = random.uniform(0, half - 4)
                c = random.choice([(70, 72, 80), (52, 54, 61), (78, 80, 88)])
                pygame.draw.circle(world, c, (int(p[0] + math.cos(a) * d),
                                              int(p[1] + math.sin(a) * d)), random.randint(1, 2))
        for lc in HW_LANE_C:                                                 # donkere bandensporen per strook
            for off in (-13, 13):
                for i in range(n):
                    pygame.draw.line(world, (53, 55, 62), self._off(i, lc + off), self._off(i + 1, lc + off), 7)
        for sd in (-1, 1):                                                   # doorgetrokken lijn bij de vluchtstrook
            for i in range(n):
                pygame.draw.line(world, (236, 236, 240), self._off(i, sd * (lh - 3)),
                                 self._off(i + 1, sd * (lh - 3)), 5)
        for k in range(1, HW_LANES):                                         # onderbroken strepen tussen de stroken
            off = (k - HW_LANES / 2) * HW_LANE_W
            for i in range(n):
                if i % 7 < 3:
                    pygame.draw.line(world, (228, 228, 232), self._off(i, off), self._off(i + 1, off), 4)

        self._draw_start(world, ip)

        # vangrail met schaduw, palen en reflectoren
        for sd in (-1, 1):
            rail = [self._off(i, sd * (half + 8)) for i in range(n + 1)]
            for i in range(n):
                a, b = rail[i], rail[i + 1]
                pygame.draw.line(world, (26, 72, 40), (a[0] + 6, a[1] + 7), (b[0] + 6, b[1] + 7), 7)
            for i in range(n):
                pygame.draw.line(world, (170, 176, 186), rail[i], rail[i + 1], 6)
            for i in range(n):
                pygame.draw.line(world, (214, 220, 228), rail[i], rail[i + 1], 2)
            for i in range(0, n, 3):
                pygame.draw.circle(world, (92, 96, 106), (int(rail[i][0]), int(rail[i][1])), 4)
            for i in range(0, n, 12):
                col = (255, 150, 40) if sd < 0 else (245, 245, 245)
                pygame.draw.circle(world, col, (int(rail[i][0]), int(rail[i][1])), 3)

        # viaducten: een kruisende weg waar je onderdoor rijdt (deck wordt BOVEN de auto's getekend)
        sites = []
        cand = sorted((max(self.kappa[(i + k) % n] for k in range(-8, 9)), i) for i in range(70, n - 50))
        for _, i in cand:
            if len(sites) >= 3:
                break
            if all(min(abs(i - j), n - abs(i - j)) >= n // 5 for j in sites):
                sites.append(i)
        reach = half + 96
        strips = []
        for i in sites:
            cx0, cy0 = self.pts[i]
            nx, ny = self.normals[i]
            for sd in (-1, 1):
                d = reach
                while d < reach + 700:
                    if self.near(cx0 + nx * sd * (d + 20), cy0 + ny * sd * (d + 20), half + 30):
                        break
                    d += 20
                if d - reach >= 60:
                    strips.append(((cx0 + nx * sd * reach, cy0 + ny * sd * reach),
                                   (cx0 + nx * sd * d, cy0 + ny * sd * d)))
            ang = -(math.degrees(self.headings[i]) + 90)
            self.overlays.append((make_overpass(2 * reach, ang), (cx0, cy0)))

        def near_strip(x, y, r):
            for (ax, ay), (bx, by) in strips:
                abx, aby = bx - ax, by - ay
                t = clamp(((x - ax) * abx + (y - ay) * aby) / (abx * abx + aby * aby), 0.0, 1.0)
                if math.hypot(x - (ax + abx * t), y - (ay + aby * t)) < r:
                    return True
            return False

        # bomen en struiken (niet op de kruisende wegen)
        for _ in range(int(w * h / 21000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            r = random.randint(26, 52)
            if self.near(x, y, half + 95) or near_strip(x, y, 40 + r):
                continue
            draw_tree(world, x, y, r)
        for _ in range(int(w * h / 70000)):
            x, y = random.randint(20, w - 20), random.randint(20, h - 20)
            if self.near(x, y, half + 75) or near_strip(x, y, 50):
                continue
            pygame.draw.circle(world, (110, 110, 118), (x, y), random.randint(6, 12))
            pygame.draw.circle(world, (150, 150, 158), (x - 2, y - 2), random.randint(3, 6))

        for a, b in strips:                                                  # de kruisende wegen zelf
            pygame.draw.line(world, (70, 100, 60), (a[0] + 7, a[1] + 8), (b[0] + 7, b[1] + 8), 56)
            pygame.draw.line(world, (150, 146, 128), a, b, 56)
            pygame.draw.line(world, (74, 76, 84), a, b, 44)
            L = math.dist(a, b)
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            for k in range(0, int(L) - 20, 36):
                pygame.draw.line(world, (225, 225, 228), (a[0] + ux * k, a[1] + uy * k),
                                 (a[0] + ux * (k + 18), a[1] + uy * (k + 18)), 3)
        self.world = world

    # ---- Tokyo: driftzones plannen (de mooiste bochten geven dubbele punten)
    def _plan_tokyo(self):
        n, kap, H = self.n, self.kappa, self.headings
        self.dzone = [0] * n
        self.dzones = []                                   # (begin, lengte, binnenkant: +1 rechts / -1 links)
        flags = [kap[i] > 1 / 520 for i in range(n)]
        start = next((k for k in range(n) if not flags[k]), None)
        if start is None:
            return
        runs, k = [], 0
        while k < n:
            j = (start + k) % n
            if flags[j]:
                L = 0
                while k + L < n and flags[(start + k + L) % n]:
                    L += 1
                if L >= 12 and 30 < j < n - 60:
                    runs.append((j, L))
                k += L
            else:
                k += 1
        chosen = []
        for a, L in sorted(runs, key=lambda r: -sum(kap[(r[0] + m) % n] for m in range(r[1]))):
            if len(chosen) >= max(3, min(7, n // 130)):
                break
            if all(min(abs(a - b), n - abs(a - b)) >= 50 for b, _ in chosen):
                chosen.append((a, L))
        for zid, (a, L) in enumerate(sorted(chosen), 1):
            inner = 1 if wrap_rad(H[(a + L) % n] - H[a]) > 0 else -1
            self.dzones.append((a, L, inner))
            for m in range(L):
                self.dzone[(a + m) % n] = zid

    # ---- Tokyo bij nacht tekenen
    def render_tokyo(self):
        """Tokyo bij nacht: neonborden, straatlantaarns, Japanse tekens op het asfalt, torii en stegen."""
        w, h, n, half = self.w, self.h, self.n, self.half
        H, kap = self.headings, self.kappa
        world = pygame.Surface((w, h)).convert()
        tile = make_tokyo_tile()
        for y in range(0, h, 256):
            for x in range(0, w, 256):
                world.blit(tile, (x, y))
        ip = [(int(x), int(y)) for x, y in self.pts]
        turn = [1 if wrap_rad(H[(i + 3) % n] - H[i - 3]) > 0 else -1 for i in range(n)]
        ASPH = (40, 42, 54)

        # voetpad, goot en asfalt
        for p in ip:
            pygame.draw.circle(world, (44, 48, 62), p, int(half + 68))
        for p in ip:
            pygame.draw.circle(world, (62, 66, 82), p, int(half + 62))
        for i in range(0, n, 3):                                          # tegelvoegen op het voetpad
            for sd in (-1, 1):
                pygame.draw.line(world, (50, 54, 70), self._off(i, sd * (half + 30)), self._off(i, sd * (half + 60)), 1)
        for p in ip:
            pygame.draw.circle(world, (28, 30, 40), p, int(half + 26))    # goot
        for p in ip:
            pygame.draw.circle(world, ASPH, p, int(half))                 # asfalt
        for p in ip:                                                      # korrel
            for _ in range(6):
                a, d = random.uniform(0, TAU), random.uniform(0, half - 4)
                pygame.draw.circle(world, random.choice([(46, 48, 62), (34, 36, 48), (52, 54, 68)]),
                                   (int(p[0] + math.cos(a) * d), int(p[1] + math.sin(a) * d)), random.randint(1, 2))
        for lane in (-0.5, 0.5):                                          # gepolijste bandensporen
            for off in (-15, 15):
                for i in range(n):
                    pygame.draw.line(world, (35, 37, 49), self._off(i, lane * half + off),
                                     self._off(i + 1, lane * half + off), 9)

        # wegmarkeringen: doorgetrokken witte rand, gele dubbele lijn in bochten, witte streepjes op rechte stukken
        for sd in (-1, 1):
            for i in range(n):
                pygame.draw.line(world, (206, 206, 198), self._off(i, sd * (half - 12)),
                                 self._off(i + 1, sd * (half - 12)), 3)
        for i in range(n):
            if kap[i] > 1 / 600:
                for off in (-3, 3):
                    pygame.draw.line(world, (214, 176, 40), self._off(i, off), self._off(i + 1, off), 3)
            elif i % 8 < 4:
                pygame.draw.line(world, (206, 206, 198), self._off(i, 0), self._off(i + 1, 0), 3)

        def paint(i, off, jp, lat, size, col=(214, 214, 200), stretch=1.9):
            ang = -(math.degrees(H[i % n]) + 90)
            sf = road_paint(jp, lat, size, ang, col, stretch=stretch)
            cx, cy = self._off(i, off)
            world.blit(sf, sf.get_rect(center=(int(cx), int(cy))))

        def lane_poly(i, off, pts, col, width=0):
            """Polygon in 'rijbaan-coordinaten': (zij, voor) -> wereld."""
            hx, hy = math.cos(H[i % n]), math.sin(H[i % n])
            nx, ny = self.normals[i % n]
            cx, cy = self._off(i, off)
            pygame.draw.polygon(world, col, [(cx + nx * u + hx * v, cy + ny * u + hy * v) for u, v in pts], width)

        # rechte stukken voor zebrapad, bruggen en wegtekst
        spots = []
        for thr in (0.0011, 0.0018, 0.003):
            i = 40
            while i < n - 40 and len(spots) < 8:
                if (max(kap[(i + k) % n] for k in range(-12, 13)) < thr and not self.dzone[i]
                        and all(min(abs(i - j), n - abs(i - j)) >= 60 for j in spots)):
                    spots.append(i)
                    i += 60
                else:
                    i += 3
            if len(spots) >= 6:
                break
        kinds = ["cross", "torii", "slow", "stop", "bridge", "speed", "arrows", "cross"]
        sig = []
        for i, kind in zip(spots, kinds):
            if kind == "cross":                                           # zebrapad (横断歩道) + stoplijn + ruiten
                hx, hy = math.cos(H[i]), math.sin(H[i])
                for off in range(-int(half) + 16, int(half) - 10, 24):
                    cx, cy = self._off(i, off)
                    pygame.draw.line(world, (206, 206, 198), (cx - hx * 20, cy - hy * 20), (cx + hx * 20, cy + hy * 20), 13)
                pygame.draw.line(world, (206, 206, 198), self._off(i - 6, -half + 12), self._off(i - 6, half - 12), 6)
                for lane in (-0.5, 0.5):
                    for d in (22, 34):
                        lane_poly(i - d, lane * half, [(0, -18), (11, 0), (0, 18), (-11, 0)], (206, 206, 198), 3)
                paint(i - 52, -0.5 * half, "注意", "CAUTION", 30)
                paint(i - 52, 0.5 * half, "注意", "CAUTION", 30)
                sig.append(i)
            elif kind == "slow":
                paint(i, -0.5 * half, "徐行", "SLOW", 40)
                paint(i, 0.5 * half, "徐行", "SLOW", 40)
            elif kind == "stop":
                pygame.draw.line(world, (206, 206, 198), self._off(i + 22, -half + 12), self._off(i + 22, half - 12), 7)
                paint(i, -0.5 * half, "止まれ", "STOP", 34)
                paint(i, 0.5 * half, "止まれ", "STOP", 34)
            elif kind == "speed":
                paint(i, 0, "スピード落とせ", "SLOW DOWN", 24)
            elif kind == "arrows":
                for lane in (-0.5, 0.5):
                    lane_poly(i, lane * half, [(-5, -34), (5, -34), (5, 8), (16, 8), (0, 34), (-16, 8), (-5, 8)],
                              (206, 206, 198))
                    lane_poly(i + 8, lane * half, [(-5, -34), (5, -34), (5, 8), (16, 8), (0, 34), (-16, 8), (-5, 8)],
                              (206, 206, 198))
            elif kind == "torii":
                self.overlays.append((make_torii(2 * (half + 16), -(math.degrees(H[i]) + 90)), self.pts[i]))
            elif kind == "bridge":
                self.overlays.append((make_footbridge(2 * (half + 54), -(math.degrees(H[i]) + 90)), self.pts[i]))
                for sd in (-1, 1):
                    bx, by = self._off(i, sd * (half + 38))
                    pygame.draw.circle(world, (10, 10, 16), (int(bx + 5), int(by + 6)), 9)
                    pygame.draw.circle(world, (96, 100, 116), (int(bx), int(by)), 9)
        paint(14, -0.5 * half, "スタート", "START", 32, (230, 230, 210))
        paint(14, 0.5 * half, "スタート", "START", 32, (230, 230, 210))
        self._draw_start(world, ip)

        # driftzones: roze 'clipping'-baan aan de binnenkant van de bocht, met pijlen en tekst
        pink = mix(ASPH, (255, 70, 140), 0.34)
        for a, L, inner in self.dzones:
            for m in range(-2, L + 2):
                i = a + m
                c1, c2 = inner * (half - 16), inner * (half - 74)
                pygame.draw.polygon(world, pink, [self._off(i, c1), self._off(i + 1, c1),
                                                  self._off(i + 1, c2), self._off(i, c2)])
                pygame.draw.line(world, (255, 96, 170), self._off(i, c2), self._off(i + 1, c2), 3)
                if m % 5 == 0:
                    lane_poly(i, inner * (half - 45), [(-14, -9), (0, 8), (14, -9), (14, -2), (0, 15), (-14, -2)],
                              (255, 190, 225))
            paint(a - 8, 0, "ドリフトゾーン", "DRIFT ZONE", 24, (255, 150, 205))
            paint(a - 8 + 18, 0, "x2", "x2", 26, (255, 150, 205))

        # betonnen muur met ledstrip; gele/zwarte waarschuwingsstrepen buiten de bochten
        for sd in (-1, 1):
            for i in range(n):
                pygame.draw.line(world, (6, 6, 12), self._off(i, sd * (half + 10)), self._off(i + 1, sd * (half + 10)), 14)
        for sd in (-1, 1):
            for i in range(n):
                pygame.draw.line(world, (126, 132, 150), self._off(i, sd * (half + 9)), self._off(i + 1, sd * (half + 9)), 12)
            for i in range(n):
                pygame.draw.line(world, (176, 182, 200), self._off(i, sd * (half + 9)), self._off(i + 1, sd * (half + 9)), 4)
            for i in range(n):
                led = (60, 226, 255) if (i // 70) % 2 == 0 else (255, 90, 170)
                pygame.draw.line(world, led, self._off(i, sd * (half + 2)), self._off(i + 1, sd * (half + 2)), 2)
        for i in range(0, n, 2):
            if kap[i] > 1 / 640:
                sd = -turn[i]
                col = (240, 196, 30) if (i // 2) % 2 == 0 else (22, 22, 26)
                pygame.draw.polygon(world, col, [self._off(i, sd * (half + 5)), self._off(i + 2, sd * (half + 5)),
                                                 self._off(i + 2, sd * (half + 13)), self._off(i, sd * (half + 13))])

        # gebouwen in een dicht raster (Tokyo is vol!)
        cell, kon = 150, 0
        for gx in range(0, w // cell + 1):
            for gy in range(0, h // cell + 1):
                if random.random() > 0.93:
                    continue
                bw, bh = random.randint(78, 126), random.randint(78, 120)
                x = gx * cell + cell // 2 + random.randint(-10, 10)
                y = gy * cell + cell // 2 + random.randint(-10, 10)
                if self.near(x, y, half + 74 + math.hypot(bw, bh) / 2):
                    continue
                if kon < 3 and bw > 100 and random.random() < 0.06:           # konbini (コンビニ)
                    kon += 1
                    draw_tk_building(world, x, y, bw, bh)
                    add_glow(world, x, y + bh // 2 + 26, 300, (120, 140, 120), 1.6)
                    for k, c in enumerate(((20, 160, 80), (240, 240, 240), (255, 120, 30))):
                        pygame.draw.rect(world, c, (x - bw // 2, y - bh // 2 + 14 + k * 8, bw, 8))
                    sg = neon_sign("コンビニ", "KONBINI", 18, (90, 255, 150))
                    world.blit(sg, sg.get_rect(center=(x, y + bh // 2 + 14)))
                else:
                    draw_tk_building(world, x, y, bw, bh)

        # elektriciteitspalen met draden (電柱), stroomschakelaars en verkeerslichten
        poles = []
        for i in range(0, n, 10):
            sd = 1 if (i // 100) % 2 == 0 else -1
            poles.append((i, sd))
        for k in range(len(poles) - 1):
            (i, sd), (j, sd2) = poles[k], poles[k + 1]
            if sd != sd2:
                continue
            for off in (-9, 0, 9):
                a = self._off(i, sd * (half + 70) + off)
                b = self._off(j, sd * (half + 70) + off)
                mid = ((a[0] + b[0]) / 2 + 2, (a[1] + b[1]) / 2 + 5)
                pygame.draw.line(world, (10, 10, 16), a, mid, 1)
                pygame.draw.line(world, (10, 10, 16), mid, b, 1)
        for i, sd in poles:
            px, py = self._off(i, sd * (half + 70))
            nx, ny = self.normals[i]
            pygame.draw.circle(world, (6, 6, 12), (int(px + 4), int(py + 5)), 6)
            pygame.draw.line(world, (24, 24, 30), (px - nx * 13, py - ny * 13), (px + nx * 13, py + ny * 13), 4)
            pygame.draw.circle(world, (86, 82, 78), (int(px), int(py)), 5)
            if (i // 10) % 6 == 0:                                          # transformator
                pygame.draw.circle(world, (110, 116, 126), (int(px + nx * 7), int(py + ny * 7)), 4)
        for i in sig:                                                      # verkeerslichten bij het zebrapad
            for sd in (-1, 1):
                sx, sy = self._off(i - 10, sd * (half + 36))
                pygame.draw.circle(world, (6, 6, 12), (int(sx + 4), int(sy + 5)), 7)
                pygame.draw.circle(world, (34, 34, 42), (int(sx), int(sy)), 7)
                pygame.draw.circle(world, (255, 70, 60), (int(sx), int(sy)), 4)
                add_glow(world, sx, sy, 90, (170, 30, 24), 1.8)

        # automaten (自動販売機), lantaarns (提灯) en kersenbloesem
        for i in range(15, n, 37):
            sd = random.choice((-1, 1))
            vx, vy = self._off(i, sd * (half + 46))
            col = random.choice([(90, 230, 255), (255, 255, 255), (255, 110, 110)])
            pygame.draw.rect(world, (8, 8, 14), (int(vx - 6), int(vy - 11), 14, 28))
            pygame.draw.rect(world, (28, 30, 40), (int(vx - 7), int(vy - 13), 14, 28), border_radius=2)
            for r in range(3):
                pygame.draw.rect(world, col, (int(vx - 5), int(vy - 11 + r * 8), 10, 6))
            add_glow(world, vx, vy, 110, tuple(int(c * 0.32) for c in col), 1.8)
        for i in range(30, n, 53):
            sd = random.choice((-1, 1))
            for k in range(3):
                lx, ly = self._off(i + k * 2, sd * (half + 42))
                pygame.draw.circle(world, (60, 10, 10), (int(lx + 3), int(ly + 4)), 7)
                pygame.draw.circle(world, (226, 40, 36), (int(lx), int(ly)), 7)
                pygame.draw.circle(world, (255, 150, 110), (int(lx - 2), int(ly - 2)), 3)
                add_glow(world, lx, ly, 100, (150, 30, 20), 1.8)
        sakura = []
        for i in range(10, n, 29):
            sd = random.choice((-1, 1))
            tx, ty = self._off(i, sd * (half + 80))
            if self.near(tx, ty, half + 74):
                continue
            sakura.append((i, tx, ty))
            draw_sakura(world, int(tx), int(ty), random.randint(22, 32))
            for _ in range(26):                                            # bloemblaadjes op het voetpad
                a, d = random.uniform(0, TAU), random.uniform(10, 70)
                pygame.draw.circle(world, random.choice([(190, 120, 160), (214, 150, 186)]),
                                   (int(tx + math.cos(a) * d), int(ty + math.sin(a) * d)), 2)

        # straatlantaarns met warme/koele gloed op het asfalt
        for i in range(6, n, 13):
            sd = 1 if (i // 13) % 2 else -1
            warm = (i // 13) % 5 != 0
            col = (122, 76, 34) if warm else (66, 96, 130)
            hx, hy = self._off(i, sd * (half + 4))
            px, py = self._off(i, sd * (half + 40))
            pygame.draw.line(world, (6, 6, 12), (px + 4, py + 5), (hx + 4, hy + 5), 4)
            pygame.draw.line(world, (46, 48, 58), (px, py), (hx, hy), 3)
            pygame.draw.circle(world, (30, 32, 40), (int(px), int(py)), 5)
            gx, gy = self._off(i, sd * (half - 26))
            add_glow(world, gx, gy, 230, col, 1.9)
            pygame.draw.circle(world, (255, 244, 214) if warm else (226, 240, 255), (int(hx), int(hy)), 5)
            add_glow(world, hx, hy, 46, (200, 170, 120) if warm else (130, 170, 210), 1.5)

        # neonreflecties in het natte asfalt
        for _ in range(n // 3):
            i = random.randrange(n)
            gx, gy = self._off(i, random.uniform(-half + 20, half - 20))
            c = random.choice(NEON)
            add_glow(world, gx, gy, random.randint(70, 130), tuple(int(v * 0.09) for v in c), 1.8)
        self.world = world

    def render_city(self):
        """Stadsomgeving: stoep, gebouwen, zebrapaden en straatlantaarns."""
        w, h = self.w, self.h
        world = pygame.Surface((w, h)).convert()
        tile = make_pavement_tile()
        for y in range(0, h, 256):
            for x in range(0, w, 256):
                world.blit(tile, (x, y))
        ip = [(int(x), int(y)) for x, y in self.pts]
        curvy = [kp > 0.0035 for kp in self.kappa]
        for p in ip:
            pygame.draw.circle(world, (60, 62, 68), p, int(HALF + 46))        # goot
        for p in ip:
            pygame.draw.circle(world, (176, 176, 182), p, int(HALF + 42))     # stoep
        for i, p in enumerate(ip):                                            # stoeprand / kerbs
            if curvy[i] and (i // 2) % 2 == 0:
                col = (214, 40, 40)
            else:
                col = (240, 240, 240)
            pygame.draw.circle(world, col, p, int(HALF + 14))
        for p in ip:
            pygame.draw.circle(world, (50, 52, 58), p, int(HALF))             # asfalt
        for p in ip:
            for _ in range(4):
                a = random.uniform(0, TAU)
                d = random.uniform(0, HALF - 4)
                c = random.choice([(58, 60, 67), (44, 46, 52), (66, 68, 76)])
                pygame.draw.circle(world, c, (int(p[0] + math.cos(a) * d),
                                              int(p[1] + math.sin(a) * d)), random.randint(1, 2))
        for i in range(0, self.n, 8):                                         # witte streep
            pygame.draw.line(world, (205, 205, 210), ip[i], ip[(i + 4) % self.n], 3)
        for i in range(40, self.n - 20, 110):                                 # zebrapaden
            if self.kappa[i] > 0.002:
                continue
            nx, ny = self.normals[i]
            hx, hy = math.cos(self.headings[i]), math.sin(self.headings[i])
            for off in range(-int(HALF) + 12, int(HALF) - 8, 20):
                cx, cy = self.pts[i][0] + nx * off, self.pts[i][1] + ny * off
                pygame.draw.line(world, (225, 225, 228), (cx - hx * 16, cy - hy * 16),
                                 (cx + hx * 16, cy + hy * 16), 9)
        self._draw_start(world, ip)

        # gebouwen in een rooster, ver genoeg van de weg
        cell = 200
        for gx in range(0, w // cell + 1):
            for gy in range(0, h // cell + 1):
                if random.random() > 0.86:
                    continue
                bw, bh = random.randint(80, 150), random.randint(80, 150)
                x = gx * cell + cell // 2 + random.randint(-15, 15)
                y = gy * cell + cell // 2 + random.randint(-15, 15)
                if self.near(x, y, HALF + 125 + max(bw, bh) / 2):
                    continue
                draw_building(world, x, y, bw, bh)
        # straatlantaarns en bomen langs de stoep
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 235, 160, 70), (20, 20), 20)
        for i in range(12, self.n, 16):
            side = 1 if (i // 16) % 2 else -1
            lx = self.pts[i][0] + self.normals[i][0] * side * (HALF + 30)
            ly = self.pts[i][1] + self.normals[i][1] * side * (HALF + 30)
            world.blit(glow, (lx - 20, ly - 20))
            pygame.draw.circle(world, (45, 45, 52), (int(lx), int(ly)), 5)
            pygame.draw.circle(world, (255, 240, 190), (int(lx), int(ly)), 3)
        for i in range(20, self.n, 31):
            side = -1 if (i // 31) % 2 else 1
            tx = self.pts[i][0] + self.normals[i][0] * side * (HALF + 62)
            ty = self.pts[i][1] + self.normals[i][1] * side * (HALF + 62)
            draw_tree(world, int(tx), int(ty), random.randint(14, 20))
        self.world = world


def make_overpass(length, ang):
    """Brugdek (lange as dwars op de snelweg) met schaduw. Wordt boven de auto's getekend."""
    length, bh = int(length), 48
    deck = pygame.Surface((length, bh), pygame.SRCALPHA)
    deck.fill((158, 160, 168))
    pygame.draw.rect(deck, (118, 120, 130), deck.get_rect(), 3)
    pygame.draw.rect(deck, (214, 216, 222), (0, 0, length, 7))
    pygame.draw.rect(deck, (214, 216, 222), (0, bh - 7, length, 7))
    pygame.draw.rect(deck, (96, 98, 108), (0, 7, length, 2))
    pygame.draw.rect(deck, (96, 98, 108), (0, bh - 9, length, 2))
    for x in range(10, length - 20, 30):
        pygame.draw.line(deck, (236, 236, 240), (x, bh // 2), (x + 16, bh // 2), 3)
    shadow = pygame.Surface(deck.get_size(), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 85))
    deck_r = pygame.transform.rotate(deck, ang)
    sh_r = pygame.transform.rotate(shadow, ang)
    r = deck_r.get_rect()
    pad = 44
    out = pygame.Surface((r.w + 2 * pad, r.h + 2 * pad), pygame.SRCALPHA)
    out.blit(sh_r, (pad + 16, pad + 22))                       # schaduw valt altijd naar rechtsonder
    out.blit(deck_r, (pad, pad))
    return out


def make_dirt_tile(size=256):
    t = pygame.Surface((size, size))
    t.fill((198, 134, 72))
    for _ in range(2400):
        d = random.randint(-16, 16)
        c = (clamp(198 + d, 0, 255), clamp(134 + d, 0, 255), clamp(72 + d // 2, 0, 255))
        pygame.draw.circle(t, c, (random.randrange(size), random.randrange(size)), random.randint(1, 3))
    for _ in range(26):                                                      # droge scheuren
        x, y = random.randrange(size), random.randrange(size)
        for _ in range(3):
            nx, ny = x + random.randint(-14, 14), y + random.randint(-14, 14)
            pygame.draw.line(t, (166, 106, 56), (x, y), (nx, ny), 1)
            x, y = nx, ny
    return t


def draw_palm(world, x, y, r):
    pygame.draw.circle(world, (160, 104, 56), (x + 9, y + 11), int(r * 0.7))
    for k in range(8):
        a = TAU * k / 8 + random.uniform(-0.15, 0.15)
        ca, sa = math.cos(a), math.sin(a)
        tip = (x + ca * r, y + sa * r)
        mid = (x + ca * r * 0.5, y + sa * r * 0.5)
        pw = r * 0.2
        pygame.draw.polygon(world, (30, 104, 44), [(x, y), (mid[0] - sa * pw, mid[1] + ca * pw),
                                                   tip, (mid[0] + sa * pw, mid[1] - ca * pw)])
        mid2 = (x + ca * r * 0.55, y + sa * r * 0.55)
        pygame.draw.polygon(world, (62, 150, 64), [(x, y), (mid2[0] - sa * pw * 0.4, mid2[1] + ca * pw * 0.4),
                                                   (x + ca * r * 0.92, y + sa * r * 0.92),
                                                   (mid2[0] + sa * pw * 0.4, mid2[1] - ca * pw * 0.4)])
    pygame.draw.circle(world, (96, 62, 30), (x, y), 5)


def draw_rock(world, x, y, r):
    n = random.randint(6, 8)
    pts = []
    for k in range(n):
        a = TAU * k / n + random.uniform(-0.2, 0.2)
        rad = r * random.uniform(0.7, 1.0)
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
    pygame.draw.polygon(world, (156, 102, 56), [(px + 8, py + 10) for px, py in pts])
    pygame.draw.polygon(world, (124, 122, 118), pts)
    for k in range(n):
        shade = (166, 164, 158) if k < n // 3 else ((124, 122, 118) if k < 2 * n // 3 else (92, 90, 90))
        pygame.draw.polygon(world, shade, [(x, y), pts[k], pts[(k + 1) % n]])


def make_stand(w=240, h=76):
    """Tribune (lange kant langs de x-as)."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (186, 186, 192), (0, 14, w, h - 14))
    for k in range(0, w, 20):
        pygame.draw.rect(s, (214, 66, 38) if (k // 20) % 2 == 0 else (242, 238, 230), (k, 0, 20, 16))
    for row in range(3):
        y = 22 + row * 17
        pygame.draw.rect(s, (60, 86, 150), (6, y, w - 12, 14), border_radius=3)
        for k in range(8, w - 10, 11):
            pygame.draw.circle(s, random.choice([(250, 200, 80), (240, 90, 90), (240, 240, 240),
                                                 (90, 200, 120), (120, 160, 255)]), (k, y + 6), 4)
    pygame.draw.rect(s, (70, 70, 80), s.get_rect(), 2)
    return s


def make_pavement_tile(size=256):
    t = pygame.Surface((size, size))
    t.fill((104, 106, 112))
    for _ in range(1800):
        d = random.randint(-10, 10)
        c = (clamp(104 + d, 0, 255), clamp(106 + d, 0, 255), clamp(112 + d, 0, 255))
        pygame.draw.circle(t, c, (random.randrange(size), random.randrange(size)), random.randint(1, 2))
    for k in range(0, size, 64):
        pygame.draw.line(t, (88, 90, 96), (k, 0), (k, size), 2)
        pygame.draw.line(t, (88, 90, 96), (0, k), (size, k), 2)
    return t


def draw_building(world, x, y, bw, bh):
    x0, y0 = x - bw // 2, y - bh // 2
    sh = pygame.Surface((bw + 30, bh + 30), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 85), (14, 16, bw, bh), border_radius=4)
    world.blit(sh, (x0, y0))
    base = random.choice([(150, 120, 105), (120, 128, 145), (160, 160, 168),
                          (140, 100, 92), (110, 125, 120), (175, 160, 130)])
    dark = tuple(int(c * 0.65) for c in base)
    light = tuple(min(255, int(c * 1.12)) for c in base)
    pygame.draw.rect(world, dark, (x0, y0, bw, bh), border_radius=4)
    pygame.draw.rect(world, base, (x0 + 4, y0 + 4, bw - 8, bh - 8), border_radius=3)
    pygame.draw.rect(world, light, (x0 + 12, y0 + 12, bw - 24, bh - 24), border_radius=3)
    for _ in range(random.randint(1, 3)):                                   # airco's / dakkapellen
        ux, uy = random.randint(x0 + 16, x0 + bw - 36), random.randint(y0 + 16, y0 + bh - 36)
        pygame.draw.rect(world, (130, 134, 142), (ux, uy, 18, 14), border_radius=2)
        pygame.draw.rect(world, (80, 84, 92), (ux + 3, uy + 3, 12, 8), border_radius=2)


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


def panel(surf, rect, alpha=150, radius=16, border=True, tint=(10, 14, 22), edge=(255, 255, 255, 40)):
    r = pygame.Rect(rect)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*tint, alpha), s.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(s, edge, s.get_rect(), 2, border_radius=radius)
    surf.blit(s, r.topleft)


def apanel(surf, rect, alpha=185, radius=12):
    """Paneel in de arena-stijl (zwart met oranje rand)."""
    panel(surf, rect, alpha, radius, True, (14, 9, 5), (255, 140, 30, 110))


# kleurenthema's voor knoppen (normaal en arena)
THEME_DEFAULT = dict(base=(32, 24, 34), hover=(62, 30, 46), sel=(74, 28, 46), dis=(24, 20, 26),
                     border=(90, 62, 76), hover_border=(255, 130, 160), accent=(235, 50, 95),
                     dis_text=(110, 100, 112), field=(18, 24, 38), field_border=(80, 92, 120),
                     fill=(46, 98, 190))
THEME_ARENA = dict(base=(30, 20, 12), hover=(84, 46, 10), sel=(104, 54, 8), dis=(20, 14, 9),
                   border=(120, 80, 36), hover_border=(255, 190, 50), accent=(255, 160, 20),
                   dis_text=(112, 96, 80), field=(22, 14, 8), field_border=(150, 100, 40),
                   fill=(214, 96, 14))


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
        pygame.draw.line(s, (int(48 - 40 * t), int(8 - 5 * t), int(20 - 12 * t)), (0, y), (W, y))
    stripes = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(-2, 9):
        x = i * 220
        pygame.draw.polygon(stripes, (255, 70, 110, 9),
                            [(x, 0), (x + 90, 0), (x + 90 - 360, H), (x - 360, H)])
    s.blit(stripes, (0, 0))
    return s


# ------------------------------------------------------------------ auto-uiterlijk
ART = None            # wordt gevuld in make_assets()


class CarArt:
    """Laadt de auto's uit cars_sheet.png (neus naar rechts) en levert varianten."""

    def __init__(self):
        if not os.path.exists(SHEET_FILE):
            print("\nFOUT: cars_sheet.png niet gevonden.\n"
                  "Zet cars_sheet.png in dezelfde map als dit bestand:\n  " + os.path.dirname(SHEET_FILE))
            pygame.quit()
            sys.exit(1)
        sheet = pygame.image.load(SHEET_FILE).convert_alpha()
        self.base = []
        for i in range(NUM_CARS):
            col, row = i % SHEET_COLS, i // SHEET_COLS
            cell = sheet.subsurface((col * CELL_W, row * CELL_H, CELL_W, CELL_H)).copy()
            self.base.append(cell.subsurface(cell.get_bounding_rect()).copy())
        self.cache = {}

    def _get(self, key, make):
        if key not in self.cache:
            if len(self.cache) > 400:
                self.cache.clear()
            self.cache[key] = make()
        return self.cache[key]

    def big(self, model, tint=0):
        """Auto op volle grootte (voor de garage en het podium)."""
        def make():
            img = self.base[model]
            if tint == 0:
                return img
            shift = tint / TINT_STEPS
            out = img.copy()
            w, h = out.get_size()
            for y in range(h):
                for x in range(w):
                    r, g, b, a = out.get_at((x, y))
                    if a == 0:
                        continue
                    hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                    if ss > 0.30 and vv > 0.2:
                        r2, g2, b2 = colorsys.hsv_to_rgb((hh + shift) % 1.0, ss, vv)
                        out.set_at((x, y), (int(r2 * 255), int(g2 * 255), int(b2 * 255), a))
            return out
        return self._get(("big", model, tint), make)

    def sprite(self, model, tint=0):
        """Auto op racegrootte (48 tot 64 px lang)."""
        def make():
            big = self.big(model, tint)
            k = clamp(big.get_width() * 0.34, 48, 64) / big.get_width()
            return pygame.transform.smoothscale(
                big, (max(8, round(big.get_width() * k)), max(8, round(big.get_height() * k))))
        return self._get(("spr", model, tint), make)

    def thumb(self, model):
        """Kleine staande afbeelding voor de keuzelijst in de garage."""
        def make():
            big = self.base[model]
            k = min(50 / big.get_height(), 74 / big.get_width())
            small = pygame.transform.smoothscale(
                big, (max(4, round(big.get_width() * k)), max(4, round(big.get_height() * k))))
            return pygame.transform.rotate(small, 90)
        return self._get(("thumb", model), make)

    def color(self, model, tint=0):
        """Overheersende (meest verzadigde) kleur, voor minimap en lijsten."""
        def make():
            small = pygame.transform.smoothscale(self.big(model, tint), (24, 12))
            best, bs = None, -1.0
            tot = [0, 0, 0, 0]
            for y in range(12):
                for x in range(24):
                    r, g, b, a = small.get_at((x, y))
                    if a < 200:
                        continue
                    tot[0] += r; tot[1] += g; tot[2] += b; tot[3] += 1
                    hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                    sc = ss * vv
                    if sc > bs:
                        best, bs = (r, g, b), sc
            if best is None or bs < 0.12:                       # grijs / wit / zwart
                n = max(1, tot[3])
                return (tot[0] // n, tot[1] // n, tot[2] // n)
            return best
        return self._get(("col", model, tint), make)


# ------------------------------------------------------------------ geluid
SR = 22050


class Sfx:
    """Alle geluiden worden hier zelf gesynthetiseerd: je hebt geen geluidsbestanden nodig.
    Lukt het starten van het geluid niet (geen audioapparaat), dan blijft het spel gewoon stil."""
    N_ENG = 8
    CH_ENG, CH_SKID, CH_DIRT, CH_BOTS, CH_RAIN, N_RES = 0, 8, 9, 10, 11, 12

    def __init__(self):
        self.ok = False
        self.volume = 0.7
        self.paused = False
        self.snd = {}
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512, allowedchanges=0)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(self.N_RES)
            self.chs = [pygame.mixer.Channel(i) for i in range(self.N_RES)]
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    # ---- synthese
    @staticmethod
    def _sound(samples):
        pk = max(abs(v) for v in samples) or 1.0
        k = 0.95 / pk if pk > 0.95 else 1.0                     # niet laten oversturen
        arr = array("h", [int(clamp(v * k, -1.0, 1.0) * 30000) for v in samples])
        return pygame.mixer.Sound(buffer=arr.tobytes())

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
        self.rng = random.Random(7)
        tp = TAU
        # motor: 8 lussen met stijgende toonhoogte (we mengen er tussen)
        N = 5512
        base_noise = self._noise(N, 0.5)
        self.eng = []
        for k in range(self.N_ENG):
            f = 38 * (235 / 38) ** (k / (self.N_ENG - 1))
            cyc = max(1, round(f * N / SR))
            buf = []
            for i in range(N):
                ph = tp * cyc * i / N
                v = (math.sin(ph) * 0.5 + math.sin(2 * ph) * 0.32 + math.sin(3 * ph) * 0.2
                     + math.sin(4 * ph) * 0.12 + math.sin(5 * ph + 0.5) * 0.08 + base_noise[i] * 0.07)
                buf.append(math.tanh(v * 1.4) * 0.55)
            self.eng.append(self._sound(buf))
        # bandenkrijs (loop, 0,5 s)
        N2 = SR // 2
        nz = self._noise(N2, 0.7)
        self.skid = self._sound([0.3 * math.sin(tp * 1400 * i / SR + 3 * math.sin(tp * 8 * i / SR))
                                 + 0.18 * math.sin(tp * 2100 * i / SR) + 0.25 * nz[i] for i in range(N2)])
        # zand/gravel (loop, 1 s)
        N3 = SR
        d = self._lowpass(self._noise(N3), 0.12)
        d = self._lowpass(d, 0.5)
        self.dirt = self._sound([clamp(v * 7.0, -1, 1) * 0.6 for v in d])
        # regen (loop, 1 s)
        r = self._noise(N3)
        lp = self._lowpass(r, 0.25)
        self.rain = self._sound([(r[i] - lp[i]) * 0.5 for i in range(N3)])

        sn = {}

        def mk(dur, fn):
            return self._sound([fn(i / SR) for i in range(int(SR * dur))])

        nz1 = self._noise(SR, 0.6)
        nz2 = self._noise(SR, 0.2)
        nz3 = self._noise(SR, 0.9)

        def n_at(buf, t):
            return buf[int(t * SR) % len(buf)]

        sn["hit"] = mk(0.35, lambda t: math.sin(tp * 70 * t) * math.exp(-t * 18) * 0.8
                       + math.sin(tp * 380 * t) * math.exp(-t * 35) * 0.25 + n_at(nz1, t) * math.exp(-t * 16) * 0.6)
        sn["bump"] = mk(0.22, lambda t: math.sin(tp * 55 * t) * math.exp(-t * 22) * 0.9
                        + n_at(nz2, t) * math.exp(-t * 20) * 1.2)

        def thud_fn():
            ph = [0.0]

            def f(t):
                fr = 110 - 70 * min(1.0, t / 0.3)
                ph[0] += tp * fr / SR
                return math.sin(ph[0]) * math.exp(-t * 8) * 0.9 + n_at(nz2, t) * math.exp(-t * 14) * 1.4
            return f
        sn["thud"] = mk(0.45, thud_fn())

        def jump_fn():
            ph = [0.0]

            def f(t):
                ph[0] += tp * (160 + 260 * t / 0.45) / SR
                e = math.sin(math.pi * t / 0.45)
                return math.sin(ph[0]) * 0.3 * e + (n_at(nz3, t) - n_at(nz1, t)) * 0.35 * e
            return f
        sn["jump"] = mk(0.45, jump_fn())

        def boost_fn():
            ph = [0.0]

            def f(t):
                ph[0] += tp * (90 + 110 * t) / SR
                e = min(1.0, t / 0.06) * math.exp(-t * 2.6)
                return (n_at(nz3, t) - n_at(nz1, t)) * 0.8 * e + math.sin(ph[0]) * 0.25 * e
            return f
        sn["boost"] = mk(0.9, boost_fn())

        def splash(t):
            v = n_at(nz1, t) * math.exp(-t * 6) * 0.9
            for t0, fr in ((0.08, 620), (0.18, 840), (0.3, 520)):
                if t > t0:
                    v += math.sin(tp * fr * (t - t0)) * math.exp(-(t - t0) * 40) * 0.3
            return v
        sn["splash"] = mk(0.55, splash)
        sn["beep"] = mk(0.2, lambda t: math.sin(tp * 440 * t) * min(1, t * 80) * math.exp(-t * 6) * 0.7)
        sn["go"] = mk(0.5, lambda t: (math.sin(tp * 880 * t) + 0.4 * math.sin(tp * 1320 * t))
                      * min(1, t * 80) * math.exp(-t * 4) * 0.55)
        sn["lap"] = mk(0.4, lambda t: (math.sin(tp * 660 * t) if t < 0.15 else math.sin(tp * 880 * t))
                       * math.exp(-(t % 0.15 if t < 0.15 else t - 0.15) * 9) * 0.6)
        notes = (523.0, 659.0, 784.0, 1047.0)

        def fanfare(t):
            k = min(3, int(t / 0.16))
            lt = t - k * 0.16
            return (math.sin(tp * notes[k] * lt) + 0.3 * math.sin(tp * notes[k] * 2 * lt)) \
                * min(1, lt * 120) * math.exp(-lt * (5 if k < 3 else 2.5)) * 0.5
        sn["finish"] = mk(0.9, fanfare)
        sn["click"] = mk(0.06, lambda t: math.sin(tp * 1000 * t) * math.exp(-t * 70) * 0.7)
        self.snd = sn

    # ---- afspelen
    def play(self, name, vol=1.0):
        if self.ok and self.volume > 0 and name in self.snd:
            snd = self.snd[name]
            snd.set_volume(min(1.0, vol * self.volume))
            snd.play()

    def start_loops(self, wet=False):
        if not self.ok:
            return
        self.stop_loops()
        for k in range(self.N_ENG):
            self.chs[self.CH_ENG + k].play(self.eng[k], loops=-1)
            self.chs[self.CH_ENG + k].set_volume(0)
        self.chs[self.CH_SKID].play(self.skid, loops=-1)
        self.chs[self.CH_DIRT].play(self.dirt, loops=-1)
        self.chs[self.CH_BOTS].play(self.eng[3], loops=-1)
        self.chs[self.CH_RAIN].play(self.rain, loops=-1)
        for c in (self.CH_SKID, self.CH_DIRT, self.CH_BOTS, self.CH_RAIN):
            self.chs[c].set_volume(0)
        self.paused = False

    def stop_loops(self):
        if self.ok:
            for ch in self.chs:
                ch.stop()

    def set_paused(self, flag):
        self.paused = flag
        if flag and self.ok:
            for ch in self.chs:
                ch.set_volume(0)

    def loops(self, rpm, power, boosting, skid, dirt, bots, rain):
        """Geluiden die continu doorlopen; waarden tussen 0 en 1."""
        if not self.ok or self.paused:
            return
        v = self.volume
        p = clamp(rpm, 0, 1) * (self.N_ENG - 1)
        base = (0.2 + 0.45 * power) * (1.3 if boosting else 1.0)
        for k in range(self.N_ENG):
            self.chs[self.CH_ENG + k].set_volume(min(1.0, max(0.0, 1 - abs(k - p)) * base * v))
        self.chs[self.CH_SKID].set_volume(min(1.0, skid * 0.5 * v))
        self.chs[self.CH_DIRT].set_volume(min(1.0, dirt * 0.7 * v))
        self.chs[self.CH_BOTS].set_volume(min(1.0, bots * 0.35 * v))
        self.chs[self.CH_RAIN].set_volume(min(1.0, rain * 0.3 * v))


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
        self.color = ART.color(look["model"], look["tint"])
        self.idx = idx
        self.progress = idx - track.n          # negatief: nog voor de startlijn
        self.laps = 0
        self.lap_times = []
        self.last_lap_t = 0.0
        self.finished = False
        self.finish_time = None
        self.slip = 0.0
        self.on_road = True
        self.mud = False
        self.was_mud = False
        self.z = 0.0                 # hoogte boven de grond (sprongen)
        self.air_t = self.air_T = self.air_h = 0.0
        self.rattle = 0.0            # trillen over wasbord
        self.drift_score = 0         # Tokyo: gebankte driftpunten
        self.drift_chain = 0.0       # punten van de lopende drift-keten (nog niet gebankt)
        self.drift_t = 0.0           # hoelang al aan het driften (hoger = meer multiplier)
        self.drift_gap = 0.0         # tijd sinds de laatste drift (de keten loopt af)
        self.drift_flicks = 0        # wissels links/rechts in de keten (elk +1 multiplier)
        self.drift_dir = 0
        self.drift_ang = 0.0         # huidige slijphoek (rad)
        self.drift_best = 0          # beste gebankte keten
        self.drift_flash = [0, 99.0, 0]   # [punten, leeftijd, soort: 1 gebankt / 2 mislukt / 3 wissel]
        self.last_idx = idx
        self.sprite = ART.sprite(look["model"], look["tint"])
        self.shadow = pygame.mask.from_surface(self.sprite).to_surface(
            setcolor=(0, 0, 0, 95), unsetcolor=(0, 0, 0, 0))

    @property
    def forward_speed(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    @property
    def drift_mult(self):
        return min(6, 1 + int(self.drift_t // 2.5) + self.drift_flicks)

    def physics(self, track, dt, throttle, brake, steer, hand=False, boost=False, grip_mult=1.0):
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        vf = self.vx * fx + self.vy * fy
        grip_turn = clamp(vf / 140, -1, 1)
        turn = TURN_RATE * self.turn * (1 - TURN_LOSS * min(1, abs(vf) / self.vmax))
        air = self.air_T > 0
        self.heading += steer * turn * grip_turn * dt * (((1.35 if track.tokyo else 1.25) if hand else 1.0)) * (0.35 if air else 1.0)

        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        vf = self.vx * fx + self.vy * fy
        vl = self.vx * rx + self.vy * ry

        on = track.on_road(self.x, self.y)
        mud = (not air) and track.dirt and track.in_mud(self.x, self.y)
        self.mud = mud
        boosting = bool(boost and throttle and self.nitro > 0 and not air)
        if boosting:
            self.nitro = max(0.0, self.nitro - NITRO_USE * dt)
        else:
            self.nitro = min(self.nitro_cap, self.nitro + NITRO_REGEN * dt)
        self.boosting = boosting
        accel = self.accel * (1.7 if boosting else 1.0)
        vmax = self.vmax * (1.2 if boosting else 1.0)
        acc = accel * (1.0 if on else 0.55)
        if track.dirt:
            acc *= 0.92
        if mud:
            acc *= 0.6
        if air:
            acc = 0.0
            brake = False
        if throttle:
            vf += acc * dt
        self.braking = bool(brake and vf > 20)
        if brake:
            if vf > 20:
                vf -= BRAKE * dt
            else:
                vf -= acc * 0.5 * dt
        drag = accel / vmax + (0 if on else 1.6) + (1.1 if mud else 0.0)
        if air:
            drag = 0.05
        vf -= vf * drag * dt
        if not throttle and not brake and not air:
            vf -= math.copysign(min(abs(vf), 90 * dt), vf)
        if hand:
            vf -= vf * (0.3 if track.tokyo else 0.7) * dt
        vf = max(vf, -self.vmax * 0.3)
        grip = (12.0 if on else 6.0) * grip_mult
        if track.dirt:
            grip = 7.5 * grip_mult          # los zand: je glijdt sneller weg
        if mud:
            grip = 3.0 * grip_mult
        if track.tokyo:                       # Tokyo: glad asfalt, de auto breekt makkelijk uit
            grip = (7.2 if on else 4.0) * grip_mult
            if throttle and not air:
                grip *= 1 - 0.28 * abs(steer) * min(1.0, abs(vf) / 260)   # gas + sturen: de achterkant komt los
            elif not air:
                grip *= 1.35                                               # gas los: de grip komt terug
        if hand:
            grip = 3.4 * grip_mult if track.tokyo else 2.5
        if air:
            grip = 0.8
        vl0 = vl
        vl *= math.exp(-grip * dt)
        if track.tokyo and not air:           # een slip houdt snelheid vast (powerslide)
            m1, m2 = math.hypot(vf, vl0), math.hypot(vf, vl)      # snelheid voor / na het wegvallen van de zijgrip
            mt = m2 + (m1 - m2) * 0.65                              # 65% van dat verlies blijft behouden
            vf = math.copysign(math.sqrt(max(0.0, mt * mt - vl * vl)), vf if vf else 1.0)

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

    def draw(self, screen, cx, cy, night=False):
        if not (-90 < self.x - cx < W + 90 and -90 < self.y - cy < H + 90):
            return
        ang = -math.degrees(self.heading)
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        z = self.z
        lift = z * 0.55                                           # sprong: auto omhoog en iets groter
        jit = random.uniform(-1.3, 1.3) if self.rattle > 0 else 0.0
        sh = pygame.transform.rotozoom(self.shadow, ang, max(0.6, 1 - z / 300))
        if z > 0:
            sh.set_alpha(int(255 * max(0.35, 1 - z / 120)))
        screen.blit(sh, sh.get_rect(center=(self.x - cx + 7 + z * 0.25, self.y - cy + 9 + z * 0.25)))
        sp = pygame.transform.rotozoom(self.sprite, ang, 1 + z / 110)
        ox, oy = self.x - cx, self.y - cy - lift + jit
        screen.blit(sp, sp.get_rect(center=(ox, oy)))
        if night and self.is_player and "neon" in GLOW:         # neon onderverlichting
            screen.blit(GLOW["neon"], GLOW["neon"].get_rect(center=(ox, oy)), special_flags=pygame.BLEND_RGB_ADD)
        if (self.braking or night) and "red" in GLOW:           # remlichten (bij nacht ook achterlichten)
            g = GLOW["red"] if self.braking else GLOW.get("red_dim", GLOW["red"])
            for s in (-1, 1):
                px = ox - fx * 27 + rx * s * 9
                py = oy - fy * 27 + ry * s * 9
                screen.blit(g, g.get_rect(center=(px, py)), special_flags=pygame.BLEND_RGB_ADD)
        if self.boosting and "blue" in GLOW:                    # nitro-gloed
            g = GLOW["blue"]
            screen.blit(g, g.get_rect(center=(ox - fx * 34, oy - fy * 34)), special_flags=pygame.BLEND_RGB_ADD)


def collide(a, b, r=40):
    """Botsing tussen twee auto's. Geeft de botssterkte terug (0 = geen botsing)."""
    if abs(a.z - b.z) > 14:
        return 0.0
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy) or 0.001
    if d >= r:
        return 0.0
    nx, ny = dx / d, dy / d
    push = (r - d) / 2
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


# ------------------------------------------------------------------ verkeer (snelweg)
CIV_ACC = 120          # burgerauto's trekken rustig op
CIV_DEC = 380          # en remmen stevig als ze iets voor zich krijgen


class Civilian(Car):
    """Burgerauto op de snelweg: blijft in zijn eigen rijstrook en rijdt met een vaste snelheid.
    Is een obstakel: zwaarder dan de racers, dus een botsing kost jou snelheid."""

    def __init__(self, track, s, lane, cruise, model, tint):
        L = track.n * DS
        super().__init__(track, int(s // DS) % track.n, HW_LANE_C[lane], dict(model=model, tint=tint),
                         dict(vmax=cruise, accel=CIV_ACC), "Verkeer")
        self.lane = lane
        self.lane_off = HW_LANE_C[lane]
        self.s = s % L                 # afstand langs de middenlijn (px)
        self.cruise = cruise
        self.v = cruise
        self.lat = self.lat_v = 0.0    # zijwaartse uitwijking na een botsing (veert terug)
        self.yaw = self.yaw_v = 0.0    # draai na een botsing (veert terug)
        self.place(track, 0.0)
        self.vx, self.vy = math.cos(self.heading) * cruise, math.sin(self.heading) * cruise

    def place(self, track, dt):
        n, L = track.n, track.n * DS
        u = (self.s % L) / DS
        i = int(u) % n
        f = u - int(u)
        a, b = track.pts[i], track.pts[(i + 1) % n]
        h0, h1 = track.headings[i], track.headings[(i + 1) % n]
        hd = h0 + wrap_rad(h1 - h0) * f
        off = self.lane_off + self.lat
        x = a[0] + (b[0] - a[0]) * f - math.sin(hd) * off
        y = a[1] + (b[1] - a[1]) * f + math.cos(hd) * off
        if dt > 0:
            self.vx, self.vy = (x - self.x) / dt, (y - self.y) / dt
        self.x, self.y = x, y
        self.heading = hd + self.yaw

    def step(self, track, dt, target):
        dv = target - self.v
        self.v = clamp(self.v + clamp(dv, -CIV_DEC * dt, CIV_ACC * dt), 0.0, 600.0)
        self.braking = dv < -12
        self.s = (self.s + self.v * dt) % (track.n * DS)
        self.lat_v += (-14.0 * self.lat - 7.0 * self.lat_v) * dt
        self.lat = clamp(self.lat + self.lat_v * dt, -46.0, 46.0)
        self.yaw_v += (-40.0 * self.yaw - 9.0 * self.yaw_v) * dt
        self.yaw = clamp(self.yaw + self.yaw_v * dt, -1.0, 1.0)
        self.place(track, dt)


CIV_A, CIV_B = 50.0, 31.0      # halve lengte / breedte van het botsvlak (ellips, in de rijrichting van de burgerauto)


def collide_civ(car, civ):
    """Botsing racer <-> burgerauto. De burgerauto is 3x zo zwaar: de racer krijgt de klap.
    Het botsvlak is een ellips langs de rijrichting: langs elkaar rijden in naastliggende
    stroken is veilig, achterop rijden niet. Geeft de botssterkte terug (0 = geen botsing)."""
    if abs(car.z - civ.z) > 14:
        return 0.0
    dx, dy = car.x - civ.x, car.y - civ.y                # van de burgerauto naar de racer
    if abs(dx) > 60 or abs(dy) > 60:
        return 0.0
    hx, hy = math.cos(civ.heading - civ.yaw), math.sin(civ.heading - civ.yaw)
    u = dx * hx + dy * hy                                # langs de rijrichting
    v = -dx * hy + dy * hx                               # opzij (rechts = positief)
    e = (u / CIV_A) ** 2 + (v / CIV_B) ** 2
    if e >= 1.0:
        return 0.0
    r = math.hypot(u, v)
    if r < 1e-3:
        gu, gv, over = 0.0, 1.0, CIV_B
    else:
        gu, gv = u / CIV_A ** 2, v / CIV_B ** 2          # normaal op de ellips
        gl = math.hypot(gu, gv)
        gu, gv = gu / gl, gv / gl
        over = r * (1 / math.sqrt(e) - 1)                # hoe diep zit de racer erin
    nx, ny = gu * hx - gv * hy, gu * hy + gv * hx        # wereldrichting: burgerauto -> racer
    along = nx * hx + ny * hy
    side = -nx * hy + ny * hx
    car.x += nx * over * 0.85
    car.y += ny * over * 0.85
    civ.s -= along * over * 0.15
    civ.lat -= side * over * 0.15
    rel = (car.vx - civ.vx) * nx + (car.vy - civ.vy) * ny
    if rel >= 0:
        return 0.0
    j = -(1 + 0.3) * rel / (1 + 1 / 3)
    car.vx += nx * j
    car.vy += ny * j
    civ.v = clamp(civ.v - along * j / 3, 0.0, 600.0)     # zetje langs de weg...
    civ.lat_v -= side * j / 3                            # ...opzij...
    civ.yaw_v -= side * j * 0.012                        # ...en een draaitje
    return -rel


def spawn_traffic(track, count):
    """Zet `count` burgerauto's op de snelweg. Linkerstrook = snel, rechterstrook = langzaam."""
    L = track.n * DS
    speeds = [(285, 345), (240, 300), (200, 260), (160, 215)]            # per strook (px/s), links -> rechts
    combos = [(random.choice(CIVIL_MODELS), random.choice([0, 0, 5, 10, 14, 19])) for _ in range(14)]
    civs = []
    tries = 0
    while len(civs) < count and tries < 6000:
        tries += 1
        lane = random.choices(range(HW_LANES), weights=[2, 3, 3, 3])[0]
        s = random.uniform(0, L)
        if s / DS > track.n - 90 or s / DS < 70:                # start/grid vrijhouden
            continue
        ok, close = True, 0
        for c in civs:
            ds = abs((c.s - s + L / 2) % L - L / 2)
            if ds < 110:
                close += 1
            if (c.lane == lane and ds < 260) or (abs(c.lane - lane) == 1 and ds < 110):
                ok = False
                break
        if not ok or close >= 2:                                 # geen muur van auto's over de hele weg
            continue
        lo, hi = speeds[lane]
        model, tint = random.choice(combos)
        civs.append(Civilian(track, s, lane, random.uniform(lo, hi), model, tint))
    return civs


# ------------------------------------------------------------------ AI-bot
class AIDriver:
    def __init__(self, car, track, cfg, skill, others, target, wet, civs=()):
        self.car, self.track, self.cfg = car, track, cfg
        self.others = others           # alle andere auto's (om uit te wijken)
        self.target = target           # de speler (voor inhaalhulp / afremmen)
        self.civs = civs               # burgerauto's (alleen op de snelweg)
        self.line_off = random.uniform(-38, 38)
        self.stuck = 0.0
        self.hw = track.highway
        self.hw_clear = True           # rij ik vrij? (dan mag nitro)
        if self.hw:
            lat = track.lateral(car.x, car.y, car.idx)
            self.lane = min(range(HW_LANES), key=lambda k: abs(HW_LANE_C[k] - lat))
            self.hw_off = lat
            self.lane_cd = 0.0
            self.jit = random.uniform(-3, 3)
        vmax = car.base_vmax
        n = track.n
        corner = cfg["ai_corner"] * (1 - (1 - skill) * 0.8) * (0.93 if wet else 1.0)
        if track.dirt:
            corner *= 0.88                         # los zand: minder grip
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

    def _highway(self, vf, dt):
        """Snelweg: kies een rijstrook zonder verkeer, wissel van strook en rem als het niet anders kan.
        Geeft een maximale snelheid terug (of None) en zet self.line_off."""
        c, t = self.car, self.track
        n, L = t.n, t.n * DS
        s_c = c.idx * DS
        lat_c = t.lateral(c.x, c.y, c.idx)
        look = 200 + max(vf, 0.0) * 0.75                    # hoe ver we vooruit kijken (px)
        obs = []                                            # (afstand vooruit, zijdelings, snelheid)
        for o in self.civs:
            ds = (o.s - s_c + L / 2) % L - L / 2
            if -80 < ds < look + 80:
                obs.append((ds, o.lane_off + o.lat, o.v))
        for o in self.others:
            ds = ((o.idx - c.idx + n // 2) % n - n // 2) * DS
            if -80 < ds < look + 80:
                obs.append((ds, t.lateral(o.x, o.y, o.idx), max(o.forward_speed, 0.0)))

        def lane_free(lc):                                  # vrije afstand vooruit in deze strook
            sc = look
            for ds, lat, ov in obs:
                if ds > -5 and abs(lat - lc) < 34 and (vf - ov > 15 or ds < 110):
                    sc = min(sc, ds)
            return sc

        def lane_enterable(lc):                             # is er plek om hierheen te sturen?
            for ds, lat, ov in obs:
                if abs(lat - lc) < 36 and -75 < ds < 110 + max(0.0, vf - ov) * 0.5:
                    return False
            return True

        self.lane_cd = max(0.0, self.lane_cd - dt)
        sc = [lane_free(lc) for lc in HW_LANE_C]
        cur = self.lane
        if sc[cur] < look * 0.92 and self.lane_cd <= 0:     # mijn strook is niet vrij: zoek een betere
            best = max(range(HW_LANES), key=lambda k: sc[k] - 25 * abs(k - cur) + (60 if k == cur else 0))
            if best != cur:
                nxt = cur + (1 if best > cur else -1)       # steeds een strook tegelijk
                if lane_enterable(HW_LANE_C[nxt]):
                    self.lane, self.lane_cd = nxt, 0.45
        goal = HW_LANE_C[self.lane]
        stp = 170 * dt
        self.hw_off += clamp(goal - self.hw_off, -stp, stp)
        self.line_off = self.hw_off + self.jit
        self.hw_clear = sc[self.lane] >= look * 0.92

        cap = None                                          # veilige snelheid: kunnen we nog op tijd stoppen?
        for ds, lat, ov in obs:
            if ds > 0 and (abs(lat - lat_c) < 32 or abs(lat - self.hw_off) < 32):
                gap = ds - 66 - 0.12 * ov                   # we willen minstens zoveel afstand houden
                v = ov * 0.5 if gap <= 0 else ov + math.sqrt(2 * BRAKE * 0.4 * gap)
                cap = v if cap is None else min(cap, v)
        return cap

    def control(self, dt=1 / 60):
        c, t, cfg = self.car, self.track, self.cfg
        vf = c.forward_speed
        hw_cap = self._highway(vf, dt) if self.hw else None
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
        if hw_cap is not None:
            target = min(target, hw_cap)
        if not c.on_road:
            target *= 0.8
        boost = False
        if (cfg["nitro"] and c.nitro > 30 and self.straight[c.idx] and abs(diff) < 0.15
                and c.on_road and not slow_for_car and self.hw_clear):
            boost = True
            target = c.base_vmax * 1.18
        throttle = vf < target
        brake = vf > target * 1.06 or slow_for_car
        if hw_cap is not None and vf > hw_cap + 6:        # verkeer vlak voor je: direct remmen
            throttle, brake = False, True
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
    def __init__(self, raw, level, opts, car_cfg, field, grid, sfx=None):
        self.sfx = sfx
        self.level = level
        cfg = self.cfg = LEVELS[level]
        self.laps = opts["laps"]
        self.wet = bool(opts["weather"])
        self.grip = 0.72 if self.wet else 1.0
        self.track = Track(raw, int(opts.get("env", 0)))
        self.track.render()
        t = self.track
        self.tokyo = t.tokyo
        self.civs = spawn_traffic(t, int(opts.get("traffic", 0))) if t.highway else []
        self.crashes = 0               # botsingen van de speler met verkeer
        self._crash_cd = 0.0

        info = {"Jij": (dict(model=car_cfg["model"], tint=car_cfg["tint"]),
                        car_params(car_cfg["stats"]), 1.0)}
        for f in field:
            look = dict(model=f["model"], tint=0)
            prm = dict(vmax=cfg["ai_vmax"] * f["skill"], accel=BASE_ACCEL, turn=1.0, nitro=100)
            info[f["name"]] = (look, prm, f["skill"])

        self.cars = []
        for slot, name in enumerate(grid):
            if t.highway:                                   # snelweg: 4 naast elkaar, een per rijstrook
                row, col = divmod(slot, HW_LANES)
                idx = t.n - 6 - 5 * row - (2 if col % 2 else 0)
                off = HW_LANE_C[col]
            else:
                row, col = divmod(slot, 2)
                idx = t.n - 6 - 5 * row - (2 if col else 0)
                off = 30 if col else -30
            look, prm, _ = info[name]
            self.cars.append(Car(t, idx, off, look, prm, name, name == "Jij"))
        self.player = next(c for c in self.cars if c.is_player)
        self.drivers = []
        for c in self.cars:
            if not c.is_player:
                others = [o for o in self.cars if o is not c]
                self.drivers.append(AIDriver(c, t, cfg, info[c.name][2], others, self.player, self.wet, self.civs))

        self.minimap = MiniMap(t.pts, 240, 200)
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        self.top = pygame.Surface((W, H), pygame.SRCALPHA)
        self.mark = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(self.mark, (60, 36, 18, 95) if t.dirt else ((0, 0, 0, 150) if t.tokyo else (10, 10, 12, 70)),
                           (3, 3), 3)
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
        self._cd_last = 4
        self.rpm, self.power, self._thr = 0.2, 0.15, False
        self.splats = []
        self._splat_t = 0.0
        if sfx:
            sfx.start_loops(self.wet)
        self.cam_x = clamp(self.player.x - W / 2, 0, t.w - W)
        self.cam_y = clamp(self.player.y - H / 2, 0, t.h - H)
        self.dial = make_dial(200)

    # ---- hulpjes
    def ranking(self):
        if self.tokyo:                                     # Tokyo: wie het meeste gedrift heeft wint
            return sorted(self.cars, key=lambda c: (-self.drift_total(c), -c.progress))
        return sorted(self.cars, key=lambda c: (0, c.finish_time) if c.finished else (1, -c.progress))

    def drift_total(self, c):
        return c.drift_score + int(c.drift_chain * c.drift_mult)

    def _bank(self, c):
        """Zet de lopende drift-keten op de score."""
        pts = int(c.drift_chain * c.drift_mult)
        c.drift_score += pts
        c.drift_best = max(c.drift_best, pts)
        if c.is_player and pts >= 150:
            c.drift_flash = [pts, 0.0, 1]
        c.drift_chain, c.drift_t, c.drift_flicks, c.drift_dir, c.drift_gap = 0.0, 0.0, 0, 0, 0.0

    def _fail(self, c):
        """Muur geraakt: de lopende keten is weg."""
        pts = int(c.drift_chain * c.drift_mult)
        if c.is_player and pts >= 150:
            c.drift_flash = [pts, 0.0, 2]
        c.drift_chain, c.drift_t, c.drift_flicks, c.drift_dir, c.drift_gap = 0.0, 0.0, 0, 0, 0.0

    def _drift(self, c, dt):
        """Tokyo: punten voor driften = snelheid x slijphoek. Dubbel in een driftzone, wissel = bonus."""
        speed = math.hypot(c.vx, c.vy)
        ang, sgn = 0.0, 0
        if speed > 150 and c.forward_speed > 40 and c.on_road and c.air_T == 0 and not c.finished:
            d = wrap_rad(math.atan2(c.vy, c.vx) - c.heading)
            ang, sgn = abs(d), (1 if d > 0 else -1)
        c.drift_ang = ang
        if 0.2 < ang < 1.45 and speed > 170:
            c.drift_gap = 0.0
            if c.drift_dir and sgn != c.drift_dir and ang > 0.25 and c.drift_chain > 0:
                c.drift_flicks += 1
                c.drift_chain += 120 * c.drift_mult
                if c.is_player:
                    c.drift_flash = [0, 0.0, 3]
            c.drift_dir = sgn
            c.drift_t += dt
            zone = 2.0 if self.track.dzone[c.idx] else 1.0
            c.drift_chain += speed * min(ang, 1.0) * 1.6 * zone * dt
        elif c.drift_chain > 0:
            c.drift_gap += dt
            if c.drift_gap > 0.8:
                self._bank(c)

    def say(self, title, sub="", col=(255, 255, 255)):
        self.banner = [title, sub, col, 0.0]

    def visible(self, car, m=100):
        return (abs(car.x - (self.cam_x + W / 2)) < W / 2 + m
                and abs(car.y - (self.cam_y + H / 2)) < H / 2 + m)

    def respawn(self, car):
        """Zet een auto terug op de weg. Op de snelweg: in het midden van een strook, niet op verkeer."""
        t = self.track
        if not t.highway:
            car.respawn(t)
            return
        lat = t.lateral(car.x, car.y, car.idx)
        k = min(range(HW_LANES), key=lambda k: abs(HW_LANE_C[k] - lat))
        step, i, x, y = 0, car.idx, car.x, car.y
        for step in range(0, 66, 3):
            i = (car.idx + step) % t.n
            p, nr = t.pts[i], t.normals[i]
            x, y = p[0] + nr[0] * HW_LANE_C[k], p[1] + nr[1] * HW_LANE_C[k]
            if (all(math.hypot(v.x - x, v.y - y) > 120 for v in self.civs)
                    and all(o is car or math.hypot(o.x - x, o.y - y) > 60 for o in self.cars)):
                break
        car.idx = i
        car.progress += step
        car.x, car.y = x, y
        car.heading = t.headings[i]
        car.vx = car.vy = 0.0

    def spawn(self, x, y, vx, vy, life, size, col, kind=0):
        self.particles.append([x, y, vx, vy, 0.0, life, size, col, kind])

    # ---- logica
    def update(self, dt, keys):
        dt = min(dt, 0.05)
        t, p = self.track, self.player
        if self.state == "countdown":
            self.countdown -= dt
            n_cd = math.ceil(max(self.countdown, 0))
            if n_cd != self._cd_last:
                self._cd_last = n_cd
                if self.sfx and n_cd in (1, 2, 3):
                    self.sfx.play("beep")
            if self.countdown <= 0:
                self.state, self.go_t = "race", 1.2
                if self.sfx:
                    self.sfx.play("go")
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
            self._thr = bool(thr)
            p.physics(t, dt, thr, brk, steer, hand, boost, self.grip)
            for d in self.drivers:
                a_thr, a_brk, a_steer, a_boost = d.control(dt)
                d.car.physics(t, dt, a_thr, a_brk, a_steer, False, a_boost, self.grip)
            if self.civs:
                self._traffic(dt)

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
                            if self.sfx:
                                self.sfx.play("hit", clamp(imp / 220, 0.3, 1.0))
                        elif self.sfx and self.visible(a):
                            self.sfx.play("hit", clamp(imp / 400, 0.1, 0.4))

            if self.civs:                                           # racers <-> verkeer
                self._crash_cd = max(0.0, self._crash_cd - dt)
                for v in self.civs:
                    for c in cars:
                        if abs(v.x - c.x) > 44 or abs(v.y - c.y) > 44:
                            continue
                        imp = collide_civ(c, v)
                        if imp <= 20:
                            continue
                        if self.visible(c):
                            mx, my = (c.x + v.x) / 2, (c.y + v.y) / 2
                            for _ in range(int(min(16, imp / 10))):
                                ang = random.uniform(0, TAU)
                                sp = random.uniform(80, 300)
                                self.spawn(mx, my, math.cos(ang) * sp, math.sin(ang) * sp,
                                           random.uniform(0.2, 0.5), random.uniform(2, 3.5),
                                           random.choice([(255, 220, 110), (255, 160, 60), (240, 240, 235)]), 1)
                        if c.is_player:
                            self.shake = max(self.shake, min(9, imp * 0.045))
                            if imp > 35 and self._crash_cd <= 0:
                                self.crashes += 1
                                self._crash_cd = 0.6
                            if self.sfx:
                                self.sfx.play("hit", clamp(imp / 220, 0.3, 1.0))
                        elif self.sfx and self.visible(c):
                            self.sfx.play("hit", clamp(imp / 400, 0.1, 0.4))

            for c in cars:
                c.update_progress(t)
                laps = max(0, int(c.progress // t.n))
                if laps > c.laps:
                    c.laps = laps
                    lt = self.time - c.last_lap_t
                    c.last_lap_t = self.time
                    c.lap_times.append(lt)
                    if c.is_player and self.sfx and laps < self.laps:
                        self.sfx.play("lap")
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
            if t.dirt:
                for c in cars:
                    self._offroad(c, dt)
            elif t.highway or t.tokyo:
                for c in cars:
                    self._wall(c)
            if self.tokyo:
                for c in cars:
                    self._drift(c, dt)
                    c.drift_flash[1] += dt
            for c in cars:
                self._effects(c, dt, c.is_player and hand)

            # bots die vastzitten terugzetten
            for d in self.drivers:
                a = d.car
                if math.hypot(a.vx, a.vy) < 35:
                    d.stuck += dt
                    if d.stuck > 2.0:
                        self.respawn(a)
                        d.stuck = 0
                else:
                    d.stuck = 0

            if p.boosting and not self._was_boost:
                self.shake = max(self.shake, 3.5)
                if self.sfx:
                    self.sfx.play("boost")
            self._was_boost = p.boosting
            if not p.on_road and math.hypot(p.vx, p.vy) > 200:
                self.shake = max(self.shake, 1.6)

            if p.finished and self.state == "race":
                self.state = "finished"
                if self.tokyo:
                    for c in self.cars:
                        if c.drift_chain > 0:
                            self._bank(c)
                self.say("FINISH!", "", (255, 220, 70))
                if self.sfx:
                    self.sfx.play("finish")

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
        self.particles = [q for q in self.particles if q[4] < q[5]][-700:]
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

        # modderspatten op het scherm van de speler
        if p.mud:
            self._splat_t -= dt
            if self._splat_t <= 0:
                self._splat_t = 0.06
                self.splats.append([random.uniform(160, W - 160), random.uniform(120, H - 120),
                                    random.uniform(14, 46), 0.0])
        for sp in self.splats:
            sp[3] += dt
        self.splats = [sp for sp in self.splats if sp[3] < 2.2][-40:]
        self._audio(dt)

        # camera
        tx = p.x + p.vx * 0.28 - W / 2
        ty = p.y + p.vy * 0.28 - H / 2
        k = min(1, dt * 5)
        self.cam_x = clamp(self.cam_x + (tx - self.cam_x) * k, 0, t.w - W)
        self.cam_y = clamp(self.cam_y + (ty - self.cam_y) * k, 0, t.h - H)

    def _traffic(self, dt):
        """Burgerauto's: rij je strook, houd afstand tot de auto voor je en rem als er een racer voor je staat."""
        t = self.track
        L = t.n * DS
        racers = [(c.idx * DS, t.lateral(c.x, c.y, c.idx), max(c.forward_speed, 0.0)) for c in self.cars]
        lanes = {}
        for v in self.civs:
            lanes.setdefault(v.lane, []).append(v)
        for lst in lanes.values():
            lst.sort(key=lambda v: v.s)
            m = len(lst)
            for k, v in enumerate(lst):
                target = v.cruise
                need = 96 + v.v * 0.5                       # gewenste afstand tot de auto voor je
                if m > 1:
                    ah = lst[(k + 1) % m]
                    d = (ah.s - v.s) % L
                    if d < need:
                        target = min(target, max(0.0, ah.v - (need - d) * 1.5))
                for rs, rlat, rv in racers:
                    d = (rs - v.s) % L
                    if 0 < d < need and abs(rlat - v.lane_off - v.lat) < 30:
                        target = min(target, max(0.0, rv - (need - d) * 1.5))
                v.step(t, dt, target)

    def _audio(self, dt):
        sfx = self.sfx
        if not sfx or not sfx.ok:
            return
        p, t = self.player, self.track
        spd = abs(p.forward_speed)
        r = clamp(spd / (p.vmax * 1.1), 0.0, 1.0)
        gears = 5
        g = min(gears - 1, int(r * gears))
        target = 0.22 + 0.78 * (r * gears - g)               # toerental binnen een 'versnelling'
        if self._thr:
            target = max(target, 0.55)
        if p.air_T > 0:
            target = 0.95                                     # in de lucht: motor loeit
        self.rpm += (target - self.rpm) * min(1.0, dt * 9)
        self.power += ((1.0 if self._thr else 0.15) - self.power) * min(1.0, dt * 8)
        airborne = p.air_T > 0
        skid = clamp((p.slip - 60) / 140, 0.0, 1.0) if (p.on_road and not airborne) else 0.0
        if t.dirt:
            skid *= 0.35
        dirt = 0.0
        if not airborne and (t.dirt or not p.on_road):
            dirt = clamp(spd / 450, 0.0, 1.0)
            if p.mud:
                dirt = 1.0
        near = 0.0
        for c in self.cars:
            if not c.is_player:
                d = math.hypot(c.x - p.x, c.y - p.y)
                near = max(near, clamp(1 - d / 700, 0, 1) * clamp(math.hypot(c.vx, c.vy) / 300, 0.3, 1.0))
        for v in self.civs:
            near = max(near, clamp(1 - math.hypot(v.x - p.x, v.y - p.y) / 500, 0, 1) * 0.6)
        sfx.loops(self.rpm, self.power, p.boosting, skid, dirt, near, 1.0 if self.wet else 0.0)

    def _launch(self, c, spd):
        c.air_T = clamp(spd / 700, 0.3, 0.7)
        c.air_t = 0.0
        c.air_h = 24 + spd * 0.06
        for _ in range(8):
            ang = random.uniform(0, TAU)
            self.spawn(c.x, c.y, math.cos(ang) * 90, math.sin(ang) * 90,
                       random.uniform(0.4, 0.8), random.uniform(5, 9), (208, 156, 100))
        if self.sfx:
            if c.is_player:
                self.sfx.play("jump")
            elif self.visible(c):
                self.sfx.play("jump", 0.35)

    def _land(self, c):
        T = c.air_T
        c.air_T = c.air_t = c.z = 0.0
        c.vx *= 0.94
        c.vy *= 0.94
        for _ in range(14):
            ang = random.uniform(0, TAU)
            sp = random.uniform(60, 170)
            self.spawn(c.x, c.y, math.cos(ang) * sp, math.sin(ang) * sp,
                       random.uniform(0.5, 0.9), random.uniform(5, 10), (208, 156, 100))
        for _ in range(6):
            ang = random.uniform(0, TAU)
            sp = random.uniform(100, 240)
            self.spawn(c.x, c.y, math.cos(ang) * sp, math.sin(ang) * sp,
                       random.uniform(0.3, 0.6), random.uniform(2.5, 4), (120, 78, 42), 1)
        if c.is_player:
            self.shake = max(self.shake, 4 + T * 6)
            if self.sfx:
                self.sfx.play("thud")
            if T > 0.45:
                self.say("SPRONG!", f"{T:.1f} s in de lucht", (255, 200, 90))
        elif self.sfx and self.visible(c):
            self.sfx.play("thud", 0.4)

    def _wall(self, c):
        """Muur / vangrail langs de baan: de auto kaatst terug (alleen op de grond)."""
        t = self.track
        if c.z < 18:                                           # muur (alleen op de grond)
            d, (px, py) = t.center_dist(c.x, c.y, c.idx)
            if d > t.wall_limit:
                nx, ny = (c.x - px) / d, (c.y - py) / d
                c.x, c.y = px + nx * t.wall_limit, py + ny * t.wall_limit
                vn = c.vx * nx + c.vy * ny
                if vn > 0:
                    c.vx -= 1.35 * vn * nx
                    c.vy -= 1.35 * vn * ny
                    c.vx *= 0.97
                    c.vy *= 0.97
                    if self.tokyo and vn > 60:
                        self._fail(c)
                    if vn > 50 and self.visible(c):
                        for _ in range(int(min(8, vn / 20))):
                            ang = random.uniform(0, TAU)
                            sp = random.uniform(60, 200)
                            self.spawn(c.x + nx * 14, c.y + ny * 14, math.cos(ang) * sp - nx * 60,
                                       math.sin(ang) * sp - ny * 60, random.uniform(0.2, 0.4),
                                       random.uniform(2, 3.5), random.choice([(255, 220, 110), (240, 240, 235)]), 1)
                    if c.is_player and vn > 50:
                        self.shake = max(self.shake, min(7, vn * 0.03))
                        if self.sfx:
                            self.sfx.play("bump", clamp(vn / 200, 0.3, 1.0))

    def _offroad(self, c, dt):
        """Muren langs de baan, sprongen, wasbord en modder."""
        t = self.track
        spd = math.hypot(c.vx, c.vy)
        self._wall(c)
        i0, i1 = c.last_idx, c.idx                             # sprongen
        steps = (i1 - i0) % t.n
        if 0 < steps < t.n // 2 and c.air_T == 0 and spd > 150:
            for k in range(1, steps + 1):
                if t.jump_at[(i0 + k) % t.n]:
                    self._launch(c, spd)
                    break
        c.last_idx = i1
        if t.zone[c.idx] == 1 and c.air_T == 0 and spd > 140:   # wasbord: trillen en remmen
            c.rattle = 0.15
            c.vx *= 1 - 0.35 * dt
            c.vy *= 1 - 0.35 * dt
            if c.is_player:
                self.shake = max(self.shake, 1.8)
        c.rattle = max(0.0, c.rattle - dt)
        if c.air_T > 0:
            c.air_t += dt
            u = c.air_t / c.air_T
            if u >= 1:
                self._land(c)
            else:
                c.z = c.air_h * 4 * u * (1 - u)
        if c.mud and not c.was_mud and self.sfx:
            if c.is_player:
                self.sfx.play("splash")
            elif self.visible(c):
                self.sfx.play("splash", 0.3)
        c.was_mud = c.mud

    def _effects(self, car, dt, hand):
        if not self.visible(car, 150):
            return
        t = self.track
        dirt = t.dirt
        grounded = car.air_T == 0
        fx, fy = math.cos(car.heading), math.sin(car.heading)
        rx, ry = -fy, fx
        speed = math.hypot(car.vx, car.vy)
        wheels = [(car.x - fx * 18 + rx * s * 10, car.y - fy * 18 + ry * s * 10) for s in (-1, 1)]
        if grounded and car.slip > (60 if dirt else 72) and car.on_road:        # bandensporen
            for wx, wy in wheels:
                t.world.blit(self.mark, (wx - 3, wy - 3))
        smoke_col = (205, 155, 100) if dirt else ((196, 202, 226) if t.tokyo else (225, 225, 230))
        if grounded and (car.slip > (70 if dirt else 85) or (hand and speed > 150)
                         or (t.tokyo and car.drift_ang > 0.3 and speed > 200)):   # rook / stof bij slippen
            for wx, wy in wheels:
                if random.random() < 0.5:
                    self.spawn(wx, wy, random.uniform(-25, 25), random.uniform(-25, 25),
                               random.uniform(0.5, 0.9), random.uniform(5, 9), smoke_col)
        if (grounded and car.on_road and not dirt and
                ((hand and speed > 200) or (t.tokyo and car.drift_ang > 0.45 and speed > 220))):   # driftvonken
            for wx, wy in wheels:
                if random.random() < 0.35:
                    self.spawn(wx, wy, -fx * 90 + random.uniform(-70, 70),
                               -fy * 90 + random.uniform(-70, 70), random.uniform(0.15, 0.35),
                               random.uniform(1.5, 2.5), (255, 190, 90), 1)
        if grounded and not car.on_road and speed > 90:                         # stof/gras
            for wx, wy in wheels:
                if random.random() < 0.6:
                    self.spawn(wx, wy, random.uniform(-40, 40), random.uniform(-40, 40),
                               random.uniform(0.4, 0.8), random.uniform(5, 10), (150, 130, 90))
        if dirt and grounded and speed > 100 and not car.mud:                   # zand: stofsliert + opgeworpen klonten
            for wx, wy in wheels:
                if random.random() < clamp(speed / 600, 0, 1) * 0.9:
                    self.spawn(wx, wy, random.uniform(-30, 30) - car.vx * 0.1, random.uniform(-30, 30) - car.vy * 0.1,
                               random.uniform(0.5, 0.9), random.uniform(5, 9), (208, 156, 100))
                if car.slip > 55 and random.random() < 0.45:
                    self.spawn(wx, wy, -fx * random.uniform(60, 200) + random.uniform(-80, 80),
                               -fy * random.uniform(60, 200) + random.uniform(-80, 80),
                               random.uniform(0.35, 0.7), random.uniform(2.5, 4), (120, 78, 42), 1)
        if car.mud and speed > 40:                                              # modder: zware spatten
            for wx, wy in wheels:
                for _ in range(2):
                    if random.random() < 0.9:
                        self.spawn(wx, wy, random.uniform(-60, 60), random.uniform(-60, 60),
                                   random.uniform(0.6, 1.0), random.uniform(7, 12), (96, 64, 36))
                if random.random() < 0.7:
                    ang = random.uniform(0, TAU)
                    sp = random.uniform(120, 300)
                    self.spawn(wx, wy, math.cos(ang) * sp, math.sin(ang) * sp, random.uniform(0.4, 0.8),
                               random.uniform(3, 5), (80, 50, 28), 1)
        if self.wet and not dirt and grounded and car.on_road and speed > 200:  # opspattend water
            for wx, wy in wheels:
                if random.random() < 0.4:
                    self.spawn(wx, wy, random.uniform(-30, 30), random.uniform(-30, 30),
                               random.uniform(0.3, 0.6), random.uniform(4, 7), (170, 190, 215))
        if car.boosting:                                        # nitro-vlammen
            ex, ey = car.x - fx * 30, car.y - fy * 30 - car.z * 0.55
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

        for v in self.civs:
            v.draw(screen, cx, cy)
        for c in sorted(self.cars, key=lambda c: (c.z > 0, c.is_player)):
            c.draw(screen, cx, cy, t.night)
        for img, (ox, oy) in t.overlays:                        # viaducten: auto's rijden eronderdoor
            r = img.get_rect(center=(int(ox - cx), int(oy - cy)))
            if r.right > 0 and r.left < W and r.bottom > 0 and r.top < H:
                screen.blit(img, r)

        # bovenlaag: regen, donker, snelheidslijnen
        used = False
        self.top.fill((0, 0, 0, 0))
        if self.wet:
            self.top.fill((8, 14, 34, 34 if t.night else 78))
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
        for sx0, sy0, sr, age in self.splats:                   # modder op het 'scherm'
            a = int(200 * max(0.0, 1 - age / 2.2))
            pygame.draw.ellipse(self.top, (88, 56, 30, a), (sx0 - sr, sy0 - sr * 0.8, sr * 2, sr * 1.6))
            pygame.draw.ellipse(self.top, (60, 38, 20, a), (sx0 - sr * 0.5, sy0 - sr * 0.3, sr, sr * 0.7))
            used = True
        if used:
            screen.blit(self.top, (0, 0))
        if (self.wet or t.night) and "cone" in GLOW:            # koplampen in de regen / bij nacht
            cone = GLOW["cone"]
            for c in (*self.cars, *self.civs):
                if -200 < c.x - cx < W + 200 and -200 < c.y - cy < H + 200:
                    rot = pygame.transform.rotozoom(cone, -math.degrees(c.heading), 1)
                    px = c.x - cx + math.cos(c.heading) * 10
                    py = c.y - cy + math.sin(c.heading) * 10
                    screen.blit(rot, rot.get_rect(center=(px, py)), special_flags=pygame.BLEND_RGB_ADD)

        screen.blit(A["vignette"], (0, 0))
        self._hud(screen, A)

    def _drift_hud(self, screen, f):
        """Tokyo: driftpunten, lopende keten, multiplier en grote melding in het midden."""
        p = self.player
        x0, y0 = 20, H - 226
        panel(screen, (x0, y0, 330, 150), 165, 14)
        text(screen, f["s"], "DRIFT PUNTEN", (x0 + 16, y0 + 10), (160, 175, 200))
        text(screen, f["m"], str(p.drift_score), (x0 + 16, y0 + 30), (255, 220, 70))
        deg = math.degrees(p.drift_ang)
        text(screen, f["s"], f"HOEK {deg:.0f}\u00b0", (x0 + 314, y0 + 10),
             (255, 150, 205) if deg > 12 else (160, 175, 200), "topright")
        if self.track.dzone[p.idx]:
            text(screen, f["s"], "DRIFTZONE  x2", (x0 + 314, y0 + 34), (255, 150, 205), "topright")
        live = int(p.drift_chain * p.drift_mult)
        if p.drift_chain > 0:
            hot = p.drift_gap == 0.0
            col = (255, 120, 200) if hot else (200, 160, 190)
            text(screen, f["s"], "KETEN", (x0 + 16, y0 + 72), (160, 175, 200))
            text(screen, f["m"], f"+{live}", (x0 + 16, y0 + 90), col)
            text(screen, f["l"], f"x{p.drift_mult}", (x0 + 314, y0 + 74), (255, 230, 120), "topright")
            if not hot:                                     # de keten loopt af: drift snel weer door!
                frac = clamp(1 - p.drift_gap / 0.8, 0.0, 1.0)
                pygame.draw.rect(screen, (30, 36, 52), (x0 + 16, y0 + 132, 298, 8), border_radius=4)
                pygame.draw.rect(screen, (255, 120, 200), (x0 + 16, y0 + 132, int(298 * frac), 8), border_radius=4)
        else:
            text(screen, f["s"], "Sla in en glijd door de bocht!", (x0 + 16, y0 + 84), (150, 165, 195))
        if self.state != "race":
            return
        fl = p.drift_flash
        if p.drift_chain > 0 and p.drift_ang > 0.2:
            m = p.drift_mult
            col = [(255, 150, 200), (255, 140, 210), (255, 170, 90), (255, 210, 80), (120, 240, 255), (255, 255, 255)][min(5, m - 1)]
            sh = jp_surf("ドリフト", "DRIFT", 56, (0, 0, 0))
            sh.set_alpha(140)
            img = jp_surf("ドリフト", "DRIFT", 56, col)
            screen.blit(sh, sh.get_rect(midtop=(W // 2 + 3, 127)))
            screen.blit(img, img.get_rect(midtop=(W // 2, 124)))
            text(screen, f["m"], f"x{m}    +{live}", (W // 2, 190), col, "midtop")
        elif fl[1] < 1.6:
            a = clamp((1.6 - fl[1]) / 0.5, 0.0, 1.0)
            msg = {1: (f"+{fl[0]}", "GEBANKT!", (255, 220, 70)), 2: ("MUUR!", f"-{fl[0]} punten kwijt", (255, 90, 80)),
                   3: ("WISSEL!", "multiplier omhoog", (120, 240, 255))}.get(fl[2])
            if msg:
                for k, (s, sz, c) in enumerate(((msg[0], f["l"], msg[2]), (msg[1], f["s"], (230, 235, 245)))):
                    img = sz.render(s, True, c)
                    img.set_alpha(int(255 * a))
                    screen.blit(img, img.get_rect(midtop=(W // 2, 130 + k * 52)))

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
            if self.tokyo:
                text(screen, f["s"], str(self.drift_total(c)), (222, y), col, "topright")

        # midden boven: positie
        medal = [(255, 220, 70), (215, 220, 230), (225, 150, 90)]
        pcol = medal[pos] if pos < 3 else (255, 255, 255)
        panel(screen, (W // 2 - 95, 20, 190, 96))
        text(screen, f["s"], "POSITIE", (W // 2, 28), (160, 175, 200), "midtop")
        text(screen, f["l"], str(pos + 1), (W // 2 - 10, 76), pcol, "midright")
        text(screen, f["m"], f"/{rows}", (W // 2 - 4, 80), (190, 200, 220), "midleft")
        if self.tokyo:
            if pos > 0:
                text(screen, f["s"], f"-{self.drift_total(order[pos - 1]) - self.drift_total(p)} pt",
                     (W // 2, 100), (255, 120, 110), "midtop")
            elif rows > 1:
                text(screen, f["s"], f"+{self.drift_total(p) - self.drift_total(order[1])} pt",
                     (W // 2, 100), (110, 235, 140), "midtop")
        elif pos > 0:
            gap = (order[pos - 1].progress - p.progress) * DS / 10
            text(screen, f["s"], f"-{gap:.0f} m", (W // 2, 100), (255, 120, 110), "midtop")
        elif rows > 1:
            gap = (p.progress - order[1].progress) * DS / 10
            text(screen, f["s"], f"+{gap:.0f} m", (W // 2, 100), (110, 235, 140), "midtop")

        # rechts boven: minimap
        mm = self.minimap
        mx, my = W - 20 - mm.w, 20
        screen.blit(mm.surf, (mx, my))
        for v in self.civs:
            qx, qy = mm.to_map(v.x, v.y)
            pygame.draw.circle(screen, (170, 178, 195), (int(mx + qx), int(my + qy)), 3)
        for c in sorted(self.cars, key=lambda c: c.is_player):
            qx, qy = mm.to_map(c.x, c.y)
            r = 7 if c.is_player else 5
            pygame.draw.circle(screen, (255, 255, 255), (int(mx + qx), int(my + qy)), r + 2)
            pygame.draw.circle(screen, c.color, (int(mx + qx), int(my + qy)), r)

        # links onder: verkeer (snelweg)
        if self.track.highway:
            panel(screen, (20, H - 134, 230, 58), 150, 12)
            text(screen, f["s"], f"VERKEER  {len(self.civs)} auto's", (36, H - 126), (160, 175, 200))
            text(screen, f["s"], f"BOTSINGEN  {self.crashes}", (36, H - 104),
                 (255, 130, 110) if self.crashes else (210, 220, 240))

        if self.tokyo:
            self._drift_hud(screen, f)

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
                text(screen, f["s"], ("Sturen + gas = glijden  -  SPATIE = drift  -  ESC pauze"
                                    if self.tokyo else "Pijltjes/WASD rijden  -  SHIFT nitro  -  SPATIE handrem  -  T terugzetten  -  ESC pauze"),
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
def make_field(n, level, avoid_model):
    """Maak n bots met eigen naam, auto en rijvaardigheid."""
    names = random.sample(BOT_NAMES, n)
    models = random.sample([m for m in range(NUM_CARS) if m != avoid_model], n)
    spread = max(0.012, 0.035 - 0.005 * (level - 1))
    skills = [1 - spread * i - random.uniform(0, 0.008) for i in range(n)]
    random.shuffle(skills)
    return [dict(name=names[i], model=models[i], tint=0, color=ART.color(models[i], 0),
                 skill=skills[i]) for i in range(n)]


# ================================================================== ARENA: monstertrucks en stunts
ARENA_W, ARENA_H, ARENA_M = 3200, 2200, 360      # wereld (incl. tribunes) en breedte van de tribune-rand
GRAV = 950.0                                      # zwaartekracht (px/s^2)
SPIN_RATE = 5.2                                   # draaisnelheid in de lucht (rad/s)
TRUCK_L, TRUCK_H = 150, 112                       # afmeting van het truck-plaatje
TRUCK_HEIGHT = 64                                 # hoogte van de truck (voor de projectie tijdens een flip)
CROWD = [(230, 70, 60), (240, 180, 50), (70, 150, 230), (235, 235, 235), (90, 200, 110), (200, 90, 200)]


def _dark(c, k):
    return mix(c, (0, 0, 0), k)


def _lite(c, k):
    return mix(c, (255, 255, 255), k)


def truck_params(cfg):
    """Vertaal de truck-instellingen naar eigenschappen."""
    s, v, f, n = cfg["stats"]
    w = cfg["wheels"]
    return dict(vmax=330 + 24 * s + 12 * w, accel=330.0, turn=0.95, nitro=60 + 8 * n,
                hop=360 + 34 * v + 25 * w, flip=6.0 + 0.45 * f)


def random_truck_cfg():
    return dict(style=random.randrange(len(TRUCK_STYLES)), color=random.randrange(len(PALETTE)),
                accent=random.randrange(len(ACCENTS)), decal=random.randrange(len(TRUCK_DECALS)),
                wheels=random.randrange(len(TRUCK_WHEELS)), lights=random.randint(0, 1),
                stats=[random.randint(3, 8) for _ in range(4)])


def make_truck_art(cfg):
    """Teken een monstertruck van boven (neus naar rechts). Geeft (bovenkant, onderkant)."""
    body, acc = PALETTE[cfg["color"]], ACCENTS[cfg["accent"]]
    ws = cfg["wheels"]
    wl, ww = (34, 42, 50)[ws], (18, 22, 26)[ws]
    cx, cy = TRUCK_L // 2, TRUCK_H // 2
    off = 24 + ww // 2 - 2

    def wheels(s):
        for ax in (-40, 40):
            for sd in (-1, 1):
                r = pygame.Rect(0, 0, wl, ww)
                r.center = (cx + ax, cy + sd * off)
                pygame.draw.rect(s, (20, 20, 24), r, border_radius=ww // 3)
                for k in range(r.left + 4, r.right - 3, 5):
                    pygame.draw.line(s, (52, 52, 58), (k, r.top + 2), (k, r.bottom - 3), 2)
                pygame.draw.rect(s, (90, 90, 100), r, 2, border_radius=ww // 3)

    top = pygame.Surface((TRUCK_L, TRUCK_H), pygame.SRCALPHA)
    for ax in (-40, 40):                                              # assen
        pygame.draw.rect(top, (44, 44, 50), (cx + ax - 4, cy - off, 8, 2 * off))
    wheels(top)
    dk = _dark(body, 0.4)
    st = cfg["style"]
    if st == 0:                                                       # pickup
        pygame.draw.rect(top, dk, (cx - 51, cy - 26, 102, 52), border_radius=12)
        pygame.draw.rect(top, body, (cx - 49, cy - 24, 98, 48), border_radius=11)
        pygame.draw.rect(top, _lite(body, 0.14), (cx + 10, cy - 21, 37, 42), border_radius=8)
        pygame.draw.rect(top, _dark(body, 0.12), (cx - 26, cy - 21, 34, 42), border_radius=7)
        pygame.draw.rect(top, (28, 38, 54), (cx + 2, cy - 18, 8, 36), border_radius=3)
        pygame.draw.rect(top, (28, 38, 54), (cx - 30, cy - 17, 5, 34), border_radius=2)
        for k in range(-45, -32, 5):
            pygame.draw.line(top, dk, (cx + k, cy - 20), (cx + k, cy + 20), 2)
        lx = cx - 12
    elif st == 1:                                                     # muscle car
        pygame.draw.rect(top, dk, (cx - 52, cy - 24, 104, 48), border_radius=16)
        pygame.draw.rect(top, body, (cx - 50, cy - 22, 100, 44), border_radius=15)
        pygame.draw.rect(top, _lite(body, 0.12), (cx + 6, cy - 19, 42, 38), border_radius=12)
        pygame.draw.rect(top, _dark(body, 0.55), (cx + 16, cy - 9, 22, 18), border_radius=5)
        pygame.draw.rect(top, (28, 38, 54), (cx - 22, cy - 18, 26, 36), border_radius=9)
        pygame.draw.rect(top, _dark(body, 0.15), (cx - 18, cy - 14, 18, 28), border_radius=7)
        pygame.draw.rect(top, acc, (cx - 52, cy - 22, 6, 44), border_radius=3)
        lx = cx - 8
    elif st == 2:                                                     # beast: breed met blower
        pygame.draw.rect(top, dk, (cx - 50, cy - 28, 100, 56), border_radius=8)
        pygame.draw.rect(top, body, (cx - 48, cy - 26, 96, 52), border_radius=7)
        pygame.draw.rect(top, _lite(body, 0.1), (cx + 8, cy - 23, 38, 46), border_radius=5)
        pygame.draw.circle(top, (190, 194, 204), (cx + 26, cy), 12)
        pygame.draw.circle(top, (90, 94, 104), (cx + 26, cy), 12, 3)
        pygame.draw.circle(top, (40, 40, 46), (cx + 26, cy), 5)
        pygame.draw.rect(top, (28, 38, 54), (cx - 8, cy - 20, 14, 40), border_radius=3)
        pygame.draw.rect(top, _dark(body, 0.2), (cx - 34, cy - 22, 26, 44), border_radius=4)
        pygame.draw.rect(top, acc, (cx - 36, cy - 25, 46, 50), 3, border_radius=4)
        lx = cx - 22
    else:                                                             # buggy: open frame
        pygame.draw.rect(top, (40, 40, 46), (cx - 48, cy - 18, 96, 36), border_radius=10)
        pygame.draw.rect(top, body, (cx - 46, cy - 16, 92, 32), border_radius=9)
        pygame.draw.rect(top, _lite(body, 0.15), (cx + 16, cy - 14, 30, 28), border_radius=8)
        pygame.draw.circle(top, (28, 38, 54), (cx - 4, cy), 11)
        pygame.draw.circle(top, (235, 205, 70), (cx - 4, cy), 7)
        pygame.draw.rect(top, (170, 175, 185), (cx - 42, cy - 12, 20, 24), border_radius=4)
        pygame.draw.rect(top, acc, (cx - 20, cy - 23, 38, 46), 3, border_radius=10)
        lx = cx - 12
    hw = 18 if st != 3 else 14                                        # halve breedte van de body (voor stickers)
    d = cfg["decal"]
    if d == 1:                                                        # vlammen
        for sd in (-1, 1):
            pts = [(cx + 46, cy + sd * hw)]
            for k in range(6):
                x = cx + 46 - k * 14
                pts += [(x - 6, cy + sd * (hw - 8 - (k % 2) * 4)), (x - 14, cy + sd * hw)]
            pygame.draw.polygon(top, acc, pts)
    elif d == 2:                                                      # racestrepen
        pygame.draw.rect(top, acc, (cx - 47, cy - 9, 94, 5))
        pygame.draw.rect(top, acc, (cx - 47, cy + 4, 94, 5))
    elif d == 3:                                                      # geblokt
        for sd in (-1, 1):
            y0 = cy - hw if sd < 0 else cy + hw - 5
            for k in range(0, 92, 8):
                col = (240, 240, 240) if (k // 8) % 2 == 0 else (20, 20, 24)
                pygame.draw.rect(top, col, (cx - 46 + k, y0, 8, 5))
    elif d == 4:                                                      # bliksem
        pygame.draw.lines(top, acc, False, [(cx + 44, cy - 11), (cx + 18, cy + 2), (cx + 30, cy + 2),
                                            (cx - 6, cy + 13), (cx + 4, cy + 3), (cx - 6, cy + 3),
                                            (cx - 40, cy - 9)], 4)
    if cfg["lights"]:                                                 # dakverlichting
        pygame.draw.rect(top, (30, 30, 36), (lx - 3, cy - 16, 7, 32), border_radius=2)
        for k in range(-12, 13, 6):
            pygame.draw.circle(top, (255, 244, 160), (lx, cy + k), 2)
    for sd in (-1, 1):                                                # koplampen
        pygame.draw.circle(top, (255, 250, 205), (cx + 48, cy + sd * 13), 3)

    under = pygame.Surface((TRUCK_L, TRUCK_H), pygame.SRCALPHA)       # onderkant (als hij op zijn kop ligt)
    pygame.draw.rect(under, (46, 48, 56), (cx - 50, cy - 22, 100, 44), border_radius=8)
    pygame.draw.rect(under, (74, 76, 86), (cx - 50, cy - 22, 100, 44), 2, border_radius=8)
    for ln in (-14, 14):
        pygame.draw.line(under, (30, 32, 38), (cx - 48, cy + ln), (cx + 48, cy + ln), 4)
    pygame.draw.line(under, (84, 86, 96), (cx - 40, cy), (cx + 40, cy), 5)
    pygame.draw.rect(under, (120, 92, 62), (cx - 12, cy + 15, 42, 5))
    pygame.draw.rect(under, acc, (cx - 8, cy - 20, 16, 6))
    for ax in (-40, 40):
        pygame.draw.rect(under, (96, 98, 108), (cx + ax - 3, cy - off, 6, 2 * off))
        pygame.draw.circle(under, (116, 118, 128), (cx + ax, cy), 8)
    wheels(under)
    return top.convert_alpha(), under.convert_alpha()


class TruckArt:
    def __init__(self, cfg):
        self.top, self.under = make_truck_art(cfg)
        self.under_f = pygame.transform.flip(self.under, True, False)
        self.scaled = {}
        sh = pygame.Surface((TRUCK_L - 14, TRUCK_H - 28), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 120), sh.get_rect())
        self.shadow = sh

    def proj(self, pitch):
        """Plaatje zoals het er van boven uitziet bij deze stand (flip = korter, op zijn kop = onderkant)."""
        c, s = math.cos(pitch), abs(math.sin(pitch))
        L = max(16, int(abs(c) * TRUCK_L + s * TRUCK_HEIGHT * 0.9))
        key = (c < 0, L // 4)
        img = self.scaled.get(key)
        if img is None:
            if len(self.scaled) > 150:
                self.scaled.clear()
            base = self.under_f if c < 0 else self.top
            img = pygame.transform.smoothscale(base, (max(8, L // 4 * 4), TRUCK_H))
            self.scaled[key] = img
        return img


_TRUCK_ART = {}


def get_truck_art(cfg):
    key = (cfg["style"], cfg["color"], cfg["accent"], cfg["decal"], cfg["wheels"], cfg["lights"])
    if key not in _TRUCK_ART:
        if len(_TRUCK_ART) > 40:
            _TRUCK_ART.clear()
        _TRUCK_ART[key] = TruckArt(cfg)
    return _TRUCK_ART[key]


# ------------------------------------------------------------------ stuntpunten
def flip_name(base, n):
    return base if n == 1 else (f"DUBBELE {base}" if n == 2 else (f"TRIPLE {base}" if n == 3 else f"{n}x {base}"))


class Scorer:
    """Houdt punten, combo en meldingen bij voor een truck."""

    def __init__(self):
        self.total = 0
        self.chain = 0
        self.chain_t = 0.0
        self.best = (0, "")
        self.events = []                     # [titel, tekst, kleur, leeftijd]
        self.n = dict(flips=0, spins=0, wheelie=0.0, crushes=0, jumps=0, crashes=0, cars=0)

    @property
    def mult(self):
        return min(5.0, 1.0 + 0.5 * self.chain)

    def add(self, title, base, col=(255, 220, 70), chain=True):
        m = self.mult
        pts = int(base * m)
        self.total += pts
        if chain:
            self.chain += 1
            self.chain_t = 5.0
        if pts > self.best[0]:
            self.best = (pts, title)
        self.events.append([title, f"+{pts:,}".replace(",", ".") + (f"   x{m:.1f}" if m > 1 else ""), col, 0.0])
        del self.events[:-5]
        return pts

    def crash(self):
        self.chain, self.chain_t = 0, 0.0
        self.n["crashes"] += 1
        self.events.append(["CRASH!", "combo kwijt", (255, 90, 70), 0.0])

    def update(self, dt):
        if self.chain_t > 0:
            self.chain_t -= dt
            if self.chain_t <= 0:
                self.chain = 0
        for e in self.events:
            e[3] += dt
        self.events = [e for e in self.events if e[3] < 2.6]


class Junk:
    """Een oude auto die je kunt platrijden (of overheen springen)."""

    def __init__(self, x, y, ang, model, tint):
        self.x, self.y, self.ang = x, y, ang
        self.model, self.tint = model, tint
        self.crushed = False
        self.sprite = ART.sprite(model, tint)
        self.flat = None

    def crush(self):
        self.crushed = True
        w, h = self.sprite.get_size()
        self.flat = pygame.transform.smoothscale(self.sprite, (int(w * 1.12), max(6, int(h * 0.5))))
        self.flat.fill((120, 110, 105), special_flags=pygame.BLEND_RGB_MULT)

    def draw(self, screen, cx, cy):
        sx, sy = self.x - cx, self.y - cy
        if not (-90 < sx < W + 90 and -90 < sy < H + 90):
            return
        img = self.flat if self.crushed else self.sprite
        rot = pygame.transform.rotate(img, -math.degrees(self.ang))
        screen.blit(rot, rot.get_rect(center=(sx, sy)))


# ------------------------------------------------------------------ de arena zelf
def soft_light(radius, color, a_max=70):
    """Zachte lichtvlek (alpha-ringen) om op de wereld te leggen."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(22):
        t = i / 22
        pygame.draw.circle(s, (*color, int(a_max * t * t)), (radius, radius), int(radius * (1 - t) + 2))
    return s


class ArenaMap:
    """De arena: hellingen, heuvels, modder en een muur eromheen. Werkt ook als 'track' voor Car.physics."""
    dirt = True

    def __init__(self):
        self.w, self.h = ARENA_W, ARENA_H
        M = ARENA_M
        self.x0, self.y0, self.x1, self.y1 = M, M, self.w - M, self.h - M
        self.ramps = []        # (startx, starty, dirx, diry, lengte, halve breedte, hoogte)
        self.mounds = []       # (x, y, straal, hoogte)
        self.puddles = []      # (x, y, straal, 0)
        self.junk_spec = []    # (x, y, hoek)
        cx, cy = self.w / 2, self.h / 2

        def ramp(x, y, ang, L=190, Wr=80, Hr=80):
            self.ramps.append((x, y, math.cos(ang), math.sin(ang), L, Wr, Hr))
        # twee mega-ramps met een rij auto's ervoor
        ramp(560, cy, 0.0, 260, 100, 120)
        ramp(self.w - 560, cy, math.pi, 260, 100, 120)
        for k in range(6):
            self.junk_spec.append((900 + k * 72, cy, 0.0))
            self.junk_spec.append((self.w - 900 - k * 72, cy, math.pi))
        # kleinere schansen die naar het midden wijzen
        for x, y in ((760, 640), (self.w - 760, 640), (760, self.h - 640), (self.w - 760, self.h - 640),
                     (cx, 560), (cx, self.h - 560)):
            ramp(x, y, math.atan2(cy - y, cx - x))
        self.mounds = [(cx, cy, 150, 40), (cx - 380, cy - 330, 110, 34), (cx + 380, cy + 330, 110, 34),
                       (cx - 380, cy + 330, 100, 30), (cx + 380, cy - 330, 100, 30)]
        self.puddles = [(1050, 1480, 105, 0), (2150, 720, 105, 0), (2120, 1500, 100, 0)]
        for _ in range(9):                                            # losse autowrakken
            for _try in range(30):
                x = random.uniform(self.x0 + 220, self.x1 - 220)
                y = random.uniform(self.y0 + 220, self.y1 - 220)
                if self.height(x, y) == 0 and not self.in_mud(x, y) and all(
                        math.hypot(x - jx, y - jy) > 120 for jx, jy, _ in self.junk_spec):
                    self.junk_spec.append((x, y, random.uniform(0, TAU)))
                    break
        self.world = None

    # ---- interface voor Car.physics
    def on_road(self, x, y):
        return True

    def in_mud(self, x, y):
        for px, py, r, _ in self.puddles:
            if (x - px) ** 2 + (y - py) ** 2 < r * r:
                return True
        return False

    def height(self, x, y):
        """Hoogte van de grond (helling of heuvel) op deze plek."""
        h = 0.0
        for sx, sy, dx, dy, L, Wr, Hr in self.ramps:
            rx, ry = x - sx, y - sy
            u = rx * dx + ry * dy
            if 0 <= u <= L and abs(-rx * dy + ry * dx) <= Wr:
                h = max(h, Hr * u / L)
        for mx, my, r, hm in self.mounds:
            d = math.hypot(x - mx, y - my)
            if d < r:
                h = max(h, hm * 0.5 * (1 + math.cos(math.pi * d / r)))
        return h

    # ---- tekenen
    def render(self):
        w, h, M = self.w, self.h, ARENA_M
        world = pygame.Surface((w, h)).convert()
        world.fill((16, 12, 12))
        floor = pygame.Rect(M, M, w - 2 * M, h - 2 * M)
        self._stands(world, floor)
        tile = make_dirt_tile()
        for y in range(floor.top, floor.bottom, 256):
            for x in range(floor.left, floor.right, 256):
                world.blit(tile, (x, y), pygame.Rect(0, 0, min(256, floor.right - x), min(256, floor.bottom - y)))
        for _ in range(110):                                          # duinen en kuilen
            r = random.randint(100, 320)
            s = pygame.Surface((2 * r, r), pygame.SRCALPHA)
            c = (236, 172, 104, 20) if random.random() < 0.5 else (110, 64, 30, 26)
            pygame.draw.ellipse(s, c, s.get_rect())
            world.blit(s, (random.randint(floor.left, floor.right) - r, random.randint(floor.top, floor.bottom) - r // 2))
        for _ in range(80):                                           # bandensporen
            x, y = random.uniform(floor.left + 100, floor.right - 100), random.uniform(floor.top + 100, floor.bottom - 100)
            a = random.uniform(0, TAU)
            pts = []
            for k in range(28):
                a += random.uniform(-0.2, 0.2)
                x += math.cos(a) * 34
                y += math.sin(a) * 34
                pts.append((x, y))
            for off in (-9, 9):
                pygame.draw.lines(world, (150, 98, 54), False, [(px, py + off) for px, py in pts], 4)
        pygame.draw.circle(world, (170, 116, 66), (w // 2, h // 2), 520, 6)       # ring op de vloer
        pygame.draw.circle(world, (170, 116, 66), (w // 2, h // 2), 500, 2)
        for px, py, r, _ in self.puddles:                             # modderpoelen
            px, py, r = int(px), int(py), int(r)
            pygame.draw.ellipse(world, (156, 104, 62), (px - r - 6, py - int(r * 0.8) - 6, 2 * r + 12, int(1.6 * r) + 12))
            pygame.draw.ellipse(world, (92, 58, 32), (px - r, py - int(r * 0.8), 2 * r, int(1.6 * r)))
            pygame.draw.ellipse(world, (118, 78, 46), (px - int(r * 0.7), py - int(r * 0.5), int(r * 1.3), int(r * 0.8)))
            pygame.draw.ellipse(world, (176, 140, 108), (px - int(r * 0.5), py - int(r * 0.45), int(r * 0.5), int(r * 0.2)))
        for mx, my, r, hm in self.mounds:                             # heuvels
            for i in range(10):
                t = i / 9
                rr = int(r * (1 - t * 0.85))
                col = mix((176, 120, 66), (232, 180, 112), t)
                pygame.draw.circle(world, col, (int(mx - t * r * 0.12), int(my - t * r * 0.12)), rr)
            pygame.draw.circle(world, (120, 78, 42), (int(mx), int(my)), int(r), 3)
        for sx, sy, dx, dy, L, Wr, Hr in self.ramps:                  # hellingen
            surf = pygame.Surface((int(L) + 40, int(Wr * 2) + 20), pygame.SRCALPHA)
            for u in range(int(L)):
                t = u / L
                pygame.draw.line(surf, mix((110, 78, 46), (236, 196, 120), t), (u + 20, 10), (u + 20, int(Wr * 2) + 10))
            for u in range(34, int(L) - 10, 44):                      # gele pijlen
                pygame.draw.polygon(surf, (255, 214, 60), [(u + 22, Wr + 10), (u + 4, Wr - 16), (u + 4, Wr - 6),
                                                           (u + 12, Wr + 10), (u + 4, Wr + 26), (u + 4, Wr + 36)])
            pygame.draw.rect(surf, (80, 52, 28), (20, 10, int(L), 8))
            pygame.draw.rect(surf, (80, 52, 28), (20, int(Wr * 2) + 2, int(L), 8))
            pygame.draw.rect(surf, (255, 240, 200), (int(L) + 14, 10, 8, int(Wr * 2)))
            ang = -math.degrees(math.atan2(dy, dx))
            sh = pygame.Surface((26, int(Wr * 2)), pygame.SRCALPHA)
            sh.fill((0, 0, 0, 90))
            rs = pygame.transform.rotate(sh, ang)
            lipx, lipy = sx + dx * L, sy + dy * L
            world.blit(rs, rs.get_rect(center=(lipx + dx * 14 + 6, lipy + dy * 14 + 8)))
            rot = pygame.transform.rotate(surf, ang)
            world.blit(rot, rot.get_rect(center=(sx + dx * L / 2, sy + dy * L / 2)))
        # muur (rood/wit) rond de vloer
        for x in range(floor.left - 34, floor.right + 34, 50):
            for yy in (floor.top - 34, floor.bottom):
                pygame.draw.rect(world, (214, 56, 40) if (x // 50) % 2 else (236, 232, 224), (x, yy, 50, 34))
        for y in range(floor.top - 34, floor.bottom + 34, 50):
            for xx in (floor.left - 34, floor.right):
                pygame.draw.rect(world, (214, 56, 40) if (y // 50) % 2 else (236, 232, 224), (xx, y, 34, 50))
        pygame.draw.rect(world, (60, 56, 56), floor.inflate(68, 68), 3)
        pygame.draw.rect(world, (30, 20, 14), floor.inflate(2, 2), 4)
        for cxp, cyp in ((floor.left, floor.top), (floor.right, floor.top), (floor.left, floor.bottom), (floor.right, floor.bottom)):
            for k in range(3):                                         # bandenstapels in de hoeken
                pygame.draw.circle(world, (20, 20, 22), (int(cxp + (k - 1) * 18), int(cyp)), 22)
                pygame.draw.circle(world, (60, 60, 66), (int(cxp + (k - 1) * 18), int(cyp)), 22, 3)
                pygame.draw.circle(world, (12, 12, 14), (int(cxp + (k - 1) * 18), int(cyp)), 9)
        glow = soft_light(560, (255, 214, 150), 55)                    # schijnwerpers
        for gx, gy in ((floor.left + 300, floor.top + 250), (floor.right - 300, floor.top + 250),
                       (floor.left + 300, floor.bottom - 250), (floor.right - 300, floor.bottom - 250),
                       (w // 2, h // 2)):
            world.blit(glow, (gx - 560, gy - 560))
        self.world = world

    def _stands(self, world, floor):
        w, h = self.w, self.h
        bands = [pygame.Rect(0, 0, w, floor.top - 40), pygame.Rect(0, floor.bottom + 40, w, h - floor.bottom - 40),
                 pygame.Rect(0, floor.top - 40, floor.left - 40, floor.height + 80),
                 pygame.Rect(floor.right + 40, floor.top - 40, w - floor.right - 40, floor.height + 80)]
        for b in bands:
            pygame.draw.rect(world, (28, 24, 28), b)
            for y in range(b.top + 6, b.bottom - 4, 15):
                pygame.draw.rect(world, (40, 34, 40), (b.left, y + 9, b.width, 5))
                for x in range(b.left + 6, b.right - 4, 11):
                    if random.random() < 0.92:
                        c = random.choice(CROWD)
                        c = _dark(c, random.uniform(0.0, 0.5))
                        pygame.draw.circle(world, c, (x + random.randint(-1, 1), y + random.randint(0, 3)), 4)
        bf = pygame.font.SysFont("impact,arialblack,arial", 34, bold=True)
        words = ["MONSTER STUNTS", "NITRO", "BIG AIR", "CRUSH!", "BACKFLIP", "FULL THROTTLE"]
        cols = [(214, 56, 40), (255, 190, 30), (40, 150, 230), (236, 232, 224)]
        x = 160
        i = 0
        while x < w - 400:
            img = bf.render(words[i % len(words)], True, (20, 14, 10))
            bw = img.get_width() + 40
            for yy in (floor.top - 96, floor.bottom + 56):
                pygame.draw.rect(world, cols[i % 4], (x, yy, bw, 42), border_radius=6)
                world.blit(img, (x + 20, yy + 3))
            x += bw + 90
            i += 1

    def make_junk(self):
        return [Junk(x, y, a, random.choice(CIVIL_MODELS), random.choice([0, 0, 5, 10, 14, 19]))
                for x, y, a in self.junk_spec]


class Truck(Car):
    """Monstertruck: een Car (voor de grondfysica) met hoogte, flips en stuntpunten."""

    def __init__(self, x, y, heading, cfg, name, is_player=False):
        prm = truck_params(cfg)
        self.x, self.y, self.heading = x, y, heading
        self.vx = self.vy = 0.0
        self.vmax = self.base_vmax = prm["vmax"]
        self.accel, self.turn = prm["accel"], prm["turn"]
        self.nitro_cap = prm["nitro"]
        self.nitro = self.nitro_cap
        self.boosting = self.braking = False
        self.name, self.is_player = name, is_player
        self.color = PALETTE[cfg["color"]]
        self.slip, self.on_road, self.mud, self.was_mud = 0.0, True, False, False
        self.air_T, self.z, self.rattle = 0.0, 0.0, 0.0
        self.hop_v, self.flip_rate = prm["hop"], prm["flip"]
        self.vz = self.pitch = self.pw = 0.0
        self.air = False
        self.info = None                       # gegevens van de huidige sprong
        self.rise = 0.0                        # hoe snel de grond omhoog liep (voor lanceren)
        self.wheelie_t = 0.0
        self.stun = self.hop_cd = self.ram_cd = 0.0
        self.art = get_truck_art(cfg)
        self.score = Scorer()


def new_air_info(tiny=False):
    return dict(t=0.0, peak=0.0, back=0.0, front=0.0, spin=0.0, cars=0, over=set(), tiny=tiny)


class ArenaBot:
    """Bot-monstertruck: rijdt naar schansen, springt en doet flips (soms te gewaagd)."""

    def __init__(self, truck, arena, skill):
        self.t, self.a, self.skill = truck, arena, skill
        self.target, self.mode, self.ramp = None, "roam", None
        self.timer = 0.0
        self.plan = None
        self.wheelie_left = 0.0
        self.stuck = 0.0

    def pick(self):
        m, r = self.a.map, random.random()
        if r < 0.6 and m.ramps:
            self.ramp = random.choice(m.ramps)
            self.mode = "ramp"
            self.target = (self.ramp[0] - self.ramp[2] * 280, self.ramp[1] - self.ramp[3] * 280)
        elif r < 0.78 and self.a.junk:
            j = random.choice(self.a.junk)
            self.mode, self.target = "roam", (j.x, j.y)
        else:
            self.mode = "roam"
            self.target = (random.uniform(m.x0 + 250, m.x1 - 250), random.uniform(m.y0 + 250, m.y1 - 250))
        self.timer = 10.0

    def control(self, dt):
        t, m = self.t, self.a.map
        if t.air:
            return self._air()
        self.plan = None
        self.timer -= dt
        if self.target is None or self.timer <= 0:
            self.pick()
        tx, ty = self.target
        if self.mode == "ramp":
            sx, sy, dx, dy, L, Wr, Hr = self.ramp
            u = (t.x - sx) * dx + (t.y - sy) * dy
            v = -(t.x - sx) * dy + (t.y - sy) * dx
            if abs(v) < 95 and -340 < u:
                tx, ty = sx + dx * (u + 220), sy + dy * (u + 220)        # recht op de lip aan
            else:
                tx, ty = sx - dx * 280, sy - dy * 280                    # eerst naar de startpositie
            if u > L + 40:
                self.pick()
        elif math.hypot(tx - t.x, ty - t.y) < 100:
            self.pick()
        if (t.x < m.x0 + 200 or t.x > m.x1 - 200 or t.y < m.y0 + 200 or t.y > m.y1 - 200) and self.mode == "roam":
            tx, ty = m.w / 2, m.h / 2
        diff = wrap_rad(math.atan2(ty - t.y, tx - t.x) - t.heading)
        steer = clamp(diff * 2.6, -1, 1)
        fs = t.forward_speed
        thr, brk, boost = True, False, False
        if abs(diff) > 1.2 and fs > 200:
            thr, brk = False, True
        if self.mode == "roam":
            if self.wheelie_left > 0:
                self.wheelie_left -= dt
                boost = t.nitro > 4
            elif fs > 160 and t.nitro > 70 and abs(diff) < 0.3 and random.random() < dt * 0.1:
                self.wheelie_left = random.uniform(1.5, 3.2)
        if fs < 25:
            self.stuck += dt
            if self.stuck > 1.6:
                steer, thr, brk = -steer, False, True
            if self.stuck > 2.6:
                self.stuck = 0.0
                self.pick()
        else:
            self.stuck = 0.0
        return thr, brk, steer, False, boost, 0

    def _air(self):
        t, info = self.t, self.t.info
        if info["tiny"]:
            return False, False, 0, False, False, 0
        if self.plan is None:
            T = 2 * max(t.vz, 0.0) / GRAV + 0.15
            per = TAU / t.flip_rate + 0.12
            n = int((T - 0.35) / per)
            n = min(n, 1 + int(self.skill * 3))
            if n > 0 and random.random() < (1 - self.skill) * 0.5 + 0.04:
                n += 1                                                    # te gewaagd: kan misgaan
            spin = random.choice([-1, 1]) if (T > 1.3 and random.random() < 0.4) else 0
            self.plan = dict(n=n, d=random.choice([1, -1]), spin=spin)
        pl = self.plan
        rot = info["back"] if pl["d"] > 0 else info["front"]
        flip = pl["d"] if (pl["n"] > 0 and rot < pl["n"] * TAU - 0.55) else 0
        steer = pl["spin"] if (pl["spin"] and abs(info["spin"]) < TAU - 0.5) else 0
        return False, False, steer, False, False, flip


def make_arena_bg():
    s = pygame.Surface((W, H))
    for y in range(H):
        t = y / H
        c = mix(mix((6, 5, 9), (40, 17, 8), min(1, t * 1.6)), (12, 7, 5), max(0, (t - 0.65) / 0.35))
        pygame.draw.line(s, c, (0, y), (W, y))
    glow = soft_light(520, (255, 110, 20), 70)                           # gloed bij de horizon
    flat = pygame.Surface(glow.get_size())
    flat.blit(glow, (0, 0))                                              # alpha -> helderheid (voor ADD)
    s.blit(pygame.transform.smoothscale(flat, (1500, 460)), (W // 2 - 750, H - 400), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.rect(s, (14, 12, 16), (0, 0, W, 46))                     # lichtmast bovenin
    for x in range(40, W, 110):
        pygame.draw.circle(s, (255, 236, 190), (x, 24), 9)
        pygame.draw.circle(s, (255, 190, 90), (x, 24), 15, 3)
    for x in range(-40, W + 40, 34):                                      # publiek onderin
        hh = random.randint(0, 12)
        pygame.draw.circle(s, (8, 6, 8), (x, H - 26 + hh), 22)
        if random.random() < 0.15:
            pygame.draw.circle(s, (255, 230, 170), (x + random.randint(-8, 8), H - 44 + hh), 2)
    for y0, sign in ((0, 1), (H - 18, 1)):                                # waarschuwingsstrepen
        for x in range(-40, W + 40, 44):
            pygame.draw.polygon(s, (240, 190, 20), [(x, y0), (x + 22, y0), (x + 22 - 18, y0 + 18), (x - 18, y0 + 18)])
        pygame.draw.rect(s, (0, 0, 0), (0, y0 + 14, W, 4))
    return s


class ArenaFX:
    """Bewegende achtergrond van de arena-menu's: zwaaiende lichtbundels en vonken."""

    def __init__(self):
        self.bg = make_arena_bg()
        self.ov = pygame.Surface((W, H), pygame.SRCALPHA)
        self.beams = [(x, random.uniform(0, TAU)) for x in (140, 420, 700, 980, 1180)]
        self.embers = [[random.uniform(0, W), random.uniform(0, H), random.uniform(-14, 14),
                        random.uniform(-110, -40), random.uniform(1.5, 3.5)] for _ in range(70)]

    def draw(self, scr, now, dt):
        scr.blit(self.bg, (0, 0))
        self.ov.fill((0, 0, 0, 0))
        for ox, ph in self.beams:
            a = math.sin(now * 0.55 + ph) * 0.5
            for k, al in ((0.16, 14), (0.09, 22)):
                tip = (ox + math.sin(a - k) * 900, 30 + math.cos(a - k) * 900)
                tip2 = (ox + math.sin(a + k) * 900, 30 + math.cos(a + k) * 900)
                pygame.draw.polygon(self.ov, (255, 214, 150, al), [(ox, 30), tip, tip2])
        scr.blit(self.ov, (0, 0))
        for e in self.embers:
            e[0] += e[2] * dt + math.sin(now * 2 + e[1]) * 8 * dt
            e[1] += e[3] * dt
            if e[1] < -10:
                e[0], e[1] = random.uniform(0, W), H + 10
            r = int(e[4])
            pygame.draw.circle(scr, (255, 150 + int(60 * math.sin(now * 5 + e[0])), 40), (int(e[0]), int(e[1])), r)


class Arena:
    """De stuntarena: freestyle (highscore) of battle tegen bots. Meer punten voor gekkere stunts."""

    def __init__(self, save, sfx):
        self.sfx = sfx
        self.mode = save["arena_mode"]
        n_bots = save["arena_bots"] if self.mode == 1 else 0
        self.duration = float(save["arena_time"])
        self.time_left = self.duration
        self.map = ArenaMap()
        self.map.render()
        self.junk = self.map.make_junk()
        cx, cy = self.map.w / 2, self.map.h / 2
        self.player = Truck(cx, cy + 640, -math.pi / 2, save["truck"], "Jij", True)
        self.trucks = [self.player]
        self.bots = []
        spots = [(cx - 520, cy + 560), (cx + 520, cy + 560), (cx - 900, cy + 400), (cx + 900, cy + 400), (cx, cy - 640)]
        names = random.sample(BOT_NAMES, n_bots)
        for i in range(n_bots):
            x, y = spots[i]
            tk = Truck(x, y, -math.pi / 2 if i < 2 else random.uniform(0, TAU), random_truck_cfg(), names[i])
            self.trucks.append(tk)
            self.bots.append(ArenaBot(tk, self, 0.55 + 0.07 * i + random.uniform(-0.05, 0.1)))
        self.particles = []
        self.shake = 0.0
        self.state = "countdown"
        self.countdown = 3.0
        self._cd_last = 4
        self.go_t = 0.0
        self.rpm, self.power = 0.2, 0.15
        self.cam_x = clamp(self.player.x - W / 2, 0, self.map.w - W)
        self.cam_y = clamp(self.player.y - H / 2, 0, self.map.h - H)
        self.dial = make_dial(200)
        self.t_run = 0.0
        if sfx:
            sfx.start_loops(False)

    # ---- hulpjes
    def ranking(self):
        return sorted(self.trucks, key=lambda t: -t.score.total)

    def visible(self, t, m=200):
        return abs(t.x - (self.cam_x + W / 2)) < W / 2 + m and abs(t.y - (self.cam_y + H / 2)) < H / 2 + m

    def spawn(self, x, y, vx, vy, life, size, col, kind=0):
        self.particles.append([x, y, vx, vy, 0.0, life, size, col, kind])

    def burst(self, x, y, n, col, speed=(60, 200), kind=0, life=(0.4, 0.9), size=(5, 10)):
        for _ in range(n):
            a = random.uniform(0, TAU)
            sp = random.uniform(*speed)
            self.spawn(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(*life), random.uniform(*size), col, kind)

    def play(self, name, vol=1.0, t=None):
        if self.sfx and (t is None or t.is_player or self.visible(t)):
            self.sfx.play(name, vol if (t is None or t.is_player) else vol * 0.4)

    # ---- invoer van de speler
    def _input(self, keys):
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        dn = keys[pygame.K_DOWN] or keys[pygame.K_s]
        steer = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        flip = (1 if (dn or keys[pygame.K_q]) else 0) - (1 if (up or keys[pygame.K_e]) else 0)   # +1 = backflip
        return up, dn, steer, keys[pygame.K_SPACE], keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT], flip

    # ---- een truck een stap laten zetten
    def _takeoff(self, t, vz, tiny=False):
        t.air, t.vz = True, vz
        t.info = new_air_info(tiny)
        if not tiny:
            self.play("jump", 0.7, t)
            self.burst(t.x, t.y, 6, (208, 156, 100))

    def _land(self, t, g):
        info = t.info
        impact = -t.vz
        t.z, t.air, t.air_T = g, False, 0.0
        w = wrap_rad(t.pitch)
        t.vx *= 0.94
        t.vy *= 0.94
        if impact > 260:
            self.burst(t.x, t.y, int(min(16, impact / 60)), (208, 156, 100), (60, 190))
            self.play("thud", clamp(impact / 700, 0.3, 1.0), t)
            if t.is_player:
                self.shake = max(self.shake, min(9, impact / 110))
        if info["tiny"]:
            t.pitch = w
            t.pw = 0.0
            return
        sc = t.score
        if abs(w) >= 0.8:                                                 # op zijn dak / zijkant: crash
            t.stun = 1.5
            t.pitch = math.pi if abs(w) > 2.3 else w
            t.pw = 0.0
            t.vx *= 0.35
            t.vy *= 0.35
            sc.crash()
            self.burst(t.x, t.y, 14, (255, 200, 90), (80, 300), 1, (0.2, 0.5), (2, 3.5))
            self.play("hit", 0.9, t)
            if t.is_player:
                self.shake = max(self.shake, 10)
            return
        t.pitch, t.pw = w, 0.0
        parts = []
        nb, nf = int((info["back"] + 0.9) // TAU), int((info["front"] + 0.9) // TAU)
        ns = int((abs(info["spin"]) + 1.0) // TAU)
        if nb:
            parts.append((flip_name("BACKFLIP", nb), sum(500 * k for k in range(1, nb + 1))))
        if nf:
            parts.append((flip_name("FRONTFLIP", nf), sum(600 * k for k in range(1, nf + 1))))
        if ns:
            parts.append((f"{ns * 360} SPIN", sum(400 * k for k in range(1, ns + 1))))
        if info["cars"]:
            parts.append((f"OVER {info['cars']} AUTO'S", 220 * info["cars"]))
        special = len(parts)
        air_t = info["t"]
        if air_t > 0.6:
            parts.append(("BIG AIR" if info["peak"] > 160 else "SPRONG", int(air_t * 100 + info["peak"] * 0.8)))
            sc.n["jumps"] += 1
        if not parts:
            return
        base = sum(b for _, b in parts)
        if special >= 2:
            base = int(base * 1.5)
            title = "COMBO! " + " + ".join(n for n, _ in parts[:2])
        else:
            title = parts[0][0] if special else parts[-1][0]
        sc.n["flips"] += nb + nf
        sc.n["spins"] += ns
        sc.n["cars"] += info["cars"]
        col = (255, 90, 200) if base >= 3000 else ((255, 150, 40) if base >= 1200 else (255, 220, 70))
        sc.add(title, base, col)
        self.play("lap", 0.8, t)
        if t.is_player:
            self.shake = max(self.shake, 5)

    def _drive(self, t, dt, inp):
        m = self.map
        thr, brk, steer, hop, boost, flip = inp
        if t.stun > 0:
            t.stun -= dt
            thr = brk = hop = boost = False
            steer = flip = 0
        t.hop_cd = max(0.0, t.hop_cd - dt)
        t.ram_cd = max(0.0, t.ram_cd - dt)
        g = m.height(t.x, t.y)
        if hop and not t.air and t.hop_cd <= 0 and t.z <= g + 4:
            t.hop_cd = 0.7
            self._takeoff(t, t.hop_v)
        t.air_T = 1.0 if t.air else 0.0
        t.physics(m, dt, thr, brk, 0 if t.air else steer, False, boost, 1.0)
        if t.air:
            t.heading += steer * SPIN_RATE * dt
            info = t.info
            info["spin"] += steer * SPIN_RATE * dt
            info["t"] += dt
            if flip:
                t.pw += (flip * t.flip_rate - t.pw) * min(1.0, dt * 9)
            else:
                w = wrap_rad(t.pitch)
                if abs(w) < 1.3:
                    t.pw += (-w * 22 - t.pw * 5.5) * dt          # automatisch rechtzetten bij bijna rechtop
                else:
                    t.pw *= max(0.0, 1 - 1.6 * dt)
            dp = t.pw * dt
            t.pitch += dp
            if dp > 0:
                info["back"] += dp
            else:
                info["front"] -= dp
            t.vz -= GRAV * dt
            t.z += t.vz * dt
            info["peak"] = max(info["peak"], t.z)
            if t.z <= g and t.vz < 0:
                self._land(t, g)
                if not t.info["tiny"] and -t.vz > 420 and t.stun <= 0:      # kleine stuiter na een harde landing
                    self._takeoff(t, -t.vz * 0.2, True)
        else:
            if g >= t.z:
                nz = min(g, t.z + 700 * dt)
                t.rise = (nz - t.z) / dt
                t.z = nz
            elif t.z - g > 6:                                          # van de lip van een helling af
                self._takeoff(t, 150 + t.rise * 3.2 if t.rise > 40 else 0.0)
                t.rise = 0.0
            else:
                t.z = g
                t.rise = 0.0
            wheelie = t.boosting and t.forward_speed > 70 and t.stun <= 0
            target = 0.62 if wheelie else (t.pitch if t.stun > 0 else 0.0)
            t.pitch += (target - t.pitch) * min(1.0, dt * 6)
            if wheelie:
                t.wheelie_t += dt
                if random.random() < dt * 30:
                    fx, fy = math.cos(t.heading), math.sin(t.heading)
                    self.spawn(t.x - fx * 40, t.y - fy * 40, random.uniform(-30, 30), random.uniform(-30, 30),
                               random.uniform(0.4, 0.8), random.uniform(6, 10), (215, 215, 220))
            elif t.wheelie_t > 0:
                if t.wheelie_t >= 0.8:
                    t.score.n["wheelie"] += t.wheelie_t
                    t.score.add(f"WHEELIE {t.wheelie_t:.1f}s", int(t.wheelie_t * 160), (120, 220, 255))
                    self.play("lap", 0.6, t)
                t.wheelie_t = 0.0
        # muur
        for ax, lo, hi, vk in (("x", m.x0 + 60, m.x1 - 60, "vx"), ("y", m.y0 + 60, m.y1 - 60, "vy")):
            v = getattr(t, ax)
            if v < lo or v > hi:
                setattr(t, ax, clamp(v, lo, hi))
                vel = getattr(t, vk)
                if (v < lo and vel < 0) or (v > hi and vel > 0):
                    setattr(t, vk, -vel * 0.35)
                    if abs(vel) > 120:
                        self.play("bump", clamp(abs(vel) / 400, 0.2, 0.9), t)
                        if t.is_player:
                            self.shake = max(self.shake, min(7, abs(vel) * 0.02))

    def _effects(self, t, dt):
        if not self.visible(t):
            return
        speed = math.hypot(t.vx, t.vy)
        fx, fy = math.cos(t.heading), math.sin(t.heading)
        rx, ry = -fy, fx
        if not t.air and speed > 90 and random.random() < clamp(speed / 450, 0.1, 0.9):
            for s in (-1, 1):
                wx, wy = t.x - fx * 40 + rx * s * 30, t.y - fy * 40 + ry * s * 30
                self.spawn(wx, wy, random.uniform(-30, 30) - t.vx * 0.1, random.uniform(-30, 30) - t.vy * 0.1,
                           random.uniform(0.5, 0.9), random.uniform(6, 11), (208, 156, 100))
        if t.mud and speed > 40:
            self.burst(t.x, t.y, 2, (96, 64, 36), (40, 160), 0, (0.5, 0.9), (7, 12))
        if t.boosting:
            ex, ey = t.x - fx * 62, t.y - fy * 62
            for _ in range(2):
                self.spawn(ex + random.uniform(-3, 3), ey + random.uniform(-3, 3), -fx * random.uniform(140, 240) + t.vx * 0.3,
                           -fy * random.uniform(140, 240) + t.vy * 0.3, random.uniform(0.12, 0.26), random.uniform(5, 9),
                           random.choice([(255, 170, 60), (255, 230, 120), (255, 120, 40)]), 2)
        if t.stun > 0 and random.random() < dt * 22:
            self.spawn(t.x, t.y, random.uniform(-40, 40), random.uniform(-40, 40), random.uniform(0.6, 1.1), 10, (90, 90, 96))

    def reset_truck(self):
        """T: de speler-truck rechtop zetten."""
        p = self.player
        p.pitch = p.pw = p.vz = p.z = 0.0
        p.air, p.air_T, p.stun = False, 0.0, 0.0
        p.vx *= 0.3
        p.vy *= 0.3

    # ---- hoofdlogica
    def update(self, dt, keys):
        dt = min(dt, 0.05)
        p, m = self.player, self.map
        playing = self.state == "play"
        if self.state == "countdown":
            self.countdown -= dt
            n_cd = math.ceil(max(self.countdown, 0))
            if n_cd != self._cd_last:
                self._cd_last = n_cd
                if n_cd in (1, 2, 3):
                    self.play("beep")
            if self.countdown <= 0:
                self.state, self.go_t = "play", 1.2
                self.play("go")
        else:
            self.t_run += dt
            self.go_t = max(0.0, self.go_t - dt)
            if playing:
                self.time_left -= dt
                if self.time_left <= 0:
                    self.time_left, self.state = 0.0, "finished"
                    self.play("finish")
        idle = (False, False, 0, False, False, 0)
        for t in self.trucks:
            if not playing:
                inp = idle
            elif t.is_player:
                inp = self._input(keys)
            else:
                inp = next(b for b in self.bots if b.t is t).control(dt)
            self._drive(t, dt, inp)
        # truck <-> truck
        tr = self.trucks
        for i in range(len(tr)):
            for j in range(i + 1, len(tr)):
                a, b = tr[i], tr[j]
                imp = collide(a, b, 84)
                if imp > 40:
                    self.burst((a.x + b.x) / 2, (a.y + b.y) / 2, int(min(10, imp / 25)), (255, 200, 90), (80, 260), 1, (0.2, 0.4), (2, 3))
                    if a.is_player or b.is_player:
                        self.shake = max(self.shake, min(8, imp * 0.03))
                        self.play("hit", clamp(imp / 300, 0.3, 1.0))
                    if imp > 260 and playing:                             # beuk: de snelste krijgt punten
                        att = a if math.hypot(a.vx, a.vy) > math.hypot(b.vx, b.vy) else b
                        if att.ram_cd <= 0:
                            att.ram_cd = 1.5
                            att.score.add("RAM!", 120, (255, 130, 90), chain=False)
        # autowrakken: platrijden of overheen springen
        for t in tr:
            for j in self.junk:
                d = math.hypot(t.x - j.x, t.y - j.y)
                if d < 52:
                    if t.air and t.z > 36 and id(j) not in t.info["over"] and not t.info["tiny"]:
                        t.info["over"].add(id(j))
                        t.info["cars"] += 1
                    elif not t.air and not j.crushed and t.z < 26 and d < 46:
                        j.crush()
                        t.score.n["crushes"] += 1
                        t.score.add("CRUSH!", 100, (255, 170, 80), chain=False)
                        self.burst(j.x, j.y, 12, (200, 200, 205), (60, 220), 1, (0.2, 0.5), (2, 3.5))
                        self.play("bump", 0.8, t)
                        if t.is_player:
                            self.shake = max(self.shake, 3)
        for t in tr:
            t.score.update(dt)
            self._effects(t, dt)
        damp = max(0.0, 1 - 3.2 * dt)
        for q in self.particles:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] += dt
            if q[8] == 1:
                q[2] *= damp
                q[3] *= damp
        self.particles = [q for q in self.particles if q[4] < q[5]][-600:]
        self.shake *= max(0.0, 1 - 7 * dt)
        self._audio(dt)
        tx = p.x + p.vx * 0.3 - W / 2
        ty = p.y + p.vy * 0.3 - H / 2 - max(0.0, p.z) * 0.45        # camera tilt mee met de hoogte
        k = min(1, dt * 5)
        self.cam_x = clamp(self.cam_x + (tx - self.cam_x) * k, 0, m.w - W)
        self.cam_y = clamp(self.cam_y + (ty - self.cam_y) * k, 0, m.h - H)

    def _audio(self, dt):
        sfx = self.sfx
        if not sfx or not sfx.ok:
            return
        p = self.player
        spd = abs(p.forward_speed)
        r = clamp(spd / (p.vmax * 1.1), 0.0, 1.0)
        g = min(3, int(r * 4))
        target = 0.25 + 0.75 * (r * 4 - g)
        if p.boosting:
            target = max(target, 0.7)
        if p.air:
            target = 0.95
        self.rpm += (target - self.rpm) * min(1.0, dt * 9)
        self.power += ((1.0 if p.boosting or p.air else 0.2) - self.power) * min(1.0, dt * 8)
        dirt = 0.0 if p.air else clamp(spd / 400, 0.0, 1.0)
        near = 0.0
        for c in self.trucks:
            if not c.is_player:
                near = max(near, clamp(1 - math.hypot(c.x - p.x, c.y - p.y) / 700, 0, 1))
        sfx.loops(self.rpm, self.power, p.boosting, clamp((p.slip - 70) / 160, 0, 0.8) * (0 if p.air else 1), dirt, near, 0.0)

    # ---- tekenen
    def draw_truck(self, screen, t, cx, cy):
        sx, sy = t.x - cx, t.y - cy
        if not (-240 < sx < W + 240 and -240 < sy < H + 240):
            return
        art = t.art
        z = max(0.0, t.z)
        ang = -math.degrees(t.heading)
        sh = pygame.transform.rotozoom(art.shadow, ang, max(0.5, 1 - z / 520))
        sh.set_alpha(int(255 * max(0.3, 1 - z / 400)))
        screen.blit(sh, sh.get_rect(center=(sx + 8 + z * 0.25, sy + 10 + z * 0.25)))
        img = art.proj(t.pitch)
        k = min(1.9, 1 + z / 420) * (1 + 0.1 * abs(math.sin(t.pitch)))
        rot = pygame.transform.rotozoom(img, ang, k)
        lift = z * 0.5 + abs(math.sin(t.pitch)) * 16
        screen.blit(rot, rot.get_rect(center=(sx, sy - lift)))

    def draw(self, screen, A):
        m, p = self.map, self.player
        sx = sy = 0.0
        if self.shake > 0.3:
            sx, sy = random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)
        cx = int(clamp(self.cam_x + sx, 0, m.w - W))
        cy = int(clamp(self.cam_y + sy, 0, m.h - H))
        screen.blit(m.world, (0, 0), pygame.Rect(cx, cy, W, H))
        for j in self.junk:
            j.draw(screen, cx, cy)
        fx = pygame.Surface((W, H), pygame.SRCALPHA)
        for x, y, _, _, age, life, size, col, kind in self.particles:
            px, py = int(x - cx), int(y - cy)
            if not (-30 < px < W + 30 and -30 < py < H + 30):
                continue
            u = age / life
            if kind == 0:
                pygame.draw.circle(fx, (*col, int(150 * (1 - u))), (px, py), int(size * (1 + u * 1.6)))
            elif kind == 1:
                pygame.draw.circle(fx, (*col, int(255 * (1 - u))), (px, py), max(1, int(size * (1 - u * 0.6))))
            else:
                pygame.draw.circle(fx, (*col, int(230 * (1 - u))), (px, py), max(1, int(size * (1 - u * 0.7))))
        screen.blit(fx, (0, 0))
        for t in sorted(self.trucks, key=lambda t: (t.z, t.is_player)):
            self.draw_truck(screen, t, cx, cy)
        f = A["afonts"]
        for t in self.trucks:                                             # punten van bots zweven boven hun truck
            if not t.is_player and t.score.events:
                title, txt, col, age = t.score.events[-1]
                if age < 1.6 and self.visible(t, 0):
                    a = int(255 * clamp(1.6 - age, 0, 1))
                    img = f["s"].render(f"{title}  {txt}", True, col)
                    img.set_alpha(a)
                    screen.blit(img, img.get_rect(midbottom=(t.x - cx, t.y - cy - 70 - t.z * 0.5 - age * 28)))
        for t in self.trucks:                                             # namen
            if not t.is_player and self.visible(t, 0):
                text(screen, f["s"], t.name, (t.x - cx, t.y - cy - 56 - t.z * 0.5), (255, 214, 160), "midbottom")
        self._hud(screen, A)

    def _hud(self, screen, A):
        f = A["afonts"]
        p, sc = self.player, self.player.score
        # score + combo
        apanel(screen, (20, 20, 330, 124))
        text(screen, f["s"], "SCORE", (38, 28), (255, 170, 60))
        text(screen, f["l"], f"{sc.total:,}".replace(",", "."), (38, 44), (255, 240, 200))
        text(screen, f["s"], f"COMBO  x{sc.mult:.1f}" if sc.chain else "COMBO  -", (38, 106),
             (255, 214, 80) if sc.chain else (160, 130, 100))
        if sc.chain:
            pygame.draw.rect(screen, (50, 30, 12), (190, 112, 140, 10), border_radius=5)
            pygame.draw.rect(screen, (255, 190, 40), (190, 112, int(140 * clamp(sc.chain_t / 5, 0, 1)), 10), border_radius=5)
        # tijd
        apanel(screen, (W // 2 - 90, 20, 180, 70))
        tl = max(0, math.ceil(self.time_left))
        text(screen, f["s"], "TIJD", (W // 2, 26), (255, 170, 60), "midtop")
        text(screen, f["m"], f"{tl // 60}:{tl % 60:02d}", (W // 2, 46), (255, 80, 60) if tl <= 10 else (255, 240, 200), "midtop")
        # rechts: stand (battle) of beste stunt (freestyle)
        if self.mode == 1:
            order = self.ranking()
            apanel(screen, (W - 290, 20, 270, 40 + 28 * len(order)))
            text(screen, f["s"], "STAND", (W - 270, 26), (255, 170, 60))
            for i, t in enumerate(order):
                col = (255, 220, 70) if t.is_player else (230, 220, 210)
                pygame.draw.circle(screen, t.color, (W - 266, 74 + i * 28), 7)
                text(screen, f["s"], f"{i + 1}. {t.name}", (W - 252, 64 + i * 28), col)
                text(screen, f["s"], f"{t.score.total:,}".replace(",", "."), (W - 34, 64 + i * 28), col, "topright")
        else:
            apanel(screen, (W - 330, 20, 310, 74))
            text(screen, f["s"], "BESTE STUNT", (W - 312, 26), (255, 170, 60))
            b = sc.best
            text(screen, f["s"], f"{b[1]}  +{b[0]:,}".replace(",", ".") if b[0] else "-", (W - 312, 56), (255, 240, 200))
        # live stuntinfo in de lucht
        if p.air and p.info and not p.info["tiny"]:
            info = p.info
            nb, nf = (info["back"] + 0.9) // TAU, (info["front"] + 0.9) // TAU
            bits = [f"LUCHT {info['t']:.1f}s"]
            if nb:
                bits.append(flip_name("BACKFLIP", int(nb)))
            if nf:
                bits.append(flip_name("FRONTFLIP", int(nf)))
            if abs(info["spin"]) > 5.3:
                bits.append(f"{int((abs(info['spin']) + 1.0) // TAU) * 360} SPIN")
            if info["cars"]:
                bits.append(f"{info['cars']} AUTO'S")
            text(screen, f["m"], "   ".join(bits), (W // 2, 120), (120, 230, 255), "midtop")
        elif p.wheelie_t > 0.3:
            text(screen, f["m"], f"WHEELIE  {p.wheelie_t:.1f}s", (W // 2, 120), (120, 230, 255), "midtop")
        # nitro
        bw, bh = 300, 18
        bx, by = W // 2 - bw // 2, H - 52
        apanel(screen, (bx - 12, by - 28, bw + 24, bh + 42), 170)
        text(screen, f["s"], "NITRO / WHEELIE  (SHIFT)", (W // 2, by - 24), (255, 170, 60), "midtop", False)
        pygame.draw.rect(screen, (40, 24, 10), (bx, by, bw, bh), border_radius=9)
        frac = p.nitro / p.nitro_cap
        if frac > 0.01:
            pygame.draw.rect(screen, (255, 230, 120) if p.boosting else (255, 140, 30), (bx, by, max(8, int(bw * frac)), bh), border_radius=9)
        pygame.draw.rect(screen, (255, 200, 120), (bx, by, bw, bh), 2, border_radius=9)
        # snelheidsmeter
        dx, dy = W - 220, H - 220
        screen.blit(self.dial, (dx, dy))
        kmh = clamp(abs(p.forward_speed) * 0.5, 0, 300)
        ang = math.radians(135 + 270 * kmh / 300)
        c = 100
        pygame.draw.line(screen, (255, 90, 70), (dx + c, dy + c), (dx + c + math.cos(ang) * 72, dy + c + math.sin(ang) * 72), 4)
        pygame.draw.circle(screen, (30, 32, 40), (dx + c, dy + c), 9)
        pygame.draw.circle(screen, (255, 255, 255), (dx + c, dy + c), 9, 2)
        text(screen, f["m"], f"{kmh:.0f}", (dx + c, dy + 140), anchor="midtop")
        text(screen, f["s"], "km/h", (dx + c, dy + 172), (160, 175, 200), "midtop")
        # meldingen in het midden
        y = 170
        for title, txt, col, age in reversed(sc.events[-3:]):
            a = clamp(min(age / 0.12, (2.6 - age) / 0.6), 0, 1)
            pop = 1 + 0.35 * max(0.0, 1 - age / 0.18)
            img = f["l" if len(title) <= 18 else "m"].render(title, True, col)
            if pop > 1.01:
                img = pygame.transform.smoothscale(img, (int(img.get_width() * pop), int(img.get_height() * pop)))
            img.set_alpha(int(255 * a))
            screen.blit(img, img.get_rect(midtop=(W // 2, y)))
            sub = f["m"].render(txt, True, (255, 240, 210))
            sub.set_alpha(int(255 * a))
            screen.blit(sub, sub.get_rect(midtop=(W // 2, y + img.get_height() - 2)))
            y += img.get_height() + sub.get_height() + 4
            if y > 420:
                break
        if self.state == "countdown" or (self.state == "play" and self.go_t > 0):
            apanel(screen, (W // 2 - 110, 150, 220, 80))
            lit = (3 - math.ceil(max(self.countdown, 0)) + 1) if self.state == "countdown" else 3
            for i in range(3):
                col = (50, 40, 36)
                if self.state == "play":
                    col = (60, 230, 90)
                elif i < lit:
                    col = (240, 40, 40)
                pygame.draw.circle(screen, col, (W // 2 - 60 + i * 60, 190), 22)
                pygame.draw.circle(screen, (0, 0, 0), (W // 2 - 60 + i * 60, 190), 22, 3)
            if self.state == "play":
                text(screen, f["xl"], "GO!", (W // 2, 250), (110, 255, 140), "midtop")
        if self.state == "play" and self.t_run < 12:
            apanel(screen, (20, H - 186, 800, 96), 190)
            text(screen, f["s"], "Pijltjes/WASD rijden   SPATIE hop   SHIFT nitro + WHEELIE   ESC pauze   T terugzetten",
                 (36, H - 178), (255, 220, 170), shadow=False)
            text(screen, f["s"], "In de lucht:  OMHOOG = frontflip   OMLAAG = backflip   LINKS/RECHTS = draaien",
                 (36, H - 150), (255, 220, 170), shadow=False)
            text(screen, f["s"], "Land op je wielen! Meer flips + draaien in een sprong = veel meer punten.",
                 (36, H - 122), (255, 190, 90), shadow=False)



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
        self.theme = THEME_DEFAULT

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

    def button(self, surf, rect, label, fn, selected=False, accent=None,
               enabled=True, font="m"):
        th = self.theme
        if accent is None:
            accent = th["accent"]
        r = pygame.Rect(rect)
        hover = enabled and r.collidepoint(self.mouse)
        if hover and self.down:
            r = r.move(0, 2)
        if not enabled:
            base = th["dis"]
        elif selected:
            base = th["sel"]
        elif hover:
            base = th["hover"]
        else:
            base = th["base"]
        pygame.draw.rect(surf, base, r, border_radius=10)
        if selected:
            pygame.draw.rect(surf, accent, r, 3, border_radius=10)
        elif hover:
            pygame.draw.rect(surf, th["hover_border"], r, 2, border_radius=10)
        else:
            pygame.draw.rect(surf, th["border"], r, 2, border_radius=10)
        if label:
            col = (255, 255, 255) if enabled else th["dis_text"]
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

    def afont(sz):                                   # zware 'stadion'-letters voor de arena
        if pygame.font.match_font("impact"):
            return pygame.font.SysFont("impact", sz)
        return pygame.font.SysFont("arialblack,franklingothicheavy,segoeuiblack,arial", sz, bold=True)
    GLOW["red"] = make_glow(44, (255, 40, 30), 2.0)
    GLOW["red_dim"] = make_glow(34, (150, 16, 12), 2.0)
    GLOW["neon"] = make_glow(120, (0, 70, 120), 2.0)
    GLOW["blue"] = make_glow(70, (70, 140, 255), 2.0)
    GLOW["spot"] = make_glow(260, (70, 90, 150), 1.6)
    GLOW["cone"] = make_cone()
    global ART
    ART = CarArt()
    return {
        "fonts": {"xs": font(15), "s": font(18), "m": font(28), "l": font(46), "xl": font(84)},
        "afonts": {"xs": afont(16), "s": afont(21), "m": afont(32), "l": afont(54), "xl": afont(88)},
        "vignette": make_vignette(),
        "menu_bg": make_menu_bg(),
    }


# ------------------------------------------------------------------ applicatie
CARD_COLORS = [(226, 45, 90), (255, 165, 40), (255, 84, 18), (30, 190, 170), (140, 110, 255)]
CARD_NAMES = ["SNELLE RACE", "GRAND PRIX", "ARENA", "GARAGE", "INSTELLINGEN"]
CARD_SUBS = ["Race tegen de bots", "Kampioenschap met punten", "Monstertrucks en stunts", "Kies en tune je auto",
             "Scherm en besturing"]
CARD_W_ACTIVE, CARD_W_IDLE = 400.0, 172.0


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
        self.sfx = Sfx()
        self.sfx.volume = self.save["volume"] / 10
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
        self.hue_drag = False
        self.drag = None                    # regelaar die nu versleept wordt: (sleutel, rechthoek, min, max)
        self.menu_active = 0
        self.card_w = [CARD_W_ACTIVE] + [CARD_W_IDLE] * 4
        self.card_heat = [1.0, 0.0, 0.0, 0.0, 0.0]
        self.arena = None
        self.arena_done = False
        self.arena_result = None
        self.fx = ArenaFX()
        self.arena_glow = soft_light(250, (255, 140, 30), 110)
        self.confirm_reset = False
        self.confetti = Confetti()
        self.streaks = [[random.uniform(0, W), random.uniform(0, H), random.uniform(60, 220),
                         random.uniform(300, 900)] for _ in range(26)]
        self.raw = self.mm = self.stats = None
        self.new_preview(False)

    # ---- algemeen
    def quit(self):
        write_save(self.save)
        self.sfx.stop_loops()
        pygame.quit()
        sys.exit()

    def show_loading(self, msg):
        self.screen.blit(self.A["menu_bg"], (0, 0))
        text(self.screen, self.f["l"], msg, (W // 2, H // 2), anchor="center")
        pygame.display.flip()
        pygame.event.pump()

    def gen_raw(self):
        """Nieuwe middenlijn voor het gekozen soort kaart (circuit of snelweg)."""
        if self.save["env"] == ENV_HIGHWAY:
            return generate_highway_centerline(self.save["level"])
        if self.save["env"] == ENV_TOKYO:
            return generate_tokyo_centerline(self.save["level"])
        return generate_centerline(self.save["level"])

    def new_preview(self, loading=True):
        if loading:
            self.show_loading("Circuit genereren...")
        self.raw = self.gen_raw()
        self.mm = MiniMap(self.raw, 360, 300, pad=24, line=8)
        self.stats = (len(self.raw) * DS / 10000, count_bends(self.raw))        # 10 px = 1 m
        self.preview_fresh = True

    def car_big(self, car):
        return ART.big(car["model"], car["tint"])

    def goto(self, state):
        write_save(self.save)
        self.state = state

    def open_setup(self, mode):
        self.mode = mode
        self.goto("setup")

    def set_pause(self, flag):
        self.paused = flag
        self.sfx.set_paused(flag)

    def toggle_fullscreen(self):
        pygame.display.toggle_fullscreen()

    def menu_action(self, i):
        [lambda: self.open_setup("race"), lambda: self.open_setup("gp"), self.open_arena,
         lambda: self.open_garage("main"), lambda: self.goto("settings")][i]()

    def reset_save(self):
        if not self.confirm_reset:
            self.confirm_reset = True
            return
        self.confirm_reset = False
        self.save = json.loads(json.dumps(DEFAULTS))
        write_save(self.save)
        self.new_preview()

    def open_garage(self, frm):
        self.garage_from = frm
        self.goto("garage")

    # ---- races starten / afronden
    def start_session(self):
        s = self.save
        write_save(s)
        pcol = ART.color(s["car"]["model"], s["car"]["tint"])
        self.field = make_field(s["bots"], s["level"], s["car"]["model"])
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
            self.cur_raw = self.gen_raw()
        laps = s["laps_gp"] if self.mode == "gp" else s["laps_q"]
        self.race = Race(self.cur_raw, s["level"],
                         dict(laps=laps, weather=s["weather"], env=s["env"], traffic=s["traffic"]),
                         s["car"], self.field, self.make_grid(), self.sfx)
        self.state = "race"
        self.paused = False
        self.sfx.set_paused(False)

    def leave_race(self):
        self.sfx.stop_loops()
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
        self.sfx.stop_loops()
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
            if self.ui.click(e.pos):
                self.sfx.play("click", 0.8)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.hue_drag = False
            self.drag = None
        elif e.type == pygame.KEYDOWN:
            self.on_key(e.key)

    def on_key(self, key):
        enter = key in (pygame.K_RETURN, pygame.K_KP_ENTER)
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        st = self.state
        if st == "main":
            if key == pygame.K_1:
                self.open_setup("race")
            elif key == pygame.K_2:
                self.open_setup("gp")
            elif key == pygame.K_3:
                self.open_arena()
            elif key == pygame.K_4:
                self.open_garage("main")
            elif key == pygame.K_5:
                self.goto("settings")
            elif key == pygame.K_LEFT:
                self.menu_active = (self.menu_active - 1) % 5
            elif key == pygame.K_RIGHT:
                self.menu_active = (self.menu_active + 1) % 5
            elif enter:
                self.menu_action(self.menu_active)
            elif key == pygame.K_s:
                self.goto("settings")
            elif key == pygame.K_ESCAPE:
                self.quit()
        elif st == "settings":
            if key == pygame.K_ESCAPE:
                self.confirm_reset = False
                self.goto("main")
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
                self.set_pause(not self.paused)
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
                r.respawn(r.player)
            elif enter and r.state == "finished":
                self.results_continue()
        elif st == "arena_hub":
            if key == pygame.K_ESCAPE:
                self.goto("main")
            elif enter or key == pygame.K_SPACE:
                self.start_arena()
            elif key in (pygame.K_g, pygame.K_b):
                self.goto("arena_garage")
        elif st == "arena_garage":
            if key == pygame.K_ESCAPE or enter:
                self.goto("arena_hub")
        elif st == "arena":
            a = self.arena
            if key == pygame.K_ESCAPE:
                if a.state == "finished":
                    self.leave_arena()
                else:
                    self.set_pause(not self.paused)
            elif key == pygame.K_r:
                self.start_arena()
            elif key == pygame.K_m:
                self.leave_arena()
            elif key == pygame.K_t and a.state == "play" and not self.paused:
                a.reset_truck()
            elif enter and a.state == "finished":
                self.start_arena()
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

    def set_env(self, v):
        kind = lambda e: 1 if e == ENV_HIGHWAY else (2 if e == ENV_TOKYO else 0)
        was = kind(self.save["env"])
        self.save["env"] = v
        if was != kind(v):                          # snelweg / Tokyo / gewoon circuit: ander soort voorbeeld nodig
            self.new_preview()

    # ================================================================ ARENA
    def open_arena(self):
        self.goto("arena_hub")

    def start_arena(self):
        write_save(self.save)
        self.show_loading("Arena bouwen...")
        self.sfx.stop_loops()
        self.arena = Arena(self.save, self.sfx)
        self.arena_done = False
        self.arena_result = None
        self.state = "arena"
        self.paused = False
        self.sfx.set_paused(False)

    def leave_arena(self):
        self.sfx.stop_loops()
        self.arena = None
        self.paused = False
        self.goto("arena_hub")

    def finish_arena(self):
        """Tijd is om: highscore en beste stunt bijhouden."""
        a, hs = self.arena, self.save["hs"]
        self.arena_done = True
        key = "battle" if a.mode == 1 else "free"
        score = a.player.score.total
        lst = sorted(hs[key] + [score], reverse=True)
        pos = lst.index(score) + 1
        hs[key] = lst[:5]
        best = a.player.score.best
        new_stunt = best[0] > hs["stunt"]
        if new_stunt:
            hs["stunt"], hs["stunt_name"] = best[0], best[1]
        self.arena_result = dict(rank=pos if (pos <= 5 and score > 0) else None, new_stunt=new_stunt)
        write_save(self.save)
        self.sfx.stop_loops()

    def set_arena_mode(self, v):
        self.save["arena_mode"] = v

    # ---- truck bouwen
    def truck_cycle(self, key, d, n):
        tr = self.save["truck"]
        tr[key] = (tr[key] + d) % n

    def truck_set(self, key, v):
        self.save["truck"][key] = v

    def truck_tune(self, i, d):
        st = self.save["truck"]["stats"]
        st[i] = int(clamp(st[i] + d, 0, STAT_MAX))

    def truck_random(self):
        self.save["truck"] = random_truck_cfg()

    def truck_reset(self):
        self.save["truck"] = json.loads(json.dumps(DEFAULTS["truck"]))

    # ---- schermen
    def arena_title(self, big, small, x, y):
        f = self.A["afonts"]
        for dx, col in ((6, (120, 40, 0)), (3, (210, 90, 10))):
            text(self.screen, f["xl"], big, (x + dx, y + dx), col, shadow=False)
        text(self.screen, f["xl"], big, (x, y), (255, 214, 60), shadow=False)
        text(self.screen, f["s"], small, (x + 4, y + 80), (255, 150, 50), shadow=False)

    def draw_truck_stage(self, rect, scale=1.6):
        scr = self.screen
        r = pygame.Rect(rect)
        apanel(scr, r, 175, 18)
        scr.blit(self.arena_glow, self.arena_glow.get_rect(center=r.center))
        art = get_truck_art(self.save["truck"])
        img = pygame.transform.rotozoom(art.top, (self.now * 34) % 360, scale)
        sh = pygame.transform.rotozoom(art.shadow, (self.now * 34) % 360, scale)
        c = (r.centerx, r.centery + int(math.sin(self.now * 2) * 4))
        scr.blit(sh, sh.get_rect(center=(c[0] + 10, c[1] + 14)))
        scr.blit(img, img.get_rect(center=c))

    def draw_arena_hub(self):
        scr, f, ui, s = self.screen, self.A["afonts"], self.ui, self.save
        self.fx.draw(scr, self.now, self.dt)
        self.arena_title("ARENA", "MONSTER TRUCK STUNT ARENA", 60, 28)
        self.draw_truck_stage((60, 128, 520, 290))
        text(scr, f["s"], f"{TRUCK_STYLES[s['truck']['style']].upper()}  -  {TRUCK_DECALS[s['truck']['decal']].upper()}",
             (80, 138), (255, 170, 60), shadow=False)
        ui.button(scr, (60, 430, 520, 62), "TRUCK BOUWEN", lambda: self.goto("arena_garage"), accent=(255, 200, 30))
        apanel(scr, (60, 506, 520, 92), 170)
        text(scr, f["xs"], "Pijltjes/WASD rijden   SPATIE hop   SHIFT nitro = wheelie", (76, 516), (255, 214, 160), shadow=False)
        text(scr, f["xs"], "In de lucht:  OMHOOG frontflip,  OMLAAG backflip,", (76, 542), (255, 214, 160), shadow=False)
        text(scr, f["xs"], "LINKS/RECHTS draaien.  Land op je wielen!", (76, 568), (255, 214, 160), shadow=False)
        ui.button(scr, (60, 614, 200, 56), "TERUG", lambda: self.goto("main"), font="s")

        x = 620
        mode = s["arena_mode"]
        text(scr, f["s"], "SPELMODUS", (x, 132), (255, 150, 50), shadow=False)
        for i, nm in enumerate(ARENA_MODES):
            ui.button(scr, (x + i * 310, 158, 300, 64), nm, lambda i=i: self.set_arena_mode(i), selected=mode == i)
        desc = ("Haal de hoogste score met stunts, tegen de klok."
                if mode == 0 else "Stunt tegen bots: de meeste punten wint!")
        text(scr, f["s"], desc, (x, 232), (255, 214, 160), shadow=False)
        text(scr, f["s"], "TIJD", (x, 268), (255, 150, 50), shadow=False)
        self.stepper(x, 292, "arena_time", ARENA_TIME_MIN, ARENA_TIME_MAX,
                     lambda v: f"{v // 60}:{v % 60:02d}", step=30)
        if mode == 1:
            text(scr, f["s"], "TEGENSTANDERS", (x + 310, 268), (255, 150, 50), shadow=False)
            self.stepper(x + 310, 292, "arena_bots", 1, ARENA_MAX_BOTS, lambda v: f"{v} bot" if v == 1 else f"{v} bots")
        else:
            text(scr, f["s"], "SOLO", (x + 310, 268), (255, 150, 50), shadow=False)
            text(scr, f["m"], "jij tegen de klok", (x + 310 + 150, 320), (200, 170, 130), "center", False)
        # highscores
        apanel(scr, (x, 366, 610, 226), 175)
        text(scr, f["s"], f"HIGHSCORES  -  {ARENA_MODES[mode]}", (x + 22, 378), (255, 200, 60), shadow=False)
        lst = s["hs"]["battle" if mode == 1 else "free"]
        for i in range(5):
            yy = 410 + i * 30
            sc = lst[i] if i < len(lst) else None
            text(scr, f["s"], f"{i + 1}.", (x + 26, yy), (255, 170, 60), shadow=False)
            text(scr, f["m"], f"{sc:,}".replace(",", ".") if sc is not None else "-", (x + 70, yy - 6),
                 (255, 240, 200) if sc is not None else (110, 90, 70), shadow=False)
        text(scr, f["s"], "BESTE STUNT", (x + 22, 562), (255, 170, 60), shadow=False)
        hs = s["hs"]
        text(scr, f["xs"], f"{hs['stunt_name'][:30]}  +{hs['stunt']:,}".replace(",", ".") if hs["stunt"] else "nog geen stunt",
             (x + 190, 565), (255, 240, 200) if hs["stunt"] else (110, 90, 70), shadow=False)
        ui.button(scr, (x, 606, 610, 68), "START", self.start_arena, accent=(255, 200, 30))

    def draw_arena_garage(self):
        scr, f, ui = self.screen, self.A["afonts"], self.ui
        tr = self.save["truck"]
        self.fx.draw(scr, self.now, self.dt)
        text(scr, f["l"], "TRUCK BOUWEN", (60, 24), (255, 214, 60), shadow=False)
        self.draw_truck_stage((60, 100, 500, 300), 1.7)
        prm = truck_params(tr)
        hop_h = prm["hop"] ** 2 / (2 * GRAV) / 10
        apanel(scr, (60, 414, 500, 52), 170)
        text(scr, f["s"], f"{prm['vmax'] * 0.5:.0f} km/h   hop {hop_h:.0f} m   flip {TAU / prm['flip']:.2f}s   nitro {prm['nitro']:.0f}",
             (310, 440), (255, 214, 160), "center", False)
        ui.button(scr, (60, 480, 240, 48), "WILLEKEURIG", self.truck_random, font="s")
        ui.button(scr, (320, 480, 240, 48), "RESET", self.truck_reset, font="s")
        ui.button(scr, (60, 600, 400, 60), "OPSLAAN & TERUG", lambda: self.goto("arena_hub"), accent=(255, 200, 30))

        x = 600

        def selector(y, label, val, key, n):
            text(scr, f["s"], label, (x, y + 10), (255, 150, 50), shadow=False)
            ui.button(scr, (x + 190, y, 46, 46), "<", lambda: self.truck_cycle(key, -1, n), font="s")
            pygame.draw.rect(scr, ui.theme["field"], (x + 244, y, 260, 46), border_radius=10)
            pygame.draw.rect(scr, ui.theme["field_border"], (x + 244, y, 260, 46), 2, border_radius=10)
            text(scr, f["m"], val, (x + 374, y + 23), (255, 240, 200), "center", False)
            ui.button(scr, (x + 512, y, 46, 46), ">", lambda: self.truck_cycle(key, 1, n), font="s")

        selector(104, "STIJL", TRUCK_STYLES[tr["style"]], "style", len(TRUCK_STYLES))
        text(scr, f["s"], "KLEUR", (x, 170), (255, 150, 50), shadow=False)
        for i, c in enumerate(PALETTE):
            ui.swatch(scr, (x + 190 + (i % 6) * 60, 160 + (i // 6) * 40, 50, 32), c, tr["color"] == i,
                      lambda i=i: self.truck_set("color", i))
        text(scr, f["s"], "ACCENT", (x, 250), (255, 150, 50), shadow=False)
        for i, c in enumerate(ACCENTS):
            ui.swatch(scr, (x + 190 + (i % 8) * 46, 246, 40, 32), c, tr["accent"] == i,
                      lambda i=i: self.truck_set("accent", i))
        selector(296, "STICKERS", TRUCK_DECALS[tr["decal"]], "decal", len(TRUCK_DECALS))
        selector(352, "WIELEN", TRUCK_WHEELS[tr["wheels"]], "wheels", len(TRUCK_WHEELS))
        text(scr, f["s"], "DAKLAMPEN", (x, 418), (255, 150, 50), shadow=False)
        ui.button(scr, (x + 190, 408, 200, 46), "AAN" if tr["lights"] else "UIT",
                  lambda: self.truck_set("lights", 0 if tr["lights"] else 1), selected=bool(tr["lights"]), font="s")

        text(scr, f["s"], "TUNING", (x, 466), (255, 214, 60), shadow=False)
        st = tr["stats"]
        effects = [f"{prm['vmax'] * 0.5:.0f} km/h", f"{hop_h:.0f} m", f"{TAU / prm['flip']:.2f} s", f"{prm['nitro']:.0f}"]
        for i, name in enumerate(TRUCK_STATS):
            y = 490 + i * 44
            text(scr, f["s"], name, (x, y + 8), (255, 236, 210), shadow=False)
            ui.button(scr, (x + 190, y, 38, 38), "-", lambda i=i: self.truck_tune(i, -1), enabled=st[i] > 0, font="s")
            for sg in range(STAT_MAX):
                r = pygame.Rect(x + 236 + sg * 22, y + 5, 18, 28)
                on = sg < st[i]
                pygame.draw.rect(scr, (255, 160, 30) if on else (40, 28, 16), r, border_radius=5)
                pygame.draw.rect(scr, (255, 230, 170) if on else (110, 80, 44), r, 2, border_radius=5)
            ui.button(scr, (x + 236 + STAT_MAX * 22 + 4, y, 38, 38), "+", lambda i=i: self.truck_tune(i, 1),
                      enabled=st[i] < STAT_MAX, font="s")
            text(scr, f["s"], effects[i], (x + 630, y + 19), (255, 214, 160), "midright", False)

    def draw_arena(self):
        a = self.arena
        a.draw(self.screen, self.A)
        if a.state == "finished":
            self.draw_arena_results()
        if self.paused:
            self.draw_arena_pause()

    def draw_arena_pause(self):
        scr, f, ui = self.screen, self.A["afonts"], self.ui
        self.dim(170)
        apanel(scr, (W // 2 - 220, 170, 440, 380), 235)
        text(scr, f["l"], "PAUZE", (W // 2, 190), (255, 214, 60), "midtop", False)
        ui.button(scr, (W // 2 - 190, 280, 380, 64), "HERVATTEN", lambda: self.set_pause(False), accent=(255, 200, 30))
        ui.button(scr, (W // 2 - 190, 358, 380, 64), "OPNIEUW", self.start_arena)
        ui.button(scr, (W // 2 - 190, 436, 380, 64), "NAAR ARENA-MENU", self.leave_arena)

    def draw_arena_results(self):
        scr, f, ui, a = self.screen, self.A["afonts"], self.ui, self.arena
        res = self.arena_result or {}
        self.dim(150)
        cx = W // 2
        apanel(scr, (cx - 340, 50, 680, 630), 238)
        text(scr, f["m"], "TIJD OP!", (cx, 62), (255, 214, 60), "midtop", False)
        p = a.player
        sc = p.score
        if a.mode == 0:
            text(scr, f["s"], "JOUW SCORE", (cx, 128), (255, 150, 50), "midtop", False)
            text(scr, f["xl"], f"{sc.total:,}".replace(",", "."), (cx, 148), (255, 240, 200), "midtop", False)
            if res.get("rank"):
                msg = "NIEUWE HIGHSCORE!" if res["rank"] == 1 else f"PLAATS {res['rank']} IN DE HIGHSCORES"
                text(scr, f["m"], msg, (cx, 262), (120, 255, 150), "midtop", False)
            y0 = 312
        else:
            order = a.ranking()
            rank = order.index(p) + 1
            text(scr, f["l"], "GEWONNEN!" if rank == 1 else f"PLAATS {rank}", (cx, 100),
                 (120, 255, 150) if rank == 1 else (255, 170, 120), "midtop", False)
            for i, t in enumerate(order):
                y = 188 + i * 34
                if t.is_player:
                    hl = pygame.Surface((620, 32), pygame.SRCALPHA)
                    pygame.draw.rect(hl, (255, 200, 40, 50), hl.get_rect(), border_radius=8)
                    scr.blit(hl, (cx - 310, y - 3))
                text(scr, f["s"], f"{i + 1}.", (cx - 290, y), (255, 170, 60), shadow=False)
                pygame.draw.circle(scr, t.color, (cx - 246, y + 12), 8)
                text(scr, f["m"], t.name, (cx - 226, y - 5), (255, 236, 200), shadow=False)
                text(scr, f["xs"], t.score.best[1][:18], (cx - 90, y + 4), (190, 160, 120), shadow=False)
                text(scr, f["m"], f"{t.score.total:,}".replace(",", "."), (cx + 296, y - 5), (255, 240, 200), "topright", False)
            y0 = 188 + len(order) * 34 + 14
            if res.get("rank"):
                text(scr, f["s"], "Je score staat in de highscores!", (cx, y0 - 8), (120, 255, 150), "midtop", False)
                y0 += 22
        b = sc.best
        text(scr, f["s"], "BESTE STUNT", (cx - 300, y0), (255, 150, 50), shadow=False)
        text(scr, f["s"], f"{b[1]}  +{b[0]:,}".replace(",", ".") if b[0] else "-", (cx - 300, y0 + 26), (255, 240, 200), shadow=False)
        if res.get("new_stunt"):
            text(scr, f["s"], "NIEUW RECORD!", (cx + 300, y0), (120, 255, 150), "topright", False)
        n = sc.n
        stats = [("Flips", str(n["flips"])), ("360-draaien", str(n["spins"])), ("Wheelie", f"{n['wheelie']:.1f}s"),
                 ("Auto's platgereden", str(n["crushes"])), ("Over auto's gesprongen", str(n["cars"])), ("Crashes", str(n["crashes"]))]
        for i, (k, v) in enumerate(stats):
            xx = cx - 300 + (i % 2) * 320
            yy = y0 + 70 + (i // 2) * 30
            text(scr, f["s"], k, (xx, yy), (200, 175, 140), shadow=False)
            text(scr, f["s"], v, (xx + 290, yy), (255, 240, 200), "topright", False)
        ui.button(scr, (cx - 320, 600, 310, 64), "OPNIEUW", self.start_arena, accent=(255, 200, 30))
        ui.button(scr, (cx + 10, 600, 310, 64), "ARENA-MENU", self.leave_arena)

    # ---- hoofdlus
    def run(self):
        while True:
            self.dt = self.clock.tick(FPS) / 1000
            self.now += self.dt
            self.sfx.volume = self.save["volume"] / 10
            self.ui.begin()
            for e in pygame.event.get():
                self.handle(e)
            self.update(self.dt)
            self.draw()
            self.ui.end()
            pygame.display.flip()

    def update(self, dt):
        if self.state == "arena" and self.arena and not self.paused:
            self.arena.update(dt, pygame.key.get_pressed())
            if self.arena.state == "finished" and not self.arena_done:
                self.finish_arena()
        elif self.state == "race" and self.race and not self.paused:
            self.race.update(dt, pygame.key.get_pressed())
        elif self.state == "gp_final":
            champ = max(self.gp["points"], key=self.gp["points"].get)
            self.confetti.update(dt, spawn=(champ == "Jij"))

    def draw(self):
        st = self.state
        arena_ui = st.startswith("arena")
        self.ui.f = self.A["afonts"] if arena_ui else self.f
        self.ui.theme = THEME_ARENA if arena_ui else THEME_DEFAULT
        if st == "arena":
            self.draw_arena()
        elif st == "arena_hub":
            self.draw_arena_hub()
        elif st == "arena_garage":
            self.draw_arena_garage()
        elif st == "race":
            self.draw_race()
        elif st == "main":
            self.draw_main()
        elif st == "setup":
            self.draw_setup()
        elif st == "garage":
            self.draw_garage()
        elif st == "settings":
            self.draw_settings()
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
            pygame.draw.line(scr, (86, 34, 56), (s[0] - s[2], s[1]), (s[0], s[1]), 2)

    def draw_stage(self, rect, car, scale=1.3):
        scr = self.screen
        r = pygame.Rect(rect)
        panel(scr, r, 150, 22)
        spot = GLOW["spot"]
        scr.blit(spot, spot.get_rect(center=r.center), special_flags=pygame.BLEND_RGB_ADD)
        rot = pygame.transform.rotozoom(self.car_big(car), (self.now * 32) % 360, scale)
        scr.blit(rot, rot.get_rect(center=(r.centerx, r.centery + int(math.sin(self.now * 2) * 4))))

    # ---- kop met tabbladen (hoofdmenu en instellingen)
    def draw_header(self, active):
        scr, f, ui = self.screen, self.f, self.ui
        pygame.draw.rect(scr, (235, 50, 95), (70, 34, 8, 40))
        text(scr, f["l"], "TOP-DOWN RACER", (92, 26))
        tabs = [("HOME", "main", lambda: self.goto("main")),
                ("GARAGE", "garage", lambda: self.open_garage("main")),
                ("INSTELLINGEN", "settings", lambda: self.goto("settings"))]
        x = 72
        for label, key, fn in tabs:
            tw = f["m"].size(label)[0]
            r = pygame.Rect(x - 6, 100, tw + 12, 44)
            hover = r.collidepoint(ui.mouse)
            on = key == active
            col = (255, 255, 255) if on else ((255, 190, 205) if hover else (170, 140, 152))
            text(scr, f["m"], label, (x, 104), col, shadow=False)
            if on:
                pygame.draw.rect(scr, (235, 50, 95), (x, 138, tw, 3))
            elif hover:
                pygame.draw.rect(scr, (130, 60, 82), (x, 138, tw, 3))
            ui.hit(r, fn)
            x += tw + 50

    # ---- kaarten van het hoofdmenu
    def draw_card(self, i, x, y, w, h, skew, heat):
        f = self.f
        col = CARD_COLORS[i]
        w = int(w)
        sw = w + skew
        surf = pygame.Surface((sw, h), pygame.SRCALPHA)
        top = mix((30, 26, 36), mix(col, (0, 0, 0), 0.18), heat)
        surf.fill(top)
        pygame.draw.polygon(surf, mix(top, (255, 255, 255), 0.10),
                            [(sw * 0.45, 0), (sw * 0.8, 0), (sw * 0.5, h), (sw * 0.15, h)])

        def tone(c):
            return mix(top, c, 0.3 + 0.7 * heat)

        cx, cy = sw // 2 + skew // 4, int(h * 0.40)
        if i == 0:                                                   # geblokte vlag + jouw auto
            sq = 26
            for rr in range(6):
                for cc in range(8):
                    if (rr + cc) % 2 == 0:
                        pygame.draw.rect(surf, mix(top, (255, 255, 255), 0.13),
                                         (sw - 8 * sq + cc * sq, rr * sq, sq, sq))
            car = self.save["car"]
            big = ART.big(car["model"], car["tint"])
            k = min(1.5, (w - 30) / max(1, big.get_width()))
            rot = pygame.transform.rotozoom(big, 14, k)
            rot.set_alpha(int(95 + 160 * heat))
            pygame.draw.ellipse(surf, mix(top, (0, 0, 0), 0.45),
                                (cx - int(big.get_width() * k * 0.45), cy + int(big.get_width() * k * 0.2),
                                 int(big.get_width() * k * 0.9), 26))
            surf.blit(rot, rot.get_rect(center=(cx, cy)))
        elif i == 1:                                                 # trofee
            gold = tone((255, 225, 120))
            dark = tone((200, 140, 40))
            pygame.draw.circle(surf, gold, (cx - 52, cy - 22), 24, 9)
            pygame.draw.circle(surf, gold, (cx + 52, cy - 22), 24, 9)
            pygame.draw.polygon(surf, gold, [(cx - 44, cy - 62), (cx + 44, cy - 62), (cx + 34, cy + 6),
                                             (cx + 12, cy + 32), (cx - 12, cy + 32), (cx - 34, cy + 6)])
            pygame.draw.polygon(surf, dark, [(cx + 8, cy - 62), (cx + 44, cy - 62), (cx + 34, cy + 6),
                                             (cx + 12, cy + 32), (cx + 8, cy + 32)])
            pygame.draw.rect(surf, gold, (cx - 9, cy + 32, 18, 30))
            pygame.draw.rect(surf, dark, (cx - 40, cy + 62, 80, 16), border_radius=4)
        elif i == 2:                                                 # arena: monstertruck met vlammen
            art = get_truck_art(self.save["truck"])
            k = min(1.5, (w - 10) / TRUCK_L)
            img = pygame.transform.rotozoom(art.top, 16, k)
            img.set_alpha(int(110 + 145 * heat))
            glow = tone((255, 150, 30))
            pygame.draw.ellipse(surf, mix(top, (0, 0, 0), 0.45), (cx - int(TRUCK_L * k * 0.42), cy + 52, int(TRUCK_L * k * 0.84), 22))
            for n in range(6):                                       # vlammen onder de truck
                fx = cx - 70 + n * 28
                pygame.draw.polygon(surf, glow, [(fx - 12, cy + 76), (fx, cy + 36 - (n % 2) * 14), (fx + 12, cy + 76)])
            surf.blit(img, img.get_rect(center=(cx, cy)))
        elif i == 3:                                                 # garage: tandwiel
            ring = tone((200, 255, 245))
            pts = []
            for n in range(48):
                a = TAU * n / 48
                rad = 84 if (n // 3) % 2 == 0 else 68
                pts.append((cx + math.cos(a) * rad, cy + 10 + math.sin(a) * rad))
            pygame.draw.polygon(surf, ring, pts)
            pygame.draw.circle(surf, top, (cx, cy + 10), 34)
            pygame.draw.circle(surf, tone((120, 220, 205)), (cx, cy + 10), 34, 6)
        else:                                                        # instellingen: schuifregelaars
            for n, pos in enumerate((0.7, 0.3, 0.55)):
                yy = cy - 40 + n * 56
                pygame.draw.rect(surf, tone((90, 80, 150)), (cx - 90, yy, 180, 10), border_radius=5)
                pygame.draw.rect(surf, tone((200, 190, 255)), (cx - 90, yy, int(180 * pos), 10), border_radius=5)
                pygame.draw.circle(surf, tone((255, 255, 255)), (cx - 90 + int(180 * pos), yy + 5), 15)
                pygame.draw.circle(surf, top, (cx - 90 + int(180 * pos), yy + 5), 7)

        band_h = 86
        pygame.draw.rect(surf, mix((16, 12, 20), mix(col, (0, 0, 0), 0.40), heat), (0, h - band_h, sw, band_h))
        pygame.draw.rect(surf, mix((80, 70, 86), col, heat), (0, h - band_h, sw, 4))
        if heat > 0.5:
            text(surf, f["l"], CARD_NAMES[i], (30, h - band_h + 10))
            text(surf, f["s"], CARD_SUBS[i], (32, h - band_h + 60), (235, 225, 232))
        else:
            text(surf, f["s"], CARD_NAMES[i], (24, h - band_h + 34), (210, 200, 208))

        mask = pygame.Surface((sw, h), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), [(skew, 0), (sw, 0), (w, h), (0, h)])
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(surf, (x, y))
        pygame.draw.polygon(self.screen, mix((200, 40, 80), col, heat) if heat > 0.5 else (200, 40, 80),
                            [(x + skew, y), (x + sw, y), (x + w, y + h), (x, y + h)], 4 if heat > 0.5 else 2)

    def draw_main(self):
        scr, f, ui, s = self.screen, self.f, self.ui, self.save
        self.draw_bg()
        self.draw_header("main")
        gap, skew, h, y = 12, 44, 380, 176

        # welke kaart is actief? (muis eerst, anders de laatst gekozen)
        x = 70
        for i, w in enumerate(self.card_w):
            if pygame.Rect(int(x + skew / 2), y, int(w), h).collidepoint(ui.mouse):
                self.menu_active = i
            x += w + gap
        k = min(1.0, self.dt * 10)
        for i in range(5):
            tw = CARD_W_ACTIVE if i == self.menu_active else CARD_W_IDLE
            self.card_w[i] += (tw - self.card_w[i]) * k
            self.card_heat[i] += ((1.0 if i == self.menu_active else 0.0) - self.card_heat[i]) * k
        x = 70
        for i, w in enumerate(self.card_w):
            self.draw_card(i, x, y, w, h, skew, self.card_heat[i])
            ui.hit((int(x + skew / 2), y, int(w), h), lambda i=i: self.menu_action(i))
            x += w + gap

        lvl = LEVELS[s["level"]]
        text(scr, f["s"], f"Moeilijkheid  {lvl['name']}", (72, 580), lvl["color"])
        extra = f"   -   {s['traffic']} verkeer" if s["env"] == ENV_HIGHWAY else ""
        text(scr, f["s"], f"Auto {s['car']['model'] + 1}   -   {s['bots']} tegenstander(s)   -   "
                          f"{ENV_NAMES[s['env']]}   -   {'Regen' if s['weather'] else 'Droog'}{extra}",
             (72, 606), (190, 170, 182))
        text(scr, f["s"], "Klik op een kaart, of gebruik pijltjes + ENTER   -   1-5 snelkeuze",
             (72, H - 44), (140, 116, 128))
        ui.button(scr, (W - 250, H - 70, 180, 46), "AFSLUITEN", self.quit, font="s")

    def draw_settings(self):
        scr, f, ui = self.screen, self.f, self.ui
        self.draw_bg()
        self.draw_header("settings")
        panel(scr, (70, 176, 520, 330), 160, 18)
        text(scr, f["s"], "SCHERM", (96, 196), (160, 140, 152))
        ui.button(scr, (96, 220, 468, 52), "VOLLEDIG SCHERM  (F11)", self.toggle_fullscreen)
        text(scr, f["s"], "GELUID", (96, 286), (160, 140, 152))
        self.stepper(96, 310, "volume", 0, 10, lambda v: "Uit" if v == 0 else f"Volume {v}", w=468)
        text(scr, f["s"], "OPSLAG", (96, 382), (160, 140, 152))
        ui.button(scr, (96, 406, 468, 52), "KLIK NOGMAALS OM TE WISSEN" if self.confirm_reset else "ALLES WISSEN",
                  self.reset_save, accent=(255, 90, 90), selected=self.confirm_reset)
        text(scr, f["s"], "Zet garage en instellingen terug naar de standaard.", (98, 468), (150, 128, 140))
        panel(scr, (630, 176, 580, 330), 160, 18)
        text(scr, f["s"], "BESTURING", (656, 198), (160, 140, 152))
        rows = [("Pijltjes / WASD", "rijden"), ("SHIFT", "nitro"), ("SPATIE", "handrem"),
                ("T", "terugzetten op de baan"), ("ESC", "pauze"), ("F11", "volledig scherm")]
        for i, (k, v) in enumerate(rows):
            text(scr, f["m"], k, (656, 232 + i * 44), (255, 120, 150))
            text(scr, f["m"], v, (900, 232 + i * 44))
        ui.button(scr, (70, 600, 200, 56), "TERUG", lambda: self.goto("main"))

    # ---- instellingen voor een race / grand prix
    def stepper(self, x, y, key, lo, hi, label, w=300, step=1):
        scr, ui = self.screen, self.ui
        th = ui.theme
        v = self.save[key]
        ui.button(scr, (x, y, 56, 56), "-", lambda: self.adjust(key, -step, lo, hi), enabled=v > lo)
        pygame.draw.rect(scr, th["field"], (x + 64, y, w - 128, 56), border_radius=14)
        pygame.draw.rect(scr, th["field_border"], (x + 64, y, w - 128, 56), 2, border_radius=14)
        text(scr, ui.f["m"], label(v), (x + w // 2, y + 28), anchor="center", shadow=False)
        ui.button(scr, (x + w - 56, y, 56, 56), "+", lambda: self.adjust(key, step, lo, hi), enabled=v < hi)

    def start_drag(self, key, bar, lo, hi):
        self.drag = (key, bar, lo, hi)
        self.apply_drag()

    def apply_drag(self):
        if not self.drag:
            return
        key, bar, lo, hi = self.drag
        frac = clamp((self.ui.mouse[0] - bar.x) / bar.w, 0.0, 1.0)
        self.save[key] = int(round(lo + frac * (hi - lo)))

    def slider(self, x, y, key, lo, hi, label, w=300):
        """Zoals stepper, maar het midden is een balk die je kunt aanklikken en slepen."""
        scr, ui = self.screen, self.ui
        if self.drag and self.drag[0] == key:
            if ui.down:
                self.apply_drag()
            else:
                self.drag = None
        v = self.save[key]
        ui.button(scr, (x, y, 56, 56), "-", lambda: self.adjust(key, -1, lo, hi), enabled=v > lo)
        bar = pygame.Rect(x + 64, y, w - 128, 56)
        th = ui.theme
        pygame.draw.rect(scr, th["field"], bar, border_radius=14)
        fw = int(bar.w * (v - lo) / (hi - lo))
        if fw > 0:
            pygame.draw.rect(scr, th["fill"], (bar.x, bar.y, max(fw, 12), bar.h), border_radius=14)
        pygame.draw.rect(scr, th["field_border"], bar, 2, border_radius=14)
        text(scr, ui.f["m"], label(v), bar.center, anchor="center", shadow=False)
        ui.button(scr, (x + w - 56, y, 56, 56), "+", lambda: self.adjust(key, 1, lo, hi), enabled=v < hi)
        ui.hit(bar, lambda: self.start_drag(key, bar, lo, hi))

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
        hwy = s["env"] == ENV_HIGHWAY
        text(scr, f["s"], "TEGENSTANDERS", (x, 108), (160, 175, 200))
        self.stepper(x, 134, "bots", 1, MAX_BOTS, lambda v: f"{v} bot" if v == 1 else f"{v} bots")
        lkey = "laps_gp" if gp else "laps_q"
        text(scr, f["s"], "RONDES PER RACE", (x, 186), (160, 175, 200))
        self.stepper(x, 212, lkey, 1, 10, lambda v: f"{v} ronden" if v > 1 else "1 ronde")
        text(scr, f["s"], "WEER", (x, 264), (160, 175, 200))
        ui.button(scr, (x, 290, 144, 56), "Droog", lambda: self.set_weather(0), selected=s["weather"] == 0)
        ui.button(scr, (x + 156, 290, 144, 56), "Regen", lambda: self.set_weather(1), selected=s["weather"] == 1)
        text(scr, f["s"], "OMGEVING", (x, 342), (160, 175, 200))
        for k, nm in enumerate(ENV_NAMES):
            ui.button(scr, (x + k * 64, 368, 62, 56), nm, lambda k=k: self.set_env(k),
                      selected=s["env"] == k, font="xs")
        row = 420                                   # volgende vrije rij (label-y)
        if hwy:
            text(scr, f["s"], "VERKEER OP DE SNELWEG", (x, row), (160, 175, 200))
            self.slider(x, row + 26, "traffic", 0, MAX_TRAFFIC,
                        lambda v: "Geen verkeer" if v == 0 else f"{v} auto's")
            row += 78
        if gp:
            text(scr, f["s"], "AANTAL RACES", (x, row), (160, 175, 200))
            self.stepper(x, row + 26, "gp_races", 2, 8, lambda v: f"{v} races")
        else:
            hint = (["Verkeer rijdt in zijn eigen strook.", "Een botsing kost veel snelheid."] if hwy else
                    ["Tokyo = DRIFTEN! Punten voor slijphoek.", "Meeste punten wint. Muur = keten weg."]
                    if s["env"] == ENV_TOKYO else ["Regen = minder grip.", "Off-road = sprongen, modder en muren."])
            for j, line in enumerate(hint):
                text(scr, f["s"], line, (x, row + 4 + j * 22), (150, 165, 195))
        ui.button(scr, (x, 604, 300, 70), "START", self.start_session, accent=(110, 255, 140))

        ui.button(scr, (60, 614, 190, 56), "TERUG", lambda: self.goto("main"))
        ui.button(scr, (260, 614, 210, 56), "GARAGE", lambda: self.open_garage("setup"))

        # voorbeeld van het circuit
        panel(scr, (830, 108, 390, 410), 150, 22)
        text(scr, f["s"], "VOORBEELD VAN HET CIRCUIT", (850, 122), (160, 175, 200))
        scr.blit(self.mm.surf, self.mm.surf.get_rect(center=(1025, 300)))
        text(scr, f["s"], f"Lengte  {self.stats[0]:.2f} km", (852, 468))
        if hwy:
            text(scr, f["s"], f"Rijstroken  {HW_LANES}", (1060, 468))
        else:
            text(scr, f["s"], f"Bochten  {self.stats[1]}", (1060, 468))
        ui.button(scr, (830, 534, 390, 56), "NIEUW CIRCUIT", self.new_preview)
        text(scr, f["s"], "1-5 moeilijkheid  -  N nieuw circuit  -  ENTER start  -  ESC terug",
             (830, 614), (150, 165, 195))

    # ---- garage
    def set_model(self, i):
        self.save["car"]["model"] = i

    def set_tint(self, t):
        self.save["car"]["tint"] = t

    def tune(self, i, d):
        st = self.save["car"]["stats"]
        nv = st[i] + d
        if 0 <= nv <= STAT_MAX:
            st[i] = nv

    def reset_car(self):
        self.save["car"] = json.loads(json.dumps(DEFAULTS["car"]))

    def random_car(self):
        car = self.save["car"]
        car["model"] = random.randrange(NUM_CARS)
        car["tint"] = random.randrange(TINT_STEPS)
        car["stats"] = [random.randint(2, STAT_MAX) for _ in range(4)]

    def draw_garage(self):
        scr, f, ui = self.screen, self.f, self.ui
        car = self.save["car"]
        self.draw_bg()
        text(scr, f["l"], "GARAGE", (60, 30))

        self.draw_stage((60, 100, 520, 290), car, 1.15)
        text(scr, f["s"], f"AUTO {car['model'] + 1} VAN {NUM_CARS}", (82, 118), (160, 175, 200))

        # kleurtint: elk blokje toont hoe de kleur van deze auto wordt
        text(scr, f["s"], "KLEURTINT   (werkt alleen op gekleurde auto's)", (60, 404), (160, 175, 200))
        base = ART.color(car["model"], 0)
        hh, ss, vv = colorsys.rgb_to_hsv(base[0] / 255, base[1] / 255, base[2] / 255)
        for t in range(TINT_STEPS):
            r, g, b = colorsys.hsv_to_rgb((hh + t / TINT_STEPS) % 1.0, ss, vv)
            rect = (60 + int(t * 21.7), 430, 20, 30)
            ui.swatch(scr, rect, (int(r * 255), int(g * 255), int(b * 255)), car["tint"] == t,
                      lambda t=t: self.set_tint(t))
        ui.button(scr, (60, 478, 250, 48), "WILLEKEURIG", self.random_car)
        ui.button(scr, (330, 478, 250, 48), "RESET", self.reset_car)
        ui.button(scr, (60, 614, 260, 60), "OPSLAAN & TERUG", lambda: self.goto(self.garage_from),
                  accent=(110, 255, 140))

        # alle auto's
        x = 620
        text(scr, f["s"], "KIES JE AUTO", (x, 100), (160, 175, 200))
        for i in range(NUM_CARS):
            r = pygame.Rect(x + (i % 10) * 60, 124 + (i // 10) * 84, 56, 80)
            sel = car["model"] == i
            hover = r.collidepoint(ui.mouse)
            pygame.draw.rect(scr, (54, 70, 108) if (sel or hover) else (28, 36, 56), r, border_radius=10)
            pygame.draw.rect(scr, (255, 220, 70) if sel else ((160, 185, 240) if hover else (70, 82, 110)),
                             r, 3 if sel else 2, border_radius=10)
            th = ART.thumb(i)
            scr.blit(th, th.get_rect(center=r.center))
            ui.hit(r, lambda i=i: self.set_model(i))

        # tuning (vrij, zonder punten)
        st = car["stats"]
        text(scr, f["s"], "TUNING   -   stel alles vrij in", (x, 480), (160, 175, 200))
        prm = car_params(st)
        effects = [f"{prm['vmax'] * 0.5:.0f} km/h", f"{(prm['accel'] / BASE_ACCEL - 1) * 100:+.0f}%",
                   f"{(prm['turn'] - 1) * 100:+.0f}%", f"{prm['nitro']:.0f}"]
        for i, name in enumerate(STAT_NAMES):
            y = 506 + i * 46
            text(scr, f["m"], name, (x, y + 4))
            ui.button(scr, (x + 190, y, 40, 40), "-", lambda i=i: self.tune(i, -1), enabled=st[i] > 0)
            for sgm in range(STAT_MAX):
                r = pygame.Rect(x + 238 + sgm * 24, y + 6, 20, 28)
                on = sgm < st[i]
                pygame.draw.rect(scr, (90, 170, 255) if on else (34, 42, 62), r, border_radius=6)
                pygame.draw.rect(scr, (255, 255, 255) if on else (80, 92, 120), r, 2, border_radius=6)
            ui.button(scr, (x + 238 + STAT_MAX * 24 + 4, y, 40, 40), "+", lambda i=i: self.tune(i, 1),
                      enabled=st[i] < STAT_MAX)
            text(scr, f["s"], effects[i], (x + 620, y + 20), (200, 210, 230), "midright")

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
        ui.button(scr, (W // 2 - 190, 280, 380, 64), "HERVATTEN", lambda: self.set_pause(False),
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
            if r.tokyo:
                text(scr, f["s"], f"{r.drift_total(c)} pt", (cx + 310, y + 3), (255, 150, 210), "topright")
            elif c.finished:
                t = fmt(c.finish_time) if i == 0 else f"+{c.finish_time - order[0].finish_time:.1f}s"
                text(scr, f["s"], t, (cx + 310, y + 3), (230, 235, 245), "topright")
            else:
                text(scr, f["s"], f"rijdt nog  ({min(c.laps + 1, r.laps)}/{r.laps})", (cx + 310, y + 3),
                     (150, 165, 195), "topright")
        best = min(p.lap_times) if p.lap_times else None
        text(scr, f["s"], (f"Jouw drift  {r.drift_total(p)} pt      Beste keten  {p.drift_best} pt      Tijd  {fmt(p.finish_time)}"
                           if r.tokyo else f"Jouw tijd  {fmt(p.finish_time)}      Beste ronde  {fmt(best)}"),
             (cx, 196 + len(order) * 36 + 12), (200, 210, 230), "midtop")
        if r.civs:
            text(scr, f["s"], f"Botsingen met verkeer  {r.crashes}",
                 (cx, 196 + len(order) * 36 + 38), (255, 150, 130) if r.crashes else (110, 235, 140), "midtop")
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
            bigc = self.car_big(look)
            kk = 120 / bigc.get_width()
            spr = pygame.transform.rotate(pygame.transform.smoothscale(
                bigc, (120, max(8, int(bigc.get_height() * kk)))), 90)
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
                return dict(model=f["model"], tint=f["tint"])
        return self.save["car"]


def main():
    App().run()


if __name__ == "__main__":
    main()
