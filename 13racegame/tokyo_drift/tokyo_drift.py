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
    music/           menu.ogg (menu-muziek) + de mix "It's 2001 and you're drifting in tokyo"
                     voor tijdens de race: zet dat bestand zelf in deze map

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

from td_core import (CARS, CYAN, FPS, GREEN, H, J, JB, NEON, NEON_NAMES, ORANGE, PINK, PURPLE, RED, STAT_NAMES, W, WHITE,
                     YELLOW, CarArt, Sfx, chrome, clamp, dim, fmt_pts, fmt_time, font, glow, load_save, make_cone,
                     make_edge_glow, make_scanlines, make_vignette, mix, panel, text, vtext, write_save)
from td_race import MODES, Race, medal_for
from td_track import COURSES, Track

HZ = 452                # hoogte van de horizon in het menu


# ------------------------------------------------------------------ bewegende menu-achtergrond
class MenuBG:
    """Jaren-90 arcade-achtergrond: zonsondergang, skyline van Tokyo met neon en een weg in perspectief."""

    def __init__(self):
        sky = pygame.Surface((W, H))
        for y in range(H):
            t = y / HZ
            if t < 0.55:
                c = mix((4, 2, 22), (52, 10, 92), t / 0.55)
            elif t < 1:
                c = mix((52, 10, 92), (255, 80, 130), ((t - 0.55) / 0.45) ** 1.6)
            else:
                c = (6, 3, 18)
            pygame.draw.line(sky, c, (0, y), (W, y))
        rnd = random.Random(3)
        for _ in range(120):                                  # sterren
            v = rnd.randint(90, 230)
            sky.set_at((rnd.randrange(W), rnd.randrange(int(HZ * 0.55))), (v, v, min(255, v + 25)))
        cx, cy, r = W // 2, HZ - 60, 190                      # de zon met strepen
        for y in range(cy - r, min(HZ, cy + r)):
            dy = y - cy
            if dy > 10 and (dy // 9) % 2 == 0 and dy % 18 > 18 - dy // 14 - 4:
                continue
            hw = int(math.sqrt(r * r - dy * dy))
            pygame.draw.line(sky, mix((255, 240, 120), (255, 40, 120), (dy + r) / (2 * r)), (cx - hw, y), (cx + hw, y))
        sky.blit(glow(900, (70, 14, 50), 1.4), (cx - 450, cy - 450), special_flags=pygame.BLEND_RGB_ADD)
        self.sky = sky
        self.far = self._skyline(rnd, (30, 10, 62), 60, 210, False)
        self.near = self._skyline(rnd, (9, 4, 24), 40, 150, True)
        self.t = 0.0

    @staticmethod
    def _skyline(rnd, col, hmin, hmax, signs):
        s = pygame.Surface((W, 260), pygame.SRCALPHA)
        x = 0
        while x < W:
            w, h = rnd.randint(46, 120), rnd.randint(hmin, hmax)
            pygame.draw.rect(s, col, (x, 260 - h, w, h))
            if rnd.random() < 0.3:
                pygame.draw.rect(s, col, (x + w // 2 - 2, 260 - h - 26, 4, 26))
                pygame.draw.circle(s, RED, (x + w // 2, 260 - h - 26), 2)
            lit = rnd.choice([(255, 226, 150), (150, 230, 255), (255, 150, 210)])
            for wx in range(x + 5, x + w - 6, 9):
                for wy in range(260 - h + 6, 256, 10):
                    if rnd.random() < (0.4 if signs else 0.22):
                        pygame.draw.rect(s, lit if signs else dim(lit, 0.55), (wx, wy, 4, 5))
            if signs and rnd.random() < 0.6 and h > 80:
                c = rnd.choice(NEON)
                img = vtext(J(rnd.choice(["ラーメン", "東京", "カラオケ", "ホテル", "酒", "ドリフト", "新宿", "寿司"]), "TOKYO"), 14, c, True)
                if img.get_height() < h - 10:
                    bx = x + rnd.choice([3, w - img.get_width() - 3])
                    pygame.draw.rect(s, (4, 2, 12), (bx - 2, 260 - h + 6, img.get_width() + 4, img.get_height() + 2))
                    pygame.draw.rect(s, c, (bx - 2, 260 - h + 6, img.get_width() + 4, img.get_height() + 2), 1)
                    s.blit(img, (bx, 260 - h + 7))
            x += w + rnd.randint(0, 6)
        return s

    def draw(self, s, dt, speed=1.0):
        self.t += dt * speed
        t = self.t
        s.blit(self.sky, (0, 0))
        for layer, v in ((self.far, 10), (self.near, 26)):
            x = -int(t * v) % W
            s.blit(layer, (x - W, HZ - 260))
            s.blit(layer, (x, HZ - 260))
        # de weg in perspectief met neon-raster
        for k in range(14):
            f = ((k + t * 2.2) % 14) / 14
            y = HZ + (H - HZ) * f ** 2.3
            pygame.draw.line(s, dim(PINK, 0.15 + 0.6 * f), (0, y), (W, y), 1 if f < 0.5 else 2)
        for k in range(-16, 17):
            pygame.draw.line(s, dim(PURPLE, 0.5), (W / 2 + k * 14, HZ), (W / 2 + k * 190, H), 1)
        pygame.draw.polygon(s, (10, 6, 26), [(W / 2 - 26, HZ), (W / 2 + 26, HZ), (W / 2 + 360, H), (W / 2 - 360, H)])
        for sd in (-1, 1):
            pygame.draw.line(s, CYAN, (W / 2 + sd * 26, HZ), (W / 2 + sd * 360, H), 3)
        for k in range(7):
            f0 = ((k + t * 2.2) % 7) / 7
            f1 = min(1.0, f0 + 0.06)
            y0, y1 = HZ + (H - HZ) * f0 ** 2.3, HZ + (H - HZ) * f1 ** 2.3
            w0, w1 = 1 + 7 * f0 ** 2.3, 1 + 7 * f1 ** 2.3
            pygame.draw.polygon(s, YELLOW, [(W / 2 - w0, y0), (W / 2 + w0, y0), (W / 2 + w1, y1), (W / 2 - w1, y1)])
        pygame.draw.line(s, WHITE, (0, HZ), (W, HZ), 1)
        # geblokte racestrepen boven en onder
        off = int(t * 60) % 32
        for y in (0, H - 16):
            for x in range(-32, W, 16):
                pygame.draw.rect(s, (236, 236, 240) if ((x // 16) + (y // 16)) % 2 == 0 else (14, 10, 26), (x + off, y, 16, 8))
                pygame.draw.rect(s, (14, 10, 26) if ((x // 16) + (y // 16)) % 2 == 0 else (236, 236, 240), (x + off, y + 8, 16, 8))


# ------------------------------------------------------------------ het spel
class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("東京ドリフト  TOKYO DRIFT")
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.save = load_save()
        self.screen.fill((4, 2, 22))
        text(self.screen, "NOW LOADING...", 30, (W // 2, H // 2), CYAN, "center", True, True)
        text(self.screen, J("サウンドを読込中", "GELUID LADEN"), 18, (W // 2, H // 2 + 44), PINK, "center", True)
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
        self.maps = [t.minimap((300, 190), width=4)[0] for t in self.tracks]
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
        self.sfx.music_on = bool(self.save["music"])
        self.sfx.update_music()

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
            elif dx or (ok and self.sel > 0):
                d = dx or 1
                if self.sel == 0:
                    s["volume"] = int(clamp(s["volume"] + d, 0, 10))
                elif self.sel == 1:
                    s["music"] = 1 - s["music"]
                elif self.sel == 2:
                    s["scan"] = 1 - s["scan"]
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
                title = self.sfx.play_race_music()            # elke race een ander nummer
                if title:
                    self.race.banner = ["♪ 音楽", title.upper(), PINK, 0.0]
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
        self.sfx.update_music(0.4 if self.state == "pause" else 0.75 if self.state in ("race", "result") else 1.0)

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
            self.bg.draw(s, 1 / FPS, 3.0 if st == "loading" else 1.0)
            getattr(self, "draw_" + st)(s)
        if self.save["scan"]:
            s.blit(self.assets["scan"], (0, 0))

    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            self.step(dt, pygame.event.get())
            self.draw()
            pygame.display.flip()

    # ------------------------------------------------------------ schermen
    def logo(self, s, y, size=118):
        t = self.t
        jp = J("東京ドリフト", "MIDNIGHT")
        flick = 0.45 if (math.sin(t * 2.1) > 0.97 or int(t * 23) % 41 == 0) else 1.0
        g = glow(520, dim(PINK, 0.34 * flick), 1.5)
        s.blit(g, (W // 2 - 260, y - 300), special_flags=pygame.BLEND_RGB_ADD)
        for off, col in ((4, dim(PINK, 0.5 * flick)), (0, mix(dim(PINK, flick), (255, 255, 255), 0.45 * flick))):
            img = font(54, True).render(jp, True, col)
            for d in ((-off, 0), (off, 0), (0, -off), (0, off)) if off else ((0, 0),):
                s.blit(img, img.get_rect(center=(W // 2 + d[0], y - 84 + d[1])))
        a = chrome("TOKYO", size, (255, 255, 255), (120, 220, 255), (30, 20, 150), (255, 120, 220), (20, 0, 60), 5)
        b = chrome("DRIFT", size, (255, 255, 210), (255, 200, 40), (210, 30, 60), (255, 240, 140), (60, 0, 20), 5)
        tw = a.get_width() + b.get_width() - 10
        x = W // 2 - tw // 2
        s.blit(a, (x, y - 50))
        s.blit(b, (x + a.get_width() - 10, y - 50 + 6))

    def top_bar(self, s, title_jp, title, hint):
        panel(s, (0, 20, W, 64), tint=(20, 4, 44), alpha=215, edge=None)
        pygame.draw.line(s, PINK, (0, 20), (W, 20), 3)
        pygame.draw.line(s, CYAN, (0, 84), (W, 84), 3)
        s.blit(chrome(title, 44, (255, 255, 210), (255, 200, 40), (210, 30, 60), (255, 240, 140), o=3), (40, 20))
        text(s, J(title_jp, ""), 30, (W - 40, 32), PINK, "topright", True)
        panel(s, (0, H - 62, W, 42), tint=(20, 4, 44), alpha=215, edge=None)
        text(s, hint, 17, (W // 2, H - 54), WHITE, "midtop", True)

    def draw_title(self, s):
        self.logo(s, 250)
        text(s, "-  MIDNIGHT NEON RUN  -", 24, (W // 2, 372), CYAN, "midtop", True, True)
        if int(self.t * 2.2) % 2:
            img = chrome("PRESS  ENTER", 46, (255, 255, 255), (255, 240, 120), (255, 120, 0), (255, 255, 200), o=3)
            s.blit(img, img.get_rect(center=(W // 2, 520)))
            text(s, J("スタートボタンを押してください", "DRUK OP ENTER OM TE STARTEN"), 20, (W // 2, 556), WHITE, "midtop", True)
        best = max([v for k, v in self.save["best"].items() if k.startswith("drift")] or [0])
        text(s, "1P", 22, (40, 26), CYAN, bold=True, italic=True)
        text(s, f"{best:08d}", 22, (84, 26), WHITE, bold=True, italic=True)
        text(s, f"HI-SCORE  {max(best, 50000):08d}", 22, (W // 2, 26), YELLOW, "midtop", True, True)
        text(s, "CREDIT  02", 22, (W - 40, 26), PINK, "topright", True, True)
        text(s, "© 1996  NEON ARCADE SYSTEM", 15, (W // 2, H - 48), (190, 190, 220), "midtop", True)

    def menu_list(self, s, items, x, y, step=62, size=34):
        """Lijst met menuregels in arcade-stijl; de gekozen regel krijgt een schuine neonbalk."""
        self.hit = []
        for k, (jp, lat) in enumerate(items):
            yy = y + k * step
            on = k == self.sel
            self.hit.append(pygame.Rect(x - 40, yy - 4, 560, step - 6))
            if on:
                w = 540 + int(8 * math.sin(self.t * 8))
                pygame.draw.polygon(s, (255, 40, 140), [(x - 30, yy + step - 14), (x - 10, yy - 2), (x - 10 + w, yy - 2), (x - 30 + w, yy + step - 14)])
                pygame.draw.polygon(s, (60, 0, 60), [(x - 24, yy + step - 18), (x - 8, yy + 2), (x - 14 + w, yy + 2), (x - 30 + w, yy + step - 18)])
                img = chrome(lat, size, (255, 255, 255), (255, 240, 120), (255, 120, 0), (255, 255, 200), o=3)
                s.blit(img, (x + 34, yy - 4))
                if int(self.t * 5) % 2:
                    pygame.draw.polygon(s, YELLOW, [(x, yy + 8), (x + 20, yy + 20), (x, yy + 32)])
                text(s, J(jp, ""), 20, (x + 500, yy + 10), CYAN, "topright", True)
            else:
                text(s, lat, size - 6, (x + 34, yy + 2), (170, 170, 215), bold=True, italic=True)
                text(s, J(jp, ""), 16, (x + 500, yy + 12), (120, 90, 170), "topright", True)

    def draw_menu(self, s):
        self.logo(s, 150, 84)
        items = [MODES["drift"], MODES["race"], ("ガレージ", "GARAGE"), ("オプション", "OPTIONS"), ("終了", "EXIT")]
        self.menu_list(s, items, 110, 280)
        info = ["Scoor zoveel mogelijk driftpunten. Lange drifts, wissels en clipping points geven een hogere multiplier.",
                "Race tegen bots door nachtelijk Tokyo. Driften vult je nitro bij.",
                "Kies je auto en de kleur van de neon onder de wagen.",
                "Volume, muziek, scanlines en volledig scherm.",
                "Terug naar de echte wereld."][self.sel]
        panel(s, (720, 280, 480, 296), edge=CYAN)
        text(s, J("インフォメーション", "INFO"), 18, (740, 292), PINK, bold=True)
        y = 326
        line = ""
        for word in info.split():
            if font(19).size(line + " " + word)[0] > 440:
                text(s, line, 19, (740, y), WHITE)
                y += 28
                line = word
            else:
                line = (line + " " + word).strip()
        text(s, line, 19, (740, y), WHITE)
        car = CARS[self.save["car"]]
        img = pygame.transform.rotate(self.art.big[car[0]], 12 * math.sin(self.t * 1.3))
        s.blit(glow(260, dim(NEON[self.save["glow"]], 0.5), 1.5), (960 - 130, 500 - 130), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(img, img.get_rect(center=(960, 500)))
        text(s, f"{J(car[1], '')}  {car[2]}", 18, (740, 546), YELLOW, bold=True, italic=True)
        text(s, "↑↓ kiezen    ENTER ok    ESC terug    M muziek    F11 volledig scherm", 16, (W // 2, H - 48), (200, 200, 230), "midtop", True)

    def draw_course(self, s):
        sv = self.save
        self.top_bar(s, "コース選択", "COURSE SELECT  -  " + MODES[self.mode][1],
                     "←→ wijzigen    ↑↓ regel    ENTER start    ESC terug")
        self.hit = []
        for k, (c, tr) in enumerate(zip(COURSES, self.tracks)):
            on = k == sv["course"]
            x, y = 50 + k * 400, 112 - (10 if on else 0)
            r = pygame.Rect(x, y, 380, 372)
            self.hit.append(r)
            edge = (YELLOW if int(self.t * 5) % 2 else PINK) if on and self.sel == 0 else (PINK if on else (70, 60, 110))
            panel(s, r, tint=(30, 6, 54) if on else (8, 6, 24), alpha=225, edge=edge, w=4 if on else 2)
            text(s, J(c["jp"], c["name"]), 32, (x + 190, y + 8), WHITE if on else (150, 150, 190), "midtop", True)
            text(s, c["name"], 20, (x + 190, y + 52), CYAN if on else (100, 120, 150), "midtop", True, True)
            m = self.maps[k]
            if not on:
                m = m.copy()
                m.set_alpha(110)
            s.blit(m, (x + 40, y + 82))
            text(s, JB("難易度", "NIVEAU") + "  " + "★" * c["diff"] + "☆" * (3 - c["diff"]), 18, (x + 20, y + 280), YELLOW, bold=True)
            text(s, f"{tr.length_m} m     {JB('高架', 'verhoogd')} {tr.elev_pct}%", 16, (x + 20, y + 308), WHITE, bold=True)
            best = sv["best"].get(f"{self.mode}-{k}-{sv['laps']}")
            bt = "---" if best is None else (fmt_pts(best) if self.mode == "drift" else fmt_time(best))
            text(s, f"{JB('記録', 'RECORD')}  {bt}", 16, (x + 20, y + 334), GREEN, bold=True)
            pygame.draw.line(s, CYAN, (x + 222, y + 296), (x + 250, y + 296), 4)
            text(s, "straat", 13, (x + 256, y + 286), CYAN, bold=True)
            pygame.draw.line(s, PINK, (x + 300, y + 296), (x + 328, y + 296), 4)
            text(s, "brug", 13, (x + 334, y + 286), PINK, bold=True)
        text(s, COURSES[sv["course"]]["desc"], 18, (W // 2, 500), WHITE, "midtop", True)
        rows = [("ラップ", "RONDEN", str(sv["laps"]))]
        if self.mode == "race":
            rows.append(("ライバル", "TEGENSTANDERS", str(sv["bots"])))
        rows.append(("天気", "WEER", J("雨 REGEN", "REGEN") if sv["weather"] else J("晴れ HELDER", "HELDER")))
        for k, (jp, lat, val) in enumerate(rows):
            x = W // 2 - len(rows) * 180 + k * 360 + 20
            on = self.sel == k + 1
            panel(s, (x, 540, 320, 78), tint=(40, 6, 60) if on else (8, 6, 24), edge=YELLOW if on else (70, 60, 110), w=3 if on else 2)
            text(s, f"{J(jp, '')}  {lat}", 15, (x + 160, 546), PINK if on else (150, 120, 190), "midtop", True)
            text(s, f"◀  {val}  ▶" if on else val, 28, (x + 160, 568), WHITE if on else (160, 160, 200), "midtop", True, True)

    def draw_garage(self, s):
        sv = self.save
        self.top_bar(s, "マシン選択", "SELECT YOUR MACHINE", "←→ auto    ↑↓ neonkleur    ENTER ok")
        car = CARS[sv["car"]]
        col = NEON[sv["glow"]]
        cx, cy = 400, 350
        for r, a in ((230, 0.12), (190, 0.2), (150, 0.3)):   # draaischijf
            pygame.draw.ellipse(s, dim(col, a), (cx - r, cy + 40 - r * 0.42, 2 * r, r * 0.84), 3)
        s.blit(glow(460, dim(col, 0.6), 1.4), (cx - 230, cy - 230), special_flags=pygame.BLEND_RGB_ADD)
        img = pygame.transform.rotozoom(self.art.big[car[0]], self.t * 40 % 360, 1.6)
        s.blit(img, img.get_rect(center=(cx, cy)))
        for k in range(len(CARS)):                            # kleine rij met alle auto's
            th = self.art.spr[CARS[k][0]]
            x = cx - len(CARS) * 34 + k * 68 + 34
            if k == sv["car"]:
                pygame.draw.rect(s, YELLOW, (x - 32, 560, 64, 44), 3)
            s.blit(th, th.get_rect(center=(x, 582)))
        text(s, "◀", 50, (70, cy - 30), YELLOW if int(self.t * 4) % 2 else PINK, bold=True)
        text(s, "▶", 50, (700, cy - 30), YELLOW if int(self.t * 4) % 2 else PINK, bold=True)
        panel(s, (790, 112, 440, 500), edge=CYAN)
        text(s, J(car[1], car[2]), 60, (1010, 116), WHITE, "midtop", True)
        s.blit(chrome(car[2], 40, (255, 255, 210), (255, 200, 40), (210, 30, 60), (255, 240, 140), o=3), (812, 200))
        for k, (jp, lat) in enumerate(STAT_NAMES):
            y = 276 + k * 60
            text(s, f"{J(jp, '')}  {lat}", 16, (812, y), CYAN, bold=True)
            for b in range(10):
                on = b < car[3][k]
                c = mix(CYAN, PINK, b / 9)
                pygame.draw.polygon(s, c if on else dim(c, 0.16), [(812 + b * 40 + 8, y + 26), (812 + b * 40 + 40, y + 26),
                                                                    (812 + b * 40 + 32, y + 46), (812 + b * 40, y + 46)])
        text(s, J("ネオン", "NEON") + "  ▲▼", 16, (812, 524), CYAN, bold=True)
        for k, c in enumerate(NEON):
            r = pygame.Rect(812 + k * 50, 550, 40, 40)
            pygame.draw.rect(s, c, r)
            if k == sv["glow"]:
                pygame.draw.rect(s, WHITE, r.inflate(10, 10), 3)
        text(s, NEON_NAMES[sv["glow"]] if J("x", "") else NEON_NAMES[sv["glow"]].split()[-1], 15, (1216, 524), col, "topright", True)

    def draw_options(self, s):
        sv = self.save
        self.top_bar(s, "オプション", "OPTIONS", "↑↓ kiezen    ←→ wijzigen    ESC terug")
        items = [("音量", f"VOLUME   {'■' * sv['volume']}{'□' * (10 - sv['volume'])}"),
                 ("音楽", "MUZIEK   " + ("AAN" if sv["music"] else "UIT")),
                 ("走査線", "SCANLINES   " + ("AAN" if sv["scan"] else "UIT")),
                 ("全画面", "VOLLEDIG SCHERM  (F11)")]
        self.menu_list(s, items, 340, 200, 80, 30)
        panel(s, (260, 540, 760, 86), edge=PINK)
        text(s, "RACE:  pijltjes/WASD rijden  -  SPATIE handrem  -  SHIFT nitro  -  R terugzetten  -  ESC pauze", 15, (W // 2, 552), WHITE, "midtop", True)
        text(s, "DRIFT:  stuur in, tik de handrem aan en geef gas. Stuur tegen om de drift vast te houden.", 15, (W // 2, 582), CYAN, "midtop", True)

    def draw_loading(self, s):
        c = COURSES[self.save["course"]]
        img = chrome(J(c["jp"], c["name"]), 80, (255, 255, 255), (150, 240, 255), (20, 80, 200), (220, 250, 255), o=4)
        s.blit(img, img.get_rect(center=(W // 2, 200)))
        text(s, c["name"], 30, (W // 2, 262), PINK, "midtop", True, True)
        dots = "." * (int(self.t * 6) % 4)
        text(s, "NOW LOADING" + dots, 34, (W // 2 - 150, 330), YELLOW, bold=True, italic=True)
        text(s, self.load_msg, 22, (W // 2, 388), CYAN, "midtop", True)

    def draw_pause(self, s):
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((6, 0, 20, 170))
        s.blit(dark, (0, 0))
        img = chrome(J("一時停止", "PAUSE"), 80, (255, 255, 255), (255, 120, 200), (160, 0, 90), (255, 220, 240), o=4, italic=False)
        s.blit(img, img.get_rect(center=(W // 2, 180)))
        text(s, "PAUSE", 26, (W // 2, 232), WHITE, "midtop", True, True)
        self.menu_list(s, [("続ける", "VERDER RIJDEN"), ("やり直す", "OPNIEUW"), ("メニュー", "NAAR MENU")], W // 2 - 250, 310)

    def draw_result(self, s):
        r, res = self.race, self.result
        p = r.player
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((6, 0, 20, 185))
        s.blit(dark, (0, 0))
        self.top_bar(s, "結果", "RESULT  -  " + r.t.spec["name"], "ENTER opnieuw    ESC menu")
        panel(s, (240, 120, 800, 480), edge=PINK, alpha=215)
        if r.mode == "drift":
            name, col, need = medal_for(r.score, r.t, r.laps)
            text(s, JB("ドリフトスコア", "DRIFT SCORE"), 22, (W // 2, 136), CYAN, "midtop", True)
            img = chrome(fmt_pts(r.score), 110, (255, 255, 255), (255, 170, 230), (180, 20, 120), (255, 220, 240), o=5)
            s.blit(img, img.get_rect(center=(W // 2, 230)))
            text(s, name or JB("メダルなし", "GEEN MEDAILLE"), 40, (W // 2, 300), col, "midtop", True)
            rows = [(JB("最高チェーン", "BESTE KETEN"), fmt_pts(r.best_chain)), (JB("クリップ", "CLIPPING POINTS"), str(r.clips)),
                    (JB("タイム", "TIJD"), fmt_time(p.finish_time)),
                    (JB("前の記録", "VORIG RECORD"), "---" if res["old"] is None else fmt_pts(res["old"]))]
        else:
            pos = res["pos"]
            col = (YELLOW, (210, 220, 235), (225, 140, 80))[pos - 1] if pos <= 3 else WHITE
            img = chrome(f"{pos}", 130, (255, 255, 255), col, dim(col, 0.4), (255, 255, 255), o=5)
            s.blit(img, img.get_rect(center=(W // 2 - 60, 210)))
            text(s, J("位", "e"), 50, (W // 2 + 10, 200), col, bold=True)
            text(s, JB("優勝!!", "GEWONNEN!!") if pos == 1 else JB("ゴール", "FINISH"), 34, (W // 2, 290), col, "midtop", True)
            rows = [(JB("タイム", "TIJD"), fmt_time(p.finish_time)), (JB("ベストラップ", "BESTE RONDE"), fmt_time(min(p.lap_times))),
                    (JB("ドリフト", "DRIFTPUNTEN"), fmt_pts(r.score)),
                    (JB("前の記録", "VORIG RECORD"), "---" if res["old"] is None else fmt_time(res["old"]))]
            for k, c in enumerate(res["table"]):
                tm = fmt_time(c.finish_time) if c.finished else "DNF"
                text(s, f"{k + 1}. {c.name}", 17, (790, 150 + k * 26), YELLOW if c.is_player else WHITE, bold=True)
                text(s, tm, 17, (1020, 150 + k * 26), YELLOW if c.is_player else CYAN, "topright", True)
        for k, (a, b) in enumerate(rows):
            y = 372 + k * 40
            text(s, a, 22, (330, y), CYAN, bold=True)
            text(s, b, 26, (950, y - 2), WHITE, "topright", True, True)
            pygame.draw.line(s, (70, 40, 110), (330, y + 34), (950, y + 34), 1)
        if res["new"] and int(self.t * 4) % 2:
            img = chrome(JB("新記録!!", "NEW RECORD!!"), 44, (255, 255, 255), (255, 240, 120), (255, 120, 0), (255, 255, 200), o=3)
            s.blit(img, img.get_rect(center=(W // 2, 566)))


if __name__ == "__main__":
    App().run()
