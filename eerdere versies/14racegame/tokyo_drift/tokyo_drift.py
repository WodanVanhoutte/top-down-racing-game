"""
東京ドリフト  -  TOKYO DRIFT  -  top-down drift racer in neon Tokyo
====================================================================
Installeren:   py -m pip install pygame-ce        (gewoon 'pygame' werkt ook)
Starten:       py tokyo_drift.py

Deze bestanden moeten in dezelfde map staan:
    tokyo_drift.py   dit bestand: menu's en de hoofdlus
    td_core.py       hulpfuncties, lettertype, geluid en muziek
    td_track.py      de circuits en het tekenen van de stad
    td_race.py       auto's, drift-fysica, bots, effecten en HUD
    cars_sheet.png   de auto's            tokyo_jp.otf   Japans lettertype
    sounds/          motor (DeLorean V6), nitro, banden, botsingen, menu-geluiden
    music/           menu.ogg = muziek in de menu's
                     Zet hier zelf het bestand "It's 2001 and you're drifting in tokyo" (mp3/ogg/wav/flac):
                     dat is de muziek tijdens de race, elke race een ander nummer uit de tracklist.

Besturing in de race
    Pijltjes / WASD   gas, remmen, sturen
    SPATIE            handrem (begin een drift)
    SHIFT             nitro (driften vult de nitro bij)
    R                 terug op de weg zetten
    ESC               pauze        M  muziek aan/uit        F11  volledig scherm
"""
import math
import random
import sys

import pygame

from td_core import (AMBER, CARS, FPS, H, J, JB, NEON, NEON_NAMES, PINK, STAT_NAMES, W, WHITE,
                     YELLOW, CarArt, Sfx, clamp, dim, fmt_pts, fmt_time, font, glow, load_save, make_cone, make_edge_glow,
                     make_scanlines, make_vignette, metal, mix, text, write_save)
from td_race import MODES, Race, medal_for
from td_track import COURSES, Track

ORANGE = (255, 122, 0)          # accentkleuren van de menu's (stijl: drift-games van begin jaren 2000)
BLUE = (90, 180, 255)
GREY = (150, 156, 170)
DARK = (10, 11, 16)


def slant(s, color, x, y, w, h, skew=16):
    """Schuin vlak (parallellogram): het typische vormpje van racemenu's uit de jaren 2000."""
    pygame.draw.polygon(s, color, [(x + skew, y), (x + w + skew, y), (x + w, y + h), (x, y + h)])


def plate(s, rect, accent=ORANGE, alpha=215):
    """Donker doorschijnend paneel met een gekleurde lijn bovenaan."""
    r = pygame.Rect(rect)
    box = pygame.Surface(r.size, pygame.SRCALPHA)
    box.fill((*DARK, alpha))
    s.blit(box, r.topleft)
    pygame.draw.rect(s, (58, 62, 74), r, 1)
    pygame.draw.rect(s, accent, (r.x, r.y, r.w, 3))
    slant(s, accent, r.right - 46, r.y + 3, 30, 6, 6)


# ------------------------------------------------------------------ bewegende menu-achtergrond
class MenuBG:
    """Een natte parking bij nacht, van bovenaf gezien. Je gekozen auto drift er rondjes (donuts) met rook."""
    CX, CY, R = 900, 380, 130

    def __init__(self):
        rnd = random.Random(5)
        f = pygame.Surface((W, H))
        f.fill((15, 16, 22))
        for _ in range(9000):                                 # korrel in het asfalt
            d = rnd.randint(-5, 6)
            f.set_at((rnd.randrange(W), rnd.randrange(H)), (18 + d, 19 + d, 26 + d))
        for x in range(-40, W, 88):                           # parkeervakken boven en onder
            for y0, y1 in ((0, 150), (H - 150, H)):
                pygame.draw.line(f, (70, 72, 80), (x, y0), (x, y1), 3)
        pygame.draw.line(f, (70, 72, 80), (0, 150), (W, 150), 3)
        pygame.draw.line(f, (70, 72, 80), (0, H - 150), (W, H - 150), 3)
        for x, y, col in ((250, 300, (40, 30, 14)), (900, 380, (30, 36, 50)), (1180, 120, (40, 30, 14)), (560, 640, (14, 30, 44))):
            f.blit(glow(760, col, 1.5), (x - 380, y - 380), special_flags=pygame.BLEND_RGB_ADD)   # lantaarns
        for _ in range(26):                                   # plassen die het licht weerkaatsen
            x, y = rnd.randrange(W), rnd.randrange(160, H - 160)
            pygame.draw.ellipse(f, (24, 28, 40), (x, y, rnd.randint(40, 150), rnd.randint(14, 44)))
        for k in range(40):                                   # oude bandensporen van de donuts
            r = self.R + rnd.randint(-40, 44)
            a0, n = rnd.uniform(0, 6.28), rnd.randint(14, 50)
            ox, oy = rnd.randint(-12, 12), rnd.randint(-12, 12)
            pts = [(self.CX + ox + math.cos(a0 + j * 0.07) * r, self.CY + oy + math.sin(a0 + j * 0.07) * r * 0.92) for j in range(n)]
            pygame.draw.lines(f, (9, 9, 13), False, pts, rnd.choice([3, 4, 5]))
        self.floor = f
        shade = pygame.Surface((W, H), pygame.SRCALPHA)       # links donkerder, zodat de tekst leesbaar blijft
        for x in range(0, W, 4):
            a = int(215 * clamp(1 - (x - 260) / 520, 0, 1))
            pygame.draw.rect(shade, (6, 7, 10, a), (x, 0, 4, H))
        self.shade = shade
        self.puff = []
        for size in (20, 30, 44, 60, 80, 104):
            img = pygame.Surface((size, size), pygame.SRCALPHA)
            for r in range(size // 2, 0, -1):
                pygame.draw.circle(img, (200, 204, 216, int(120 * (1 - r / (size / 2)) ** 0.8)), (size // 2, size // 2), r)
            self.puff.append(img)
        self.cone = make_cone(260, 17)
        self.smoke = []                                       # [x, y, vx, vy, leeftijd]
        self.t = 0.0

    def draw(self, s, dt, sprite=None, neon=WHITE, speed=1.0, dark=0):
        self.t += dt * speed
        s.blit(self.floor, (0, 0))
        if sprite:
            a = self.t * 1.7
            x, y = self.CX + math.cos(a) * self.R, self.CY + math.sin(a) * self.R * 0.92
            head = a + math.pi / 2 + 0.95                     # de neus wijst naar binnen: de auto drift
            fx, fy = math.cos(head), math.sin(head)
            for side in (-16, 16):                            # rook van de achterwielen
                self.smoke.append([x - fx * 34 - fy * side, y - fy * 34 + fx * side, -fx * 30 + random.uniform(-14, 14),
                                   -fy * 30 + random.uniform(-14, 14), 0.0])
            s.blit(glow(260, dim(neon, 0.55), 1.5), (x - 130, y - 130), special_flags=pygame.BLEND_RGB_ADD)
            cone = pygame.transform.rotate(self.cone, -math.degrees(head))
            s.blit(cone, cone.get_rect(center=(x + fx * 30, y + fy * 30)), special_flags=pygame.BLEND_RGB_ADD)
            img = pygame.transform.rotozoom(sprite, -math.degrees(head), 0.62)
            s.blit(img, img.get_rect(center=(x, y)))
            for sd in (-1, 1):                                # achterlichten
                s.blit(glow(40, (200, 20, 16), 1.4), (x - fx * 50 - fy * 15 * sd - 20, y - fy * 50 + fx * 15 * sd - 20),
                       special_flags=pygame.BLEND_RGB_ADD)
        for p in self.smoke:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] += dt
            f = p[4] / 2.2
            if f < 1:
                img = self.puff[min(5, int(f * 6))]
                img.set_alpha(int(110 * (1 - f)))
                s.blit(img, (p[0] - img.get_width() / 2, p[1] - img.get_height() / 2))
        self.smoke = [p for p in self.smoke if p[4] < 2.2] if sprite else []
        s.blit(self.shade, (0, 0))
        if dark:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((6, 7, 10, dark))
            s.blit(veil, (0, 0))


# ------------------------------------------------------------------ het spel
class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("東京ドリフト  TOKYO DRIFT")
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.save = load_save()
        self.screen.fill(DARK)
        text(self.screen, "NOW LOADING...", 30, (W // 2, H // 2), WHITE, "center", True, True)
        text(self.screen, J("サウンドを読込中", "GELUID LADEN"), 18, (W // 2, H // 2 + 44), GREY, "center", True)
        pygame.display.flip()
        self.sfx = Sfx()
        self.apply_audio()
        self.art = CarArt()
        self.assets = dict(cone=make_cone(), red=glow(34, (255, 40, 30), 1.4), red_dim=glow(22, (150, 16, 14), 1.5),
                           blue=glow(64, (80, 170, 255), 1.4), edge_blue=make_edge_glow((20, 70, 130)),
                           edge_red=make_edge_glow((150, 10, 20)), vignette=make_vignette(), scan=make_scanlines(),
                           white=pygame.Surface((W, H)))
        self.assets["white"].fill((255, 255, 255))
        self.bg = MenuBG()
        self.tracks = [Track(c) for c in COURSES]
        self.maps = [t.minimap((176, 104), BLUE, ORANGE, 2)[0] for t in self.tracks]        # kleine kaartjes
        self.big_maps = [t.minimap((400, 236), BLUE, ORANGE, 4)[0] for t in self.tracks]    # grote kaart van de keuze
        self.state = "title"
        self.sel = 0                    # gekozen regel in het huidige menu
        self.mode = "drift"
        self.race = None
        self.t = 0.0
        self.loader = None
        self.load_msg = ""
        self.result = None
        self.sfx.play_menu_music()

    def apply_audio(self):
        self.sfx.volume = self.save["volume"] / 10
        self.sfx.music_vol = self.save["music_vol"] / 10
        self.sfx.engine_vol = self.save["engine"] / 5         # 5 = normaal
        self.sfx.music_on = bool(self.save["music"])

    def go(self, state, sel=0):
        self.state, self.sel = state, sel

    # ------------------------------------------------------------ invoer
    def key(self, k):
        s, sfx = self.save, self.sfx
        up, down = k in (pygame.K_UP, pygame.K_w), k in (pygame.K_DOWN, pygame.K_s)
        left, right = k in (pygame.K_LEFT, pygame.K_a), k in (pygame.K_RIGHT, pygame.K_d)
        ok, back = k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE), k == pygame.K_ESCAPE
        dx = (1 if right else 0) - (1 if left else 0)
        if k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_m:
            s["music"] = 1 - s["music"]
            self.apply_audio()
        elif self.state == "title":
            if back:
                self.quit()
            else:
                sfx.play("ok")
                self.go("menu")
        elif self.state == "menu":
            if up or down:
                self.sel = (self.sel + (1 if down else -1)) % 5
                sfx.play("move")
            elif ok:
                sfx.play("ok")
                if self.sel < 2:
                    self.mode = ("drift", "race")[self.sel]
                    self.go("course")
                elif self.sel == 4:
                    self.quit()
                else:
                    self.go(("garage", "options")[self.sel - 2])
            elif back:
                sfx.play("back")
                self.go("title")
        elif self.state == "course":
            rows = 4 if self.mode == "race" else 3
            if up or down:
                self.sel = (self.sel + (1 if down else -1)) % rows
                sfx.play("move")
            elif dx:
                sfx.play("move")
                row = self.sel if self.mode == "race" or self.sel < 2 else 3
                if row == 0:
                    s["course"] = (s["course"] + dx) % len(COURSES)
                elif row == 1:
                    s["laps"] = int(clamp(s["laps"] + dx, 1, 9))
                elif row == 2:
                    s["bots"] = int(clamp(s["bots"] + dx, 1, 5))
                else:
                    s["weather"] = 1 - s["weather"]
            elif ok:
                sfx.play("ok")
                self.start_race()
            elif back:
                sfx.play("back")
                self.go("menu", 0 if self.mode == "drift" else 1)
        elif self.state == "garage":
            if dx:
                s["car"] = (s["car"] + dx) % len(CARS)
                sfx.play("move")
            elif up or down:
                s["glow"] = (s["glow"] + (1 if down else -1)) % len(NEON)
                sfx.play("move")
            elif ok or back:
                sfx.play("ok" if ok else "back")
                write_save(s)
                self.go("menu", 2)
        elif self.state == "options":
            if up or down:
                self.sel = (self.sel + (1 if down else -1)) % 4
                sfx.play("move")
            elif dx or (ok and self.sel == 3):
                d = dx or 1
                if self.sel < 3:
                    name = ("volume", "music_vol", "engine")[self.sel]
                    s[name] = int(clamp(s[name] + d, 0, 10))
                    if name == "music_vol":
                        s["music"] = 1                        # muziek weer aan als je het volume verandert
                else:
                    pygame.display.toggle_fullscreen()
                self.apply_audio()
                sfx.play("move")
            elif back or ok:
                sfx.play("back")
                write_save(s)
                self.go("menu", 3)
        elif self.state == "race":
            if back:
                self.sfx.loops(mute=True)
                self.go("pause")
            elif k == pygame.K_r and not self.race.player.finished:
                self.race.player.respawn(self.race.t)
            elif ok and self.race.done and self.race.done_t > 1.0:
                self.finish_race()
        elif self.state == "pause":
            if up or down:
                self.sel = (self.sel + (1 if down else -1)) % 3
                sfx.play("move")
            elif back or (ok and self.sel == 0):
                self.go("race")
            elif ok and self.sel == 1:
                self.start_race()
            elif ok:
                self.end_race()
        elif self.state == "result":
            if ok:
                sfx.play("ok")
                self.start_race()
            elif back:
                sfx.play("back")
                self.end_race()

    def click(self, pos):
        """Muis: klikken op een menuregel kiest ze, elders klikken = Enter."""
        if self.state in ("menu", "pause", "options"):
            for k, r in enumerate(self.hit):
                if r.collidepoint(pos):
                    self.sel = k
        if self.state == "course":
            for k, r in enumerate(self.hit):
                if r.collidepoint(pos):
                    self.save["course"] = k
                    self.sel = 0
                    return
        if self.state != "race":
            self.key(pygame.K_RETURN)

    hit = []

    def quit(self):
        write_save(self.save)
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------ race starten / stoppen
    def start_race(self):
        self.sfx.stop_loops()
        self.sfx.stop_music()                                # de menu-muziek sterft weg tijdens het laden
        write_save(self.save)
        self.track = self.tracks[self.save["course"]]
        self.loader = self.track.build()
        self.go("loading")

    def end_race(self):
        self.sfx.stop_loops()
        self.race = None
        self.sfx.play_menu_music()
        for t in self.tracks:                                # geheugen vrijmaken
            t.world = None
            t.tiles = {}
        self.go("menu", 0 if self.mode == "drift" else 1)

    def finish_race(self):
        """Na de finish: uitslag berekenen en het record bewaren."""
        r, s = self.race, self.save
        p = r.player
        key = f"{r.mode}-{s['course']}-{r.laps}"
        old = s["best"].get(key)
        if r.mode == "drift":
            value, new = r.score, old is None or r.score > old
        else:
            value, new = round(p.finish_time, 2), old is None or p.finish_time < old
        if new:
            s["best"][key] = value
            write_save(s)
        self.result = dict(new=new, old=old, pos=r.position(), table=r.standings())
        self.sfx.loops(mute=True)
        self.go("result")

    # ------------------------------------------------------------ hoofdlus
    def step(self, dt, events):
        self.t += dt
        for e in events:
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.KEYDOWN:
                self.key(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.click(e.pos)
        if self.state == "loading":
            try:
                self.load_msg = next(self.loader)
            except StopIteration:
                r = self.save
                self.race = Race(self, self.track, self.mode, r["laps"], r["bots"], bool(r["weather"]))
                title = self.sfx.play_race_music()            # elke race een ander nummer
                if title:
                    self.race.banner = ["♪ 音楽", title.upper(), PINK, 0.0]
                self.go("race")
        elif self.state == "race":
            self.race.update(dt, pygame.key.get_pressed())
            if self.race.done and self.race.done_t > 4.0:
                self.finish_race()
        elif self.state == "result":
            self.race.update(dt, pygame.key.get_pressed())    # de auto's rijden door op de achtergrond
            self.sfx.loops(mute=True)
        self.sfx.update_music(0.4 if self.state == "pause" else 1.0, dt)

    def draw(self):
        s = self.screen
        st = self.state
        if st in ("race", "pause", "result"):
            self.race.draw(s)
            if st == "pause":
                self.draw_pause(s)
            elif st == "result":
                self.draw_result(s)
        else:
            car = self.art.big[CARS[self.save["car"]][0]]
            show = st in ("title", "menu", "options")        # op de andere schermen staat er een paneel voor
            self.bg.draw(s, 1 / FPS, car if show else None, NEON[self.save["glow"]], dark=0 if show else 120)
            getattr(self, "draw_" + st)(s)

    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            self.step(dt, pygame.event.get())
            self.draw()
            pygame.display.flip()

    # ------------------------------------------------------------ schermen
    def logo(self, s, x, y, size=96):
        """TOKYO in staal, DRIFT in oranje, met schuine strepen ervoor."""
        for k in range(3):
            slant(s, dim(ORANGE, 1 - 0.28 * k), x + k * 22, y + size * 0.42, 14, size * 0.8, int(size * 0.3))
        a, b = metal("TOKYO", size), metal("DRIFT", size, AMBER)
        tx = x + 84 + int(size * 0.3)
        s.blit(a, (tx, y))
        s.blit(b, (tx + int(size * 0.5), y + int(size * 0.86)))
        text(s, J("東 京 ド リ フ ト", "STREET DRIFT"), int(size * 0.24), (tx + 6, y - int(size * 0.2)), GREY, bold=True)
        w = a.get_width() + int(size * 0.6)
        pygame.draw.line(s, ORANGE, (tx, y + size * 2.12), (tx + w, y + size * 2.12), 3)
        text(s, "STREET DRIFT RACING   //   WANGAN  -  SHUTOKO  -  TOUGE", max(12, int(size * 0.15)), (tx, y + size * 2.2), GREY,
             bold=True, italic=True)

    def top_bar(self, s, title_jp, title, hint):
        bar = pygame.Surface((W, 70), pygame.SRCALPHA)
        bar.fill((*DARK, 230))
        s.blit(bar, (0, 16))
        for k in range(3):
            slant(s, dim(ORANGE, 1 - 0.28 * k), 26 + k * 16, 26, 9, 50, 12)
        s.blit(metal(title, 38), (96, 26))
        text(s, J(title_jp, ""), 26, (W - 40, 34), GREY, "topright", True)
        pygame.draw.line(s, ORANGE, (0, 86), (W, 86), 2)
        bar = pygame.Surface((W, 36), pygame.SRCALPHA)
        bar.fill((*DARK, 230))
        s.blit(bar, (0, H - 52))
        pygame.draw.line(s, (58, 62, 74), (0, H - 52), (W, H - 52), 1)
        text(s, hint, 16, (W // 2, H - 46), GREY, "midtop", True, shadow=None)

    def wrap(self, s, words, size, x, y, width, color=WHITE, step=24):
        """Tekst die automatisch naar een nieuwe regel gaat als ze te breed wordt."""
        line = ""
        for word in words.split():
            if font(size).size(line + " " + word)[0] > width:
                text(s, line, size, (x, y), color)
                y += step
                line = word
            else:
                line = (line + " " + word).strip()
        text(s, line, size, (x, y), color)

    def missing_music(self, s, y):
        """Waarschuwing als het muziekbestand voor de race niet gevonden is."""
        if not self.sfx.race_file:
            text(s, "RACE-MUZIEK NIET GEVONDEN: zet \"It's 2001 and you're drifting in tokyo\" in de map music",
                 15, (W // 2, y), YELLOW, "midtop", True)

    def draw_title(self, s):
        text(s, "TOKYO METROPOLITAN AREA   //   SHUTO EXPRESSWAY   //   AM 02:47", 14, (60, 40), GREY, bold=True, italic=True)
        pygame.draw.line(s, (58, 62, 74), (60, 64), (640, 64), 1)
        self.logo(s, 60, 250)
        pulse = 0.8 + 0.2 * math.sin(self.t * 3.2)
        slant(s, dim(ORANGE, pulse), 160, 560, 300, 44, 14)
        text(s, "PRESS ENTER", 24, (322, 568), (16, 12, 8), "midtop", True, True, shadow=None)
        text(s, J("エンターキーを押してください", ""), 14, (322, 612), GREY, "midtop", True)
        best = max([v for k, v in self.save["best"].items() if k.startswith("drift")] or [0])
        text(s, f"BEST DRIFT   {fmt_pts(best)} PTS", 15, (W - 60, 40), GREY, "topright", True, True)
        self.missing_music(s, H - 40)

    def menu_list(self, s, items, x, y, step=58, size=30):
        """Lijst met menuregels; de gekozen regel krijgt een schuine oranje balk."""
        self.hit = []
        for k, item in enumerate(items):
            lat, jp = item[1], item[2] if len(item) > 2 else J(item[0], "")     # 3e waarde = tekst rechts (bv. volumebalk)
            yy = y + k * step
            on = k == self.sel
            self.hit.append(pygame.Rect(x - 20, yy - 4, 540, step - 6))
            text(s, f"{k + 1:02d}", 14, (x - 4, yy + 14), ORANGE if on else (86, 90, 104), bold=True, italic=True, shadow=None)
            if on:
                w = 470 + int(6 * math.sin(self.t * 6))
                slant(s, ORANGE, x + 26, yy - 2, w, step - 14, 14)
                slant(s, (255, 190, 90), x + 26 + w + 8, yy - 2, 10, step - 14, 14)
                text(s, lat, size, (x + 56, yy + 1), (14, 10, 6), bold=True, italic=True, shadow=None)
                text(s, jp, 16, (x + 26 + w - 14, yy + 12), (90, 44, 0), "topright", True, shadow=None)
            else:
                text(s, lat, size - 4, (x + 56, yy + 4), (176, 182, 196), bold=True, italic=True)
                text(s, jp, 14, (x + 480, yy + 14), (86, 90, 104), "topright", True, shadow=None)

    def draw_menu(self, s):
        self.logo(s, 40, 50, 54)
        items = [MODES["drift"], MODES["race"], ("ガレージ", "GARAGE"), ("オプション", "OPTIONS"), ("終了", "EXIT")]
        self.menu_list(s, items, 70, 250)
        info = ["Scoor zoveel mogelijk driftpunten. Lange drifts, wissels en clipping points geven een hogere multiplier.",
                "Race tegen bots door nachtelijk Tokyo. Driften vult je nitro bij.",
                "Kies je auto en de kleur van de neon onder de wagen.",
                "Volume van effecten, muziek en motor, en volledig scherm.",
                "Terug naar de echte wereld."][self.sel]
        plate(s, (60, 566, 560, 86))
        self.wrap(s, info, 17, 78, 580, 520)
        car = CARS[self.save["car"]]
        plate(s, (W - 330, 566, 270, 86), BLUE)
        text(s, "YOUR MACHINE", 13, (W - 314, 578), BLUE, bold=True, italic=True)
        s.blit(metal(car[2], 30), (W - 316, 598))
        text(s, J(car[1], ""), 16, (W - 76, 576), GREY, "topright", True)
        text(s, "↑↓ kiezen    ENTER ok    ESC terug    M muziek    F11 volledig scherm", 15, (W // 2, H - 30), GREY, "midtop", True)
        self.missing_music(s, 14)

    def draw_course(self, s):
        sv = self.save
        self.top_bar(s, "コース選択", "COURSE SELECT  /  " + MODES[self.mode][1],
                     "←→ circuit    ↑↓ regel    ENTER start    ESC terug")
        self.hit = []
        n = len(COURSES)
        cw = (W - 80) // n
        for k, c in enumerate(COURSES):                       # rij met alle circuits
            on = k == sv["course"]
            r = pygame.Rect(40 + k * cw, 100, cw - 10, 150)
            self.hit.append(r)
            plate(s, r, ORANGE if on else (58, 62, 74), 235 if on else 170)
            if on and self.sel == 0:
                pygame.draw.rect(s, ORANGE if int(self.t * 4) % 2 else WHITE, r, 2)
            m = self.maps[k]
            if not on:
                m = m.copy()
                m.set_alpha(120)
            s.blit(m, m.get_rect(center=(r.centerx, r.y + 62)))
            text(s, c["name"], 14, (r.centerx, r.y + 120), WHITE if on else GREY, "midtop", True, True)
        c, tr = COURSES[sv["course"]], self.tracks[sv["course"]]
        plate(s, (40, 262, W - 80, 262))                      # details van het gekozen circuit
        s.blit(self.big_maps[sv["course"]], (56, 276))
        s.blit(metal(J(c["jp"], c["name"]), 46), (490, 276))
        text(s, c["name"], 24, (494, 336), ORANGE, bold=True, italic=True)
        self.wrap(s, c["desc"], 16, 494, 370, 700, step=22)
        rows = [(JB("難易度", "NIVEAU"), "★" * c["diff"] + "☆" * (3 - c["diff"])), (JB("距離", "LENGTE"), f"{tr.length_m} m"),
                (JB("高架", "VERHOOGD"), f"{tr.elev_pct} %")]
        best = sv["best"].get(f"{self.mode}-{sv['course']}-{sv['laps']}")
        rows.append((JB("記録", "RECORD"), "---" if best is None else (fmt_pts(best) if self.mode == "drift" else fmt_time(best))))
        for k, (a, b) in enumerate(rows):
            x = 494 + k * 180
            text(s, a, 13, (x, 420), GREY, bold=True)
            text(s, b, 24, (x, 440), YELLOW if k == 0 else WHITE, bold=True, italic=True)
        pygame.draw.line(s, BLUE, (494, 496), (522, 496), 4)
        text(s, "straat", 13, (528, 487), BLUE, bold=True)
        pygame.draw.line(s, ORANGE, (590, 496), (618, 496), 4)
        text(s, "verhoogd", 13, (624, 487), ORANGE, bold=True)
        rows = [("ラップ", "RONDEN", str(sv["laps"]))]
        if self.mode == "race":
            rows.append(("ライバル", "TEGENSTANDERS", str(sv["bots"])))
        rows.append(("天気", "WEER", J("雨 REGEN", "REGEN") if sv["weather"] else J("晴れ HELDER", "HELDER")))
        for k, (jp, lat, val) in enumerate(rows):
            x = W // 2 - len(rows) * 180 + k * 360 + 20
            on = self.sel == k + 1
            plate(s, (x, 540, 320, 78), ORANGE if on else (58, 62, 74))
            text(s, f"{J(jp, '')}  {lat}", 14, (x + 160, 550), ORANGE if on else GREY, "midtop", True)
            text(s, f"◀  {val}  ▶" if on else val, 26, (x + 160, 572), WHITE if on else GREY, "midtop", True, True)

    def draw_garage(self, s):
        sv = self.save
        self.top_bar(s, "マシン選択", "GARAGE  /  SELECT YOUR MACHINE", "←→ auto    ↑↓ neonkleur    ENTER ok")
        car = CARS[sv["car"]]
        col = NEON[sv["glow"]]
        cx, cy = 400, 340
        for r, a in ((230, 0.12), (190, 0.2), (150, 0.3)):   # draaischijf
            pygame.draw.ellipse(s, dim(col, a), (cx - r, cy + 40 - r * 0.42, 2 * r, r * 0.84), 3)
        s.blit(glow(460, dim(col, 0.6), 1.4), (cx - 230, cy - 230), special_flags=pygame.BLEND_RGB_ADD)
        img = pygame.transform.rotozoom(self.art.big[car[0]], self.t * 40 % 360, 1.6)
        s.blit(img, img.get_rect(center=(cx, cy)))
        for k in range(len(CARS)):                            # kleine rij met alle auto's
            th = self.art.spr[CARS[k][0]]
            x = cx - len(CARS) * 34 + k * 68 + 34
            if k == sv["car"]:
                slant(s, ORANGE, x - 36, 562, 64, 44, 8)
            s.blit(th, th.get_rect(center=(x, 584)))
        text(s, "◀", 44, (70, cy - 26), ORANGE, bold=True)
        text(s, "▶", 44, (700, cy - 26), ORANGE, bold=True)
        plate(s, (790, 108, 440, 510))
        text(s, J(car[1], car[2]), 56, (1010, 118), WHITE, "midtop", True)
        s.blit(metal(car[2], 38, AMBER), (812, 200))
        for k, (jp, lat) in enumerate(STAT_NAMES):
            y = 276 + k * 60
            text(s, f"{J(jp, '')}  {lat}", 15, (812, y), GREY, bold=True)
            for b in range(10):
                on = b < car[3][k]
                slant(s, mix(BLUE, ORANGE, b / 9) if on else (40, 43, 52), 812 + b * 40, y + 26, 30, 18, 8)
        text(s, J("ネオン", "NEON") + "  ▲▼", 15, (812, 524), GREY, bold=True)
        for k, c in enumerate(NEON):
            r = pygame.Rect(812 + k * 50, 550, 40, 40)
            pygame.draw.rect(s, c, r)
            if k == sv["glow"]:
                pygame.draw.rect(s, WHITE, r.inflate(10, 10), 3)
        text(s, NEON_NAMES[sv["glow"]] if J("x", "") else NEON_NAMES[sv["glow"]].split()[-1], 15, (1216, 524), col, "topright", True)

    def draw_options(self, s):
        sv = self.save

        def bar(v):
            return "■" * v + "□" * (10 - v)
        self.top_bar(s, "オプション", "OPTIONS", "↑↓ kiezen    ←→ wijzigen    ESC terug")
        items = [("効果音", "EFFECTEN", bar(sv["volume"])),
                 ("音楽", "MUZIEK" + ("" if sv["music"] else " (UIT)"), bar(sv["music_vol"])),
                 ("エンジン", "MOTOR", bar(sv["engine"])),
                 ("全画面", "VOLLEDIG SCHERM", "F11")]
        self.menu_list(s, items, 70, 170, 74, 26)
        plate(s, (60, 520, 760, 96), BLUE)
        text(s, "RACE:  pijltjes/WASD rijden  -  SPATIE handrem  -  SHIFT nitro  -  R terugzetten  -  ESC pauze", 15, (78, 536), WHITE, bold=True)
        text(s, "DRIFT:  stuur in, tik de handrem aan en geef gas. Stuur tegen om de drift vast te houden.", 15, (78, 562), BLUE, bold=True)
        text(s, "M = muziek aan/uit", 15, (78, 588), GREY, bold=True)

    def draw_loading(self, s):
        c = COURSES[self.save["course"]]
        plate(s, (0, 250, W, 220))
        for k in range(3):
            slant(s, dim(ORANGE, 1 - 0.28 * k), 70 + k * 22, 280, 14, 160, 40)
        s.blit(metal(J(c["jp"], c["name"]), 64), (200, 268))
        text(s, c["name"], 28, (204, 350), ORANGE, bold=True, italic=True)
        dots = "." * (int(self.t * 6) % 4)
        text(s, "LOADING" + dots, 20, (204, 400), WHITE, bold=True, italic=True)
        text(s, self.load_msg, 16, (204, 430), GREY, bold=True)
        s.blit(self.big_maps[self.save["course"]], (W - 470, 242))

    def draw_pause(self, s):
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((6, 0, 20, 170))
        s.blit(dark, (0, 0))
        img = metal(J("一時停止", "PAUSE"), 72)
        s.blit(img, img.get_rect(center=(W // 2, 180)))
        text(s, "PAUSE", 24, (W // 2, 232), ORANGE, "midtop", True, True)
        self.menu_list(s, [("続ける", "VERDER RIJDEN"), ("やり直す", "OPNIEUW"), ("メニュー", "NAAR MENU")], W // 2 - 250, 310)

    def draw_result(self, s):
        r, res = self.race, self.result
        p = r.player
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((6, 0, 20, 185))
        s.blit(dark, (0, 0))
        self.top_bar(s, "結果", "RESULT  -  " + r.t.spec["name"], "ENTER opnieuw    ESC menu")
        plate(s, (240, 120, 800, 480))
        if r.mode == "drift":
            name, col, need = medal_for(r.score, r.t, r.laps)
            text(s, JB("ドリフトスコア", "DRIFT SCORE"), 22, (W // 2, 136), GREY, "midtop", True)
            img = metal(fmt_pts(r.score), 104, AMBER, o=3)
            s.blit(img, img.get_rect(center=(W // 2, 230)))
            text(s, name or JB("メダルなし", "GEEN MEDAILLE"), 40, (W // 2, 300), col, "midtop", True)
            rows = [(JB("最高チェーン", "BESTE KETEN"), fmt_pts(r.best_chain)), (JB("クリップ", "CLIPPING POINTS"), str(r.clips)),
                    (JB("タイム", "TIJD"), fmt_time(p.finish_time)),
                    (JB("前の記録", "VORIG RECORD"), "---" if res["old"] is None else fmt_pts(res["old"]))]
        else:
            pos = res["pos"]
            col = (YELLOW, (210, 220, 235), (225, 140, 80))[pos - 1] if pos <= 3 else WHITE
            img = metal(f"{pos}", 124, ((255, 255, 255), col), o=3)
            s.blit(img, img.get_rect(center=(W // 2 - 60, 210)))
            text(s, J("位", "e"), 50, (W // 2 + 10, 200), col, bold=True)
            text(s, JB("優勝!!", "GEWONNEN!!") if pos == 1 else JB("ゴール", "FINISH"), 34, (W // 2, 290), col, "midtop", True)
            rows = [(JB("タイム", "TIJD"), fmt_time(p.finish_time)), (JB("ベストラップ", "BESTE RONDE"), fmt_time(min(p.lap_times))),
                    (JB("ドリフト", "DRIFTPUNTEN"), fmt_pts(r.score)),
                    (JB("前の記録", "VORIG RECORD"), "---" if res["old"] is None else fmt_time(res["old"]))]
            for k, c in enumerate(res["table"]):
                tm = fmt_time(c.finish_time) if c.finished else "DNF"
                text(s, f"{k + 1}. {c.name}", 17, (790, 150 + k * 26), YELLOW if c.is_player else WHITE, bold=True)
                text(s, tm, 17, (1020, 150 + k * 26), YELLOW if c.is_player else GREY, "topright", True)
        for k, (a, b) in enumerate(rows):
            y = 372 + k * 40
            text(s, a, 22, (330, y), GREY, bold=True)
            text(s, b, 26, (950, y - 2), WHITE, "topright", True, True)
            pygame.draw.line(s, (58, 62, 74), (330, y + 34), (950, y + 34), 1)
        if res["new"] and int(self.t * 4) % 2:
            img = metal(JB("新記録!!", "NEW RECORD!!"), 42, AMBER)
            s.blit(img, img.get_rect(center=(W // 2, 566)))


if __name__ == "__main__":
    App().run()
