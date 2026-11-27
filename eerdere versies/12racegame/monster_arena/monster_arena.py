"""
MONSTER ARENA  -  top-down stuntshow met monstertrucks
=======================================================
Installeren:   py -m pip install pygame-ce        (gewoon 'pygame' werkt ook)
Starten:       py monster_arena.py

Deze bestanden moeten in dezelfde map staan:
    monster_arena.py   dit bestand: menu's en de hoofdlus
    ma_core.py         hulpfuncties, tekst, geluid en muziek
    ma_trucks.py       het tekenen van de trucks (skins) en hun aanzichten
    ma_arena.py        de arena's en alles wat erin staat
    ma_game.py         fysica, stunts, punten, bots, effecten en HUD
    cars_sheet.png     de autowrakken        arena_font.otf   lettertype

Besturing
    Pijltjes / WASD   rijden en sturen
    SPATIE            springen (hop)
    SHIFT             nitro  ->  wheelie
    X of CTRL         handrem  ->  donuts
    In de lucht:      omhoog = frontflip, omlaag = backflip, links/rechts = spin, Q / E = barrel roll
    R                 truck rechtop zetten
    ESC               pauze        M  muziek aan/uit        F11  volledig scherm
"""
import math
import random
import sys

import pygame

from ma_arena import ARENAS, Arena
from ma_core import (CYAN, FIRE, FPS, G_FIRE, G_GOLD, G_LIME, G_PINK, G_STEEL, GOLD, H, HOT, LIME, PINK, RED, STEEL, W, WHITE, Sfx,
                     chrome, clamp, dim, fmt_pts, fmt_time, font, glow, hazard, load_save, make_edge_glow, make_scanlines,
                     make_vignette, mix, panel, text, write_save)
from ma_game import MODES, Game, medal_for
from ma_trucks import ACCENTS, BODIES, DECALS, EXTRAS, PAINTS, PRESETS, STATS, WHEELS, get_art, preset_cfg

STAT_BUDGET = 24
GARAGE_ROWS = ["SKIN", "BODY", "LAK", "ACCENT", "STICKER", "WIELEN", "EXTRA"] + STATS
PART_KEYS = ["body", "paint", "accent", "decal", "wheels", "extra"]
PART_LISTS = [BODIES, [p[0] for p in PAINTS], [a[0] for a in ACCENTS], DECALS, WHEELS, EXTRAS]


def make_cone(L=230):
    s = pygame.Surface((L * 2, L * 2))
    for k in range(26, 0, -1):
        t = k / 26
        v = (1 - t) ** 1.6 * 0.42
        hw = 0.55 * t + 0.08
        pygame.draw.polygon(s, (int(255 * v), int(240 * v), int(200 * v)),
                            [(L + 14, L), (L + L * t, L - L * t * hw), (L + L * t * 1.04, L), (L + L * t, L + L * t * hw)])
    return s


# ------------------------------------------------------------------ bewegende menu-achtergrond
class MenuBG:
    """Stadion bij nacht: zwaaiende schijnwerpers, publiek met cameraflitsen, vonken en vlammen."""

    def __init__(self):
        bg = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            c = mix(mix((8, 6, 14), (58, 20, 10), min(1, t * 1.5)), (16, 8, 6), max(0, (t - 0.7) / 0.3))
            pygame.draw.line(bg, c, (0, y), (W, y))
        bg.blit(pygame.transform.smoothscale(glow(400, (150, 60, 10), 1.3), (1700, 560)), (W // 2 - 850, H - 480), special_flags=pygame.BLEND_RGB_ADD)
        rnd = random.Random(2)
        for row in range(7):                                  # tribune met publiek
            y = 300 + row * 30
            pygame.draw.rect(bg, (14 + row * 2, 10 + row, 14 + row), (0, y, W, 30))
            for x in range(-10, W + 10, 15 - row):
                c = dim(rnd.choice([(230, 70, 60), (240, 180, 50), (70, 150, 230), (235, 235, 235), (90, 200, 110), (200, 90, 200)]),
                        0.16 + row * 0.035)
                pygame.draw.circle(bg, c, (x + rnd.randint(-2, 2), y + 12 + rnd.randint(-2, 3)), 5 + row // 2)
        pygame.draw.rect(bg, (20, 12, 8), (0, 510, W, H - 510))
        for y in range(510, H):                               # zandvloer
            t = (y - 510) / (H - 510)
            pygame.draw.line(bg, mix((70, 40, 18), (150, 92, 44), t), (0, y), (W, y))
        for _ in range(900):
            x, y = rnd.randrange(W), rnd.randrange(512, H)
            d = rnd.randint(-16, 16)
            c = bg.get_at((x, y))
            pygame.draw.circle(bg, (clamp(c.r + d, 0, 255), clamp(c.g + d, 0, 255), clamp(c.b + d, 0, 255)), (x, y), rnd.randint(1, 3))
        for x in range(0, W, 64):                             # muur
            pygame.draw.rect(bg, (214, 56, 40) if (x // 64) % 2 else (236, 232, 224), (x, 498, 64, 18))
        pygame.draw.rect(bg, (20, 14, 12), (0, 514, W, 4))
        pygame.draw.rect(bg, (12, 10, 14), (0, 0, W, 60))    # lichtbrug bovenin
        for x in range(50, W, 118):
            pygame.draw.rect(bg, (40, 40, 48), (x - 26, 30, 52, 26), border_radius=5)
            pygame.draw.circle(bg, (255, 240, 200), (x, 43), 10)
            bg.blit(glow(120, (120, 90, 50), 1.5), (x - 60, 43 - 60), special_flags=pygame.BLEND_RGB_ADD)
        self.bg = bg
        self.ov = pygame.Surface((W, H), pygame.SRCALPHA)
        self.beams = [(x, rnd.uniform(0, 6.28)) for x in (168, 404, 640, 876, 1112)]
        self.embers = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(-14, 14), rnd.uniform(-120, -40), rnd.uniform(1.5, 3.5)] for _ in range(80)]
        self.t = 0.0

    def draw(self, s, dt, flames=True):
        self.t += dt
        t = self.t
        s.blit(self.bg, (0, 0))
        for k in range(5):                                    # cameraflitsen
            if random.random() < 0.35:
                x, y = random.uniform(0, W), random.uniform(300, 500)
                s.blit(glow(40, (255, 255, 255), 1.3), (x - 20, y - 20), special_flags=pygame.BLEND_RGB_ADD)
        self.ov.fill((0, 0, 0, 0))
        for ox, ph in self.beams:
            a = math.sin(t * 0.55 + ph) * 0.5
            for k, al in ((0.17, 13), (0.09, 22)):
                pygame.draw.polygon(self.ov, (255, 214, 150, al), [(ox, 43), (ox + math.sin(a - k) * 900, 43 + math.cos(a - k) * 900),
                                                                    (ox + math.sin(a + k) * 900, 43 + math.cos(a + k) * 900)])
        s.blit(self.ov, (0, 0))
        for e in self.embers:
            e[0] += e[2] * dt + math.sin(t * 2 + e[1]) * 8 * dt
            e[1] += e[3] * dt
            if e[1] < -10:
                e[0], e[1] = random.uniform(0, W), H + 10
            pygame.draw.circle(s, (255, 150 + int(60 * math.sin(t * 5 + e[0])), 40), (e[0], e[1]), int(e[4]))
        if flames:                                            # vlammen onderaan
            for col, hgt, sp, wd in ((HOT, 62, 7.0, 34), (FIRE, 46, 9.0, 28), (GOLD, 26, 12.0, 22)):
                for x in range(-20, W + 20, wd):
                    hh = hgt * (0.45 + 0.55 * abs(math.sin(t * sp * 0.4 + x * 0.071) * math.sin(t * sp * 0.23 + x * 0.013)))
                    pygame.draw.polygon(s, col, [(x - wd * 0.7, H - 16), (x + wd * 0.7, H - 16), (x + math.sin(t * sp + x) * 8, H - 16 - hh)])
        hazard(s, (0, 0, W, 18), t * 50)
        hazard(s, (0, H - 18, W, 18), -t * 50)


# ------------------------------------------------------------------ het spel
class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MONSTER ARENA")
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.save = load_save()
        self.screen.fill((10, 6, 6))
        text(self.screen, "LADEN...", 34, (W // 2, H // 2), FIRE, "center")
        text(self.screen, "motoren warmdraaien", 18, (W // 2, H // 2 + 44), GOLD, "center")
        pygame.display.flip()
        self.sfx = Sfx()
        self.apply_audio()
        self.assets = dict(cone=make_cone(), spot=glow(600, (44, 38, 26), 1.3), spot2=glow(400, (60, 54, 40), 1.4),
                           edge_fire=make_edge_glow((130, 50, 6)), edge_pink=make_edge_glow((110, 20, 70)),
                           vignette=make_vignette(), scan=make_scanlines(), white=pygame.Surface((W, H)))
        self.assets["white"].fill((255, 255, 255))
        self.bg = MenuBG()
        self.arenas = [Arena(i) for i in range(len(ARENAS))]
        self.maps = [a.schematic((310, 200))[0] for a in self.arenas]
        self.state = "title"
        self.sel = 0
        self.mode = "free"
        self.game = None
        self.t = 0.0
        self.loader = None
        self.load_msg = ""
        self.result = None
        self.hit = []
        self.sfx.start_music()

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
        ok, back = k in (pygame.K_RETURN, pygame.K_KP_ENTER), k == pygame.K_ESCAPE
        dx = (1 if right else 0) - (1 if left else 0)
        dy = (1 if down else 0) - (1 if up else 0)
        st = self.state
        if k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_m:
            s["music"] = 1 - s["music"]
            self.apply_audio()
        elif st == "title":
            if back:
                self.quit()
            else:
                sfx.play("ok")
                self.go("menu")
        elif st == "menu":
            if dy:
                self.sel = (self.sel + dy) % 6
                sfx.play("move")
            elif ok:
                sfx.play("ok")
                if self.sel < 3:
                    self.mode = ("free", "battle", "crush")[self.sel]
                    self.go("arena")
                elif self.sel == 5:
                    self.quit()
                else:
                    self.go(("garage", "options")[self.sel - 3])
            elif back:
                sfx.play("back")
                self.go("title")
        elif st == "arena":
            rows = self.arena_rows()
            if dy:
                self.sel = (self.sel + dy) % (len(rows) + 1)
                sfx.play("move")
            elif dx:
                sfx.play("move")
                if self.sel == 0:
                    s["arena"] = (s["arena"] + dx) % len(ARENAS)
                elif rows[self.sel - 1] == "time":
                    s["time"] = int(clamp(s["time"] + dx * 30, 60, 300))
                else:
                    s["bots"] = int(clamp(s["bots"] + dx, 1, 5))
            elif ok:
                sfx.play("ok")
                self.start_game()
            elif back:
                sfx.play("back")
                self.go("menu", ("free", "battle", "crush").index(self.mode))
        elif st == "garage":
            if dy:
                self.sel = (self.sel + dy) % len(GARAGE_ROWS)
                sfx.play("move")
            elif dx:
                sfx.play("move")
                tr = s["truck"]
                if self.sel == 0:                             # kant-en-klare skin
                    s["preset"] = (s["preset"] + dx) % len(PRESETS) if s["preset"] >= 0 else (0 if dx > 0 else len(PRESETS) - 1)
                    s["truck"] = preset_cfg(s["preset"])
                elif self.sel <= 6:                           # onderdeel wijzigen = eigen ontwerp
                    key = PART_KEYS[self.sel - 1]
                    tr[key] = (tr[key] + dx) % len(PART_LISTS[self.sel - 1])
                    s["preset"] = -1
                else:
                    i = self.sel - 7
                    if 1 <= tr["stats"][i] + dx <= 10 and (dx < 0 or sum(tr["stats"]) < STAT_BUDGET):
                        tr["stats"][i] += dx
                        s["preset"] = -1
            elif ok or back:
                sfx.play("ok" if ok else "back")
                write_save(s)
                self.go("menu", 3)
        elif st == "options":
            if dy:
                self.sel = (self.sel + dy) % 4
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
                self.go("menu", 4)
        elif st == "game":
            if back:
                self.sfx.loops(mute=True)
                self.go("pause")
            elif k == pygame.K_r:
                self.game.reset_truck()
            elif ok and self.game.state == "finished" and self.game.end_t > 1.0:
                self.finish_game()
        elif st == "pause":
            if dy:
                self.sel = (self.sel + dy) % 3
                sfx.play("move")
            elif back or (ok and self.sel == 0):
                self.go("game")
            elif ok and self.sel == 1:
                self.start_game()
            elif ok:
                self.end_game()
        elif st == "result":
            if ok:
                sfx.play("ok")
                self.start_game()
            elif back:
                sfx.play("back")
                self.end_game()

    def arena_rows(self):
        return {"free": ["time"], "battle": ["time", "bots"], "crush": []}[self.mode]

    def click(self, pos):
        """Muis: klikken op een regel kiest ze, elders klikken = Enter."""
        for k, r in enumerate(self.hit):
            if r.collidepoint(pos):
                if self.state == "arena":
                    self.save["arena"] = k
                    self.sel = 0
                    return
                if self.state in ("menu", "pause", "options", "garage"):
                    self.sel = k
                    if self.state == "garage":
                        return
        if self.state not in ("game", "garage"):
            self.key(pygame.K_RETURN)

    def quit(self):
        write_save(self.save)
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------ spel starten / stoppen
    def start_game(self):
        self.sfx.stop_loops()
        write_save(self.save)
        self.arena = self.arenas[self.save["arena"]]
        self.loader = self.arena.build()
        self.go("loading")

    def end_game(self):
        self.sfx.stop_loops()
        self.game = None
        for a in self.arenas:
            a.world = None
        self.go("menu", ("free", "battle", "crush").index(self.mode))

    def hs_key(self):
        s = self.save
        return f"crush-{s['arena']}" if self.mode == "crush" else f"{self.mode}-{s['arena']}-{s['time']}"

    def finish_game(self):
        g, s = self.game, self.save
        key = self.hs_key()
        old = s["hs"].get(key)
        if g.mode == "crush":
            value, new = round(g.clock, 1), old is None or g.clock < old
        else:
            value, new = g.player.score.total, old is None or g.player.score.total > old
        if new:
            s["hs"][key] = value
            write_save(s)
        self.result = dict(new=new, old=old, value=value, rank=g.ranking())
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
                s = self.save
                self.game = Game(self, self.arena, self.mode, s["time"], s["bots"])
                self.go("game")
        elif self.state == "game":
            self.game.update(dt, pygame.key.get_pressed())
            if self.game.state == "finished" and self.game.end_t > 4.5:
                self.finish_game()
        elif self.state == "result":
            self.game.update(dt, pygame.key.get_pressed())
        self.sfx.update_music(0.5 if self.state in ("game", "result", "pause") else 1.0)

    def draw(self):
        s = self.screen
        st = self.state
        if st in ("game", "pause", "result"):
            self.game.draw(s)
            if st == "pause":
                self.draw_pause(s)
            elif st == "result":
                self.draw_result(s)
        else:
            self.bg.draw(s, 1 / FPS, st in ("title", "menu", "loading"))
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
    def logo(self, s, y, size=120):
        a = chrome("MONSTER", size, G_STEEL, 6)
        b = chrome("ARENA", int(size * 1.18), G_FIRE, 6)
        s.blit(glow(700, (90, 34, 6), 1.5), (W // 2 - 350, y - 300), special_flags=pygame.BLEND_RGB_ADD)
        bob = math.sin(self.t * 2.2) * 4
        s.blit(a, a.get_rect(center=(W // 2 - 20, y - size * 0.42 + bob)))
        s.blit(b, b.get_rect(center=(W // 2 + 20, y + size * 0.52 - bob)))

    def show_truck(self, s, x, y, ang, zoom=1.0, lift=0.0):
        art = get_art(self.save["truck"], True)
        sh = pygame.Surface((int(430 * zoom), int(250 * zoom)), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 120), sh.get_rect())
        sh = pygame.transform.rotate(sh, ang)
        s.blit(sh, sh.get_rect(center=(x + 14 + lift * 0.3, y + 20 + lift * 0.5)))
        img = pygame.transform.rotozoom(art.big, ang, zoom)
        s.blit(img, img.get_rect(center=(x, y - lift)))

    def top_bar(self, s, title, hint):
        panel(s, (-20, 30, W + 40, 66), tint=(26, 12, 6), alpha=225, edge=None)
        pygame.draw.line(s, FIRE, (0, 30), (W, 30), 3)
        pygame.draw.line(s, GOLD, (0, 96), (W, 96), 3)
        s.blit(chrome(title, 46, G_FIRE, 3), (40, 28))
        panel(s, (-20, H - 66, W + 40, 40), tint=(26, 12, 6), alpha=225, edge=None)
        text(s, hint, 17, (W // 2, H - 60), WHITE, "midtop")

    def draw_title(self, s):
        self.logo(s, 168, 118)
        self.show_truck(s, W // 2, 496, 10 + 6 * math.sin(self.t * 1.1), 0.7, 8 + 8 * abs(math.sin(self.t * 3)))
        text(s, "STUNTS  -  FLIPS  -  DESTRUCTION", 22, (W // 2, 318), GOLD, "midtop")
        if int(self.t * 2.2) % 2:
            img = chrome("DRUK OP ENTER", 44, G_GOLD, 3)
            s.blit(img, img.get_rect(center=(W // 2, 640)))
        best = max([v for k, v in self.save["hs"].items() if k.startswith("free")] or [0])
        text(s, f"1P  {int(best):08d}", 20, (40, 26), GOLD)
        text(s, "TONIGHT ONLY!   LIVE!   LOUD!", 20, (W - 40, 26), FIRE, "topright")

    def menu_list(self, s, items, x, y, step=58, size=32, w=520):
        """Lijst met menuregels; de gekozen regel krijgt een stalen balk met vlamkleur."""
        self.hit = []
        for k, lat in enumerate(items):
            yy = y + k * step
            self.hit.append(pygame.Rect(x - 40, yy - 4, w + 40, step - 4))
            if k == self.sel:
                ww = w + int(8 * math.sin(self.t * 8))
                pygame.draw.polygon(s, FIRE, [(x - 34, yy + step - 12), (x - 12, yy - 4), (x - 12 + ww, yy - 4), (x - 34 + ww, yy + step - 12)])
                pygame.draw.polygon(s, (40, 14, 6), [(x - 27, yy + step - 16), (x - 9, yy), (x - 17 + ww, yy), (x - 35 + ww, yy + step - 16)])
                s.blit(chrome(lat, size, G_GOLD, 3), (x + 34, yy - 5))
                if int(self.t * 5) % 2:
                    pygame.draw.polygon(s, GOLD, [(x, yy + 8), (x + 20, yy + 20), (x, yy + 32)])
            else:
                text(s, lat, size - 6, (x + 34, yy + 2), (206, 190, 170))

    def draw_menu(self, s):
        self.logo(s, 118, 70)
        self.menu_list(s, [MODES["free"], MODES["battle"], MODES["crush"], "GARAGE", "OPTIES", "STOPPEN"], 100, 250)
        info = ["Zoveel mogelijk stuntpunten binnen de tijd. Flips, spins, barrel rolls en combo's leveren het meest op.",
                "Stuntgevecht tegen bots: wie na de tijd de meeste punten heeft, wint.",
                "Rijd alle wrakken en bussen plat, zo snel als je kan.",
                "Kies een skin of bouw je eigen monstertruck.",
                "Volume, muziek, scanlines en volledig scherm.",
                "Terug naar de echte wereld."][self.sel]
        panel(s, (690, 250, 540, 150))
        y, line = 266, ""
        for word in info.split():
            if font(19).size(line + " " + word)[0] > 500:
                text(s, line, 19, (710, y), WHITE)
                y += 28
                line = word
            else:
                line = (line + " " + word).strip()
        text(s, line, 19, (710, y), WHITE)
        self.show_truck(s, 960, 540, 10 + 5 * math.sin(self.t * 1.3), 0.62, 6 + 5 * abs(math.sin(self.t * 3)))
        name = PRESETS[self.save["preset"]][0] if self.save["preset"] >= 0 else "EIGEN ONTWERP"
        text(s, name, 20, (710, 412), GOLD)

    def draw_arena(self, s):
        sv = self.save
        self.top_bar(s, "KIES JE ARENA  -  " + MODES[self.mode], "pijltjes: wijzigen     ENTER: start     ESC: terug")
        self.hit = []
        for k, (spec, ar) in enumerate(zip(ARENAS, self.arenas)):
            on = k == sv["arena"]
            x, y = 50 + k * 400, 122 - (10 if on else 0)
            r = pygame.Rect(x, y, 380, 356)
            self.hit.append(r)
            edge = (GOLD if int(self.t * 5) % 2 else FIRE) if on and self.sel == 0 else (FIRE if on else (90, 70, 60))
            panel(s, r, tint=(44, 18, 8) if on else (16, 10, 8), alpha=230, edge=edge, w=4 if on else 2)
            img = chrome(spec["name"], 34, G_GOLD if on else G_STEEL, 3)
            s.blit(img, img.get_rect(midtop=(x + 190, y + 6)))
            m = self.maps[k]
            if not on:
                m = m.copy()
                m.set_alpha(120)
            s.blit(m, m.get_rect(center=(x + 190, y + 178)))
            n = len(ar.L["wrecks"]) + len(ar.L["buses"])
            text(s, f"{len(ar.ramps)} schansen    {n} wrakken    {len(ar.L['barrels'])} vaten", 15, (x + 190, y + 290), WHITE, "midtop")
            key = f"crush-{k}" if self.mode == "crush" else f"{self.mode}-{k}-{sv['time']}"
            best = sv["hs"].get(key)
            bt = "---" if best is None else (fmt_time(best) if self.mode == "crush" else fmt_pts(best))
            text(s, f"RECORD   {bt}", 17, (x + 190, y + 316), LIME, "midtop")
        panel(s, (190, 484, 900, 38), edge=None, alpha=215)
        text(s, ARENAS[sv["arena"]]["desc"], 18, (W // 2, 490), WHITE, "midtop")
        rows = [("TIJD", f"{sv['time'] // 60}:{sv['time'] % 60:02d}") if r == "time" else ("TEGENSTANDERS", str(sv["bots"])) for r in self.arena_rows()]
        for k, (lab, val) in enumerate(rows):
            x = W // 2 - len(rows) * 180 + k * 360 + 20
            on = self.sel == k + 1
            panel(s, (x, 532, 320, 78), tint=(50, 20, 8) if on else (16, 10, 8), edge=GOLD if on else (90, 70, 60), w=3 if on else 2)
            text(s, lab, 15, (x + 160, 538), FIRE if on else (170, 140, 120), "midtop")
            text(s, f"<  {val}  >" if on else val, 28, (x + 160, 560), WHITE if on else (190, 180, 170), "midtop")

    def draw_garage(self, s):
        sv = self.save
        tr = sv["truck"]
        self.top_bar(s, "GARAGE", "omhoog/omlaag: regel     links/rechts: wijzigen     ENTER: klaar")
        cx, cy = 360, 360
        for r, a in ((300, 0.10), (250, 0.18), (200, 0.3)):  # draaischijf
            pygame.draw.ellipse(s, dim(GOLD, a), (cx - r, cy + 30 - r * 0.5, 2 * r, r), 4)
        s.blit(self.assets["spot"], (cx - 300, cy - 300), special_flags=pygame.BLEND_RGB_ADD)
        self.show_truck(s, cx, cy + 6, self.t * 28 % 360, 0.86, 0)
        art = get_art(tr, True)
        panel(s, (60, 548, 600, 100), edge=(120, 90, 60))
        for k, img in enumerate((art.side, pygame.transform.rotate(art.front_x, -90), pygame.transform.rotate(art.rear_x, 90), art.under_x)):
            s.blit(img, img.get_rect(center=(140 + k * 146, 598)))
        name = PRESETS[sv["preset"]][0] if sv["preset"] >= 0 else "EIGEN ONTWERP"
        img = chrome(name, 40, G_FIRE, 3)
        s.blit(img, img.get_rect(midtop=(cx, 104)))
        panel(s, (700, 108, 540, 540))
        self.hit = []
        for k, lab in enumerate(GARAGE_ROWS):
            y = 118 + k * 45 + (30 if k >= 7 else 0)
            on = k == self.sel
            self.hit.append(pygame.Rect(706, y - 2, 528, 44))
            if on:
                pygame.draw.rect(s, (70, 28, 8), (708, y - 1, 524, 42))
                pygame.draw.rect(s, FIRE, (708, y - 1, 524, 42), 2)
            text(s, lab, 17, (722, y + 8), GOLD if on else (200, 180, 160))
            if k == 0:
                val = name
            elif k <= 6:
                val = PART_LISTS[k - 1][tr[PART_KEYS[k - 1]]]
                if k in (2, 3):                               # kleurstaaltje
                    col = (PAINTS if k == 2 else ACCENTS)[tr[PART_KEYS[k - 1]]][1]
                    pygame.draw.rect(s, col, (1176, y + 8, 40, 24))
                    pygame.draw.rect(s, WHITE, (1176, y + 8, 40, 24), 2)
            else:
                val = None
                v = tr["stats"][k - 7]
                for b in range(10):
                    c = mix(GOLD, RED, b / 9)
                    pygame.draw.polygon(s, c if b < v else dim(c, 0.18), [(960 + b * 26 + 7, y + 8), (960 + b * 26 + 26, y + 8),
                                                                           (960 + b * 26 + 19, y + 32), (960 + b * 26, y + 32)])
            if val:
                text(s, f"<  {val}  >" if on else val, 19, (1160 if k in (2, 3) else 1220, y + 6), WHITE if on else (220, 210, 200), "topright")
        left = STAT_BUDGET - sum(tr["stats"])
        text(s, f"PUNTEN OVER:  {left}", 16, (1220, 118 + 7 * 45 + 4), LIME if left else (170, 150, 130), "topright")

    def draw_options(self, s):
        sv = self.save
        self.top_bar(s, "OPTIES", "omhoog/omlaag: kiezen     links/rechts: wijzigen     ESC: terug")
        items = [f"VOLUME   {'|' * sv['volume']}{'.' * (10 - sv['volume'])}", "MUZIEK   " + ("AAN" if sv["music"] else "UIT"),
                 "SCANLINES   " + ("AAN" if sv["scan"] else "UIT"), "VOLLEDIG SCHERM  (F11)"]
        self.menu_list(s, items, 360, 150, 66, 30, 560)
        panel(s, (160, 430, 960, 200), edge=GOLD)
        for k, (a, b) in enumerate((("RIJDEN", "pijltjes of WASD     SPATIE springen     SHIFT nitro (wheelie)     X handrem (donuts)"),
                                    ("IN DE LUCHT", "omhoog = frontflip     omlaag = backflip     links/rechts = spin     Q / E = barrel roll"),
                                    ("LANDEN", "laat de toetsen los: de truck zet zichzelf recht. Scheef landen = crash en combo kwijt."),
                                    ("PUNTEN", "combo's, vuurringen, over auto's en bussen springen, vaten opblazen, wrakken pletten"),
                                    ("OVERIG", "R truck rechtop     ESC pauze     M muziek"))):
            text(s, a, 16, (184, 446 + k * 36), FIRE)
            text(s, b, 16, (330, 446 + k * 36), WHITE)

    def draw_loading(self, s):
        spec = ARENAS[self.save["arena"]]
        img = chrome(spec["name"], 96, G_STEEL, 5)
        s.blit(img, img.get_rect(center=(W // 2, 210)))
        text(s, MODES[self.mode], 32, (W // 2, 280), FIRE, "midtop")
        text(s, "LADEN" + "." * (int(self.t * 6) % 4), 34, (W // 2 - 80, 360), GOLD)
        text(s, self.load_msg, 20, (W // 2, 416), WHITE, "midtop")

    def draw_pause(self, s):
        dk = pygame.Surface((W, H), pygame.SRCALPHA)
        dk.fill((10, 4, 0, 175))
        s.blit(dk, (0, 0))
        img = chrome("PAUZE", 100, G_FIRE, 5)
        s.blit(img, img.get_rect(center=(W // 2, 190)))
        self.menu_list(s, ["VERDER SPELEN", "OPNIEUW", "NAAR MENU"], W // 2 - 240, 310)

    def draw_result(self, s):
        g, res = self.game, self.result
        sc = g.player.score
        dk = pygame.Surface((W, H), pygame.SRCALPHA)
        dk.fill((10, 4, 0, 190))
        s.blit(dk, (0, 0))
        self.top_bar(s, "UITSLAG  -  " + g.arena.spec["name"], "ENTER: opnieuw     ESC: menu")
        panel(s, (200, 116, 880, 500), edge=FIRE, alpha=225)
        x0 = 250
        if g.mode == "crush":
            name, col, need = medal_for("crush", g.clock, g)
            text(s, "ALLES PLAT IN", 22, (x0, 132), FIRE)
            s.blit(chrome(fmt_time(g.clock), 96, G_STEEL, 5), (x0 - 6, 150))
        else:
            name, col, need = medal_for("free", sc.total, g)
            text(s, "EINDSCORE", 22, (x0, 132), FIRE)
            s.blit(chrome(fmt_pts(sc.total), 96, G_FIRE, 5), (x0 - 6, 150))
        if g.mode == "battle":
            pos = res["rank"].index(g.player) + 1
            text(s, "GEWONNEN!" if pos == 1 else f"{pos}e PLAATS", 40, (x0, 268), GOLD if pos == 1 else WHITE)
            for k, t in enumerate(res["rank"]):
                c = GOLD if t.is_player else WHITE
                pygame.draw.circle(s, t.color, (770, 152 + k * 30), 8)
                text(s, f"{k + 1}. {t.name}", 18, (786, 140 + k * 30), c)
                text(s, fmt_pts(t.score.total), 18, (1040, 140 + k * 30), c, "topright")
        else:
            text(s, f"MEDAILLE:  {name}" if name else "GEEN MEDAILLE", 40, (x0, 268), col)
        n = sc.n
        rows = [("BESTE STUNT", f"{sc.best[1]}   +{fmt_pts(sc.best[0])}" if sc.best[0] else "-"),
                ("FLIPS / ROLLS / SPINS", f"{n['flips']} / {n['rolls']} / {n['spins']}"),
                ("PLATGEREDEN  /  OVERHEEN GESPRONGEN", f"{n['crushes']} / {n['cars']}"),
                ("VATEN  /  VUURRINGEN  /  DONUTS", f"{n['booms']} / {n['hoops']} / {n['donuts']}"),
                ("CRASHES", str(n["crashes"])),
                ("VORIG RECORD", "-" if res["old"] is None else (fmt_time(res["old"]) if g.mode == "crush" else fmt_pts(res["old"])))]
        for k, (a, b) in enumerate(rows):
            y = 336 + k * 38
            text(s, a, 18, (x0, y), FIRE)
            text(s, b, 20, (1030, y - 1), WHITE, "topright")
            pygame.draw.line(s, (90, 50, 24), (x0, y + 31), (1030, y + 31), 1)
        if res["new"] and int(self.t * 4) % 2:
            img = chrome("NIEUW RECORD!", 44, G_GOLD, 3)
            s.blit(img, img.get_rect(center=(W // 2, 588)))


if __name__ == "__main__":
    App().run()
