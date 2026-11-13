"""
ma_game.py  -  het spel zelf: trucks, stunts, punten, bots, effecten en de HUD.
"""
import math
import random

import pygame

from ma_core import (BOT_NAMES, CYAN, FIRE, G_FIRE, G_GOLD, G_ICE, G_LIME, G_PINK, G_STEEL, GOLD, H, HOT, LIME, PINK, RED, STEEL,
                     TAU, W, WHITE, chrome, clamp, dim, fmt_pts, fmt_time, glow, hazard, lerp, mix, panel, render, text, wrap_rad)
from ma_trucks import PRESETS, get_art, preset_cfg, truck_params

GRAV = 950.0            # zwaartekracht (px/s^2)
SPIN_RATE = 5.2         # draaisnelheid in de lucht (rad/s)
ROLL_RATE = 7.0
MODES = {"free": "FREESTYLE", "battle": "BATTLE", "crush": "CRUSH RUN"}


def flip_name(base, n):
    return base if n == 1 else (f"DUBBELE {base}" if n == 2 else (f"TRIPLE {base}" if n == 3 else f"{n}x {base}"))


def medal_for(mode, value, game):
    """Medaille: (naam, kleur, volgende doel)."""
    names = (("GOUD", GOLD), ("ZILVER", (214, 222, 236)), ("BRONS", (226, 140, 80)))
    if mode == "crush":
        n = game.targets
        for (nm, col), f in zip(names, (3.4, 4.8, 6.6)):
            if value <= n * f:
                return nm, col, n * f
        return None, (150, 150, 160), n * 6.6
    for (nm, col), f in zip(names, (26000, 14000, 6000)):
        if value >= f * game.duration / 60:
            return nm, col, f * game.duration / 60
    return None, (150, 150, 160), 6000 * game.duration / 60


# ------------------------------------------------------------------ punten
class Scorer:
    """Houdt punten, combo en meldingen bij voor een truck."""

    def __init__(self):
        self.total = 0
        self.chain = 0
        self.chain_t = 0.0
        self.best = (0, "")
        self.events = []                     # [titel, tekst, kleur, leeftijd, punten]
        self.n = dict(flips=0, spins=0, rolls=0, wheelie=0.0, crushes=0, jumps=0, crashes=0, cars=0, booms=0, hoops=0, donuts=0)
        self.bonus = 1                       # x2 door pickup of uitzinnig publiek

    @property
    def mult(self):
        return min(5.0, 1.0 + 0.5 * self.chain)

    def add(self, title, base, col=GOLD, chain=True):
        m = self.mult * self.bonus
        pts = int(base * m)
        self.total += pts
        if chain:
            self.chain += 1
            self.chain_t = 5.0
        if pts > self.best[0]:
            self.best = (pts, title)
        self.events.append([title, f"+{fmt_pts(pts)}" + (f"   x{m:.1f}" if m > 1 else ""), col, 0.0, pts])
        del self.events[:-4]
        return pts

    def crash(self):
        self.chain, self.chain_t = 0, 0.0
        self.n["crashes"] += 1
        self.events.append(["CRASH!", "combo kwijt", RED, 0.0, 0])

    def update(self, dt):
        if self.chain_t > 0:
            self.chain_t -= dt
            if self.chain_t <= 0:
                self.chain = 0
        for e in self.events:
            e[3] += dt
        self.events = [e for e in self.events if e[3] < 2.6]


# ------------------------------------------------------------------ truck
class Truck:
    def __init__(self, x, y, heading, cfg, name, is_player=False):
        prm = truck_params(cfg)
        self.x, self.y, self.heading = x, y, heading
        self.vx = self.vy = 0.0
        self.vmax, self.accel = prm["vmax"], prm["accel"]
        self.nitro_cap = prm["nitro"]
        self.nitro = self.nitro_cap
        self.hop_v, self.flip_rate = prm["hop"], prm["flip"]
        self.name, self.is_player = name, is_player
        self.art = get_art(cfg)
        self.color = self.art.color
        self.boosting = False
        self.slip = 0.0
        self.z = self.vz = 0.0               # hoogte en verticale snelheid
        self.pitch = self.pw = 0.0           # flip-hoek en -snelheid
        self.roll = self.rw = 0.0            # barrel-roll-hoek en -snelheid
        self.air = False
        self.info = None                     # gegevens van de huidige sprong
        self.rise = 0.0                      # hoe snel de grond omhoog liep (voor het lanceren)
        self.wheelie_t = 0.0
        self.donut = self.donut_gap = 0.0
        self.donut_n = 0
        self.stun = self.hop_cd = self.ram_cd = 0.0
        self.in_pit = False
        self.wheels = None
        self.score = Scorer()
        self.x2_t = 0.0

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    @property
    def fwd(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    def ground_physics(self, dt, thr, brk, steer, hand, boost, grip_k, drag):
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        vf = self.vx * fx + self.vy * fy
        turn = 2.9 * (1 - 0.35 * min(1, abs(vf) / self.vmax)) * (1.6 if hand else 1.0)
        dh = steer * turn * clamp(vf / 120, -1, 1) * dt
        self.heading += dh
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        vf = self.vx * fx + self.vy * fy
        vl = self.vx * rx + self.vy * ry
        boosting = bool(boost and thr and self.nitro > 0)
        self.nitro = max(0.0, self.nitro - 30 * dt) if boosting else min(self.nitro_cap, self.nitro + 7 * dt)
        self.boosting = boosting
        accel = self.accel * (1.7 if boosting else 1.0)
        vmax = self.vmax * (1.25 if boosting else 1.0)
        if thr:
            vf += accel * dt
        if brk:
            vf -= (700 if vf > 20 else accel * 0.6) * dt
        vf -= vf * (accel / vmax + drag) * dt
        if not thr and not brk:
            vf -= math.copysign(min(abs(vf), 80 * dt), vf)
        if hand:
            vf -= vf * 0.4 * dt
        vf = max(vf, -self.vmax * 0.35)
        vl *= math.exp(-(2.0 if hand else 7.0) * grip_k * dt)
        self.vx = fx * vf + rx * vl
        self.vy = fy * vf + ry * vl
        self.slip = abs(vl)
        return dh


def new_info(tiny=False):
    return dict(t=0.0, peak=0.0, back=0.0, front=0.0, spin=0.0, roll=0.0, cars=0, buses=0, hoops=0, over=set(), tiny=tiny, boom=False)


def collide(a, b, r=96):
    if abs(a.z - b.z) > 46:
        return 0.0
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy)
    if d >= r or d < 0.01:
        return 0.0
    nx, ny = dx / d, dy / d
    push = (r - d) / 2
    a.x -= nx * push
    a.y -= ny * push
    b.x += nx * push
    b.y += ny * push
    rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if rel < 0:
        a.vx += nx * rel * 0.8
        a.vy += ny * rel * 0.8
        b.vx -= nx * rel * 0.8
        b.vy -= ny * rel * 0.8
    return abs(rel)


# ------------------------------------------------------------------ bots
class Bot:
    """Bot-truck: rijdt naar schansen, wrakken en vaten, en doet flips in de lucht (soms te gewaagd)."""

    def __init__(self, truck, game, skill):
        self.t, self.g, self.skill = truck, game, skill
        self.target, self.mode, self.ramp = None, "roam", None
        self.timer = 0.0
        self.plan = None
        self.wheelie = 0.0
        self.stuck = 0.0

    def pick(self):
        a, r = self.g.arena, random.random()
        todo = [w for w in a.wrecks + a.buses if not w.crushed] + [b for b in a.barrels if b.here]
        if r < 0.58 and a.ramps:
            self.ramp = random.choice(a.ramps)
            self.mode = "ramp"
            self.target = (self.ramp[0] - self.ramp[2] * 300, self.ramp[1] - self.ramp[3] * 300)
        elif r < 0.84 and todo:
            j = random.choice(todo)
            self.mode, self.target = "roam", (j.x, j.y)
        else:
            self.mode = "roam"
            self.target = (random.uniform(a.x0 + 250, a.x1 - 250), random.uniform(a.y0 + 250, a.y1 - 250))
        self.timer = 9.0

    def control(self, dt):
        t, a = self.t, self.g.arena
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
            if abs(v) < Wr * 0.9 and u > -380:
                tx, ty = sx + dx * (u + 240), sy + dy * (u + 240)       # recht op de lip af
            else:
                tx, ty = sx - dx * 300, sy - dy * 300                   # eerst naar het begin van de aanloop
            if u > L + 40:
                self.pick()
        elif math.hypot(tx - t.x, ty - t.y) < 90:
            self.pick()
        diff = wrap_rad(math.atan2(ty - t.y, tx - t.x) - t.heading)
        steer = clamp(diff * 2.6, -1, 1)
        fs = t.fwd
        thr, brk, boost = True, False, False
        if abs(diff) > 1.2 and fs > 200:
            thr, brk = False, True
        if self.mode == "ramp" and abs(diff) < 0.2 and t.nitro > 30:
            boost = True
        elif self.mode == "roam":
            if self.wheelie > 0:
                self.wheelie -= dt
                boost = t.nitro > 4
            elif fs > 160 and t.nitro > 60 and abs(diff) < 0.3 and random.random() < dt * 0.12:
                self.wheelie = random.uniform(1.4, 3.0)
        if fs < 25:
            self.stuck += dt
            if self.stuck > 1.4:
                steer, thr, brk = -steer, False, True
            if self.stuck > 2.4:
                self.stuck = 0.0
                self.pick()
        else:
            self.stuck = 0.0
        return thr, brk, steer, False, boost, 0, 0, False

    def _air(self):
        t, info = self.t, self.t.info
        if info["tiny"]:
            return False, False, 0, False, False, 0, 0, False
        if self.plan is None:
            T = 2 * max(t.vz, 0.0) / GRAV + 0.15
            if random.random() < 0.25 and T > 1.0:           # barrel roll
                n = min(int((T - 0.3) / (TAU / ROLL_RATE + 0.1)), 1 + int(self.skill * 2))
                self.plan = dict(kind="roll", n=n, d=random.choice([1, -1]), spin=0)
            else:
                n = min(int((T - 0.35) / (TAU / t.flip_rate + 0.12)), 1 + int(self.skill * 3))
                if n > 0 and random.random() < (1 - self.skill) * 0.4 + 0.04:
                    n += 1                                    # te gewaagd: kan misgaan
                spin = random.choice([-1, 1]) if (T > 1.3 and random.random() < 0.4) else 0
                self.plan = dict(kind="flip", n=n, d=random.choice([1, -1]), spin=spin)
        pl = self.plan
        flip = roll = 0
        if pl["kind"] == "roll":
            roll = pl["d"] if (pl["n"] > 0 and info["roll"] < pl["n"] * TAU - 0.6) else 0
        else:
            rot = info["back"] if pl["d"] > 0 else info["front"]
            flip = pl["d"] if (pl["n"] > 0 and rot < pl["n"] * TAU - 0.55) else 0
        steer = pl["spin"] if (pl["spin"] and abs(info["spin"]) < TAU - 0.5) else 0
        return False, False, steer, False, False, flip, roll, False


# ------------------------------------------------------------------ het spel
class Game:
    def __init__(self, app, arena, mode, duration, n_bots):
        self.app, self.arena, self.mode = app, arena, mode
        self.sfx = app.sfx
        self.theme = arena.theme
        self.duration = float(duration)
        self.time_left = self.duration
        self.clock = 0.0                                     # verstreken speeltijd
        arena.make_objects()
        self.targets = len(arena.wrecks) + len(arena.buses)
        cx, cy = arena.w / 2, arena.h / 2
        self.player = Truck(cx, arena.y1 - 190, -math.pi / 2, app.save["truck"], "JIJ", True)
        self.trucks, self.bots = [self.player], []
        spots = [(cx - 300, arena.y1 - 190), (cx + 300, arena.y1 - 190), (cx - 600, arena.y1 - 190), (cx + 600, arena.y1 - 190), (cx, arena.y0 + 190)]
        if mode == "battle":
            names = random.sample(BOT_NAMES, n_bots)
            skins = random.sample(range(len(PRESETS)), n_bots)
            for i in range(n_bots):
                tk = Truck(spots[i][0], spots[i][1], -math.pi / 2 if i < 4 else math.pi / 2, preset_cfg(skins[i]), names[i])
                self.trucks.append(tk)
                self.bots.append(Bot(tk, self, 0.5 + 0.08 * i + random.uniform(-0.05, 0.1)))
        self.parts = []                                      # [x, y, vx, vy, leeftijd, levensduur, grootte, kleur, soort]
        self.flashes = []                                    # cameraflitsen in het publiek
        self.booms = []                                      # vaten die straks ontploffen: [tijd, vat, truck]
        self.jet_t = 0.0                                     # > 0: de vlammenwerpers spuiten
        self.shake = 0.0
        self.flash = 0.0
        self.slow = 0.0                                      # > 0: slow motion na een grote stunt
        self.hype = 0.0
        self.frenzy = 0.0
        self.state = "countdown"
        self.countdown = 3.4
        self.cd_last = 4
        self.go_t = 0.0
        self.end_t = 0.0
        self.rpm, self.power = 0.2, 0.15
        self.fx_t = 0.0
        self.cam = [clamp(self.player.x - W / 2, 0, arena.w - W), clamp(self.player.y - H / 2, 0, arena.h - H)]
        self.radar, self.rk = arena.schematic((214, 150))
        self.dust_img = self._puffs(self.theme["dust"], 150)
        self.smoke_img = self._puffs((46, 44, 48), 170)
        self.night = self.theme["dark"] > 0
        self.rings = {}                                      # vuurringen: platte ellips, gedraaid per ring
        base = pygame.Surface((60, 176), pygame.SRCALPHA)
        for col, wd, inf in (((70, 24, 8), 12, 0), (FIRE, 7, -5), (GOLD, 3, -8)):
            pygame.draw.ellipse(base, col, base.get_rect().inflate(inf, inf), wd)
        for hx, hy, ha in arena.hoops:
            self.rings[round(ha, 2)] = pygame.transform.rotate(base, -math.degrees(ha))
        self.sfx.start_loops()

    @staticmethod
    def _puffs(col, a_max):
        out = []
        for s in (16, 24, 34, 46, 60, 76, 96):
            img = pygame.Surface((s, s), pygame.SRCALPHA)
            for r in range(s // 2, 0, -1):
                pygame.draw.circle(img, (*col, int(a_max * (1 - r / (s / 2)) ** 0.8)), (s // 2, s // 2), r)
            out.append(img)
        return out

    # ---- hulpjes
    def ranking(self):
        return sorted(self.trucks, key=lambda t: -t.score.total)

    def crushed(self):
        return sum(1 for w in self.arena.wrecks + self.arena.buses if w.crushed)

    def visible(self, x, y, m=200):
        return -m < x - self.cam[0] < W + m and -m < y - self.cam[1] < H + m

    def spawn(self, x, y, vx, vy, life, size, col, kind=0):
        self.parts.append([x, y, vx, vy, 0.0, life, size, col, kind])

    def burst(self, x, y, n, col, speed=(60, 200), kind=0, life=(0.4, 0.9), size=(5, 10)):
        for _ in range(n):
            a, sp = random.uniform(0, TAU), random.uniform(*speed)
            self.spawn(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(*life), random.uniform(*size), col, kind)

    def play(self, name, vol=1.0, t=None):
        if t is None or t.is_player or self.visible(t.x, t.y):
            self.sfx.play(name, vol if (t is None or t.is_player) else vol * 0.35)

    def award(self, t, title, base, col=GOLD, chain=True):
        """Punten geven. Bij de speler stijgt ook de HYPE van het publiek."""
        pts = t.score.add(title, base, col, chain)
        if t.is_player:
            self.hype = min(100.0, self.hype + pts / 60) if self.frenzy <= 0 else self.hype
            self.crowd_flash(int(clamp(pts / 150, 2, 30)))
            if pts >= 1500:
                self.sfx.play("cheer", clamp(pts / 5000, 0.4, 1.0))
            if pts >= 3000:
                self.slow = 0.5
                self.flash = 0.3
                self.jet_t = max(self.jet_t, 1.0)
        return pts

    def crowd_flash(self, n):
        for _ in range(n):
            r = random.choice(self.arena.stand_rects)
            self.flashes.append([random.uniform(r.left, r.right), random.uniform(r.top, r.bottom), random.uniform(0.0, 0.5)])

    # ---- invoer van de speler
    def _input(self, keys):
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        dn = keys[pygame.K_DOWN] or keys[pygame.K_s]
        steer = (1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0) - (1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0)
        flip = (1 if dn else 0) - (1 if up else 0)           # +1 = backflip
        roll = (1 if keys[pygame.K_e] else 0) - (1 if keys[pygame.K_q] else 0)
        hand = keys[pygame.K_x] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        return up, dn, steer, keys[pygame.K_SPACE], keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT], flip, roll, hand

    # ---- springen en landen
    def takeoff(self, t, vz, tiny=False):
        t.air, t.vz = True, vz
        t.info = new_info(tiny)
        if not tiny:
            self.play("jump", 0.7, t)
            self.burst(t.x, t.y, 8, self.theme["dust"], kind=0)

    def land(self, t, g):
        info = t.info
        impact = -t.vz
        t.z, t.air = g, False
        wp, wr = wrap_rad(t.pitch), wrap_rad(t.roll)
        t.vx *= 0.94
        t.vy *= 0.94
        if impact > 240:
            self.burst(t.x, t.y, int(min(22, impact / 40)), self.theme["dust"], (70, 230), 0, (0.5, 1.1), (8, 15))
            self.play("thud", clamp(impact / 700, 0.3, 1.0), t)
            if t.is_player:
                self.shake = max(self.shake, min(11, impact / 90))
        if info["tiny"]:
            t.pitch, t.pw, t.roll, t.rw = wp, 0.0, wr, 0.0
            return
        sc = t.score
        if abs(wp) >= 0.8 or abs(wr) >= 0.8:                 # op zijn dak of zijkant: crash
            t.stun = 1.5
            t.pitch = math.pi if abs(wp) > 2.3 else wp
            t.roll = math.pi if abs(wr) > 2.3 else wr
            t.pw = t.rw = 0.0
            t.vx *= 0.35
            t.vy *= 0.35
            sc.crash()
            self.burst(t.x, t.y, 18, GOLD, (80, 320), 1, (0.2, 0.5), (2, 3.5))
            self.burst(t.x, t.y, 6, (60, 60, 66), (60, 200), 3, (0.5, 1.0), (4, 7))
            self.play("hit", 0.9, t)
            if t.is_player:
                self.sfx.play("fail", 0.7)
                self.shake = max(self.shake, 12)
                self.hype = max(0.0, self.hype - 15)
            return
        t.pitch, t.pw, t.roll, t.rw = wp, 0.0, wr, 0.0
        parts = []
        nb, nf = int((info["back"] + 0.9) // TAU), int((info["front"] + 0.9) // TAU)
        ns, nr = int((abs(info["spin"]) + 1.0) // TAU), int((info["roll"] + 0.9) // TAU)
        if nb:
            parts.append((flip_name("BACKFLIP", nb), sum(500 * k for k in range(1, nb + 1))))
        if nf:
            parts.append((flip_name("FRONTFLIP", nf), sum(600 * k for k in range(1, nf + 1))))
        if nr:
            parts.append((flip_name("BARREL ROLL", nr), sum(700 * k for k in range(1, nr + 1))))
        if ns:
            parts.append((f"{ns * 360} SPIN", sum(400 * k for k in range(1, ns + 1))))
        if info["hoops"]:
            parts.append(("RING OF FIRE", 800 * info["hoops"]))
        if info["buses"]:
            parts.append((f"OVER {info['buses']} BUS" + ("SEN" if info["buses"] > 1 else ""), 500 * info["buses"]))
        if info["cars"]:
            parts.append((f"OVER {info['cars']} AUTO'S", 220 * info["cars"]))
        special = len(parts)
        if info["t"] > 0.6:
            parts.append(("BIG AIR" if info["peak"] > 170 else "SPRONG", int(info["t"] * 100 + info["peak"] * 0.8)))
            sc.n["jumps"] += 1
        if not parts:
            return
        base = sum(b for _, b in parts)
        if special >= 2:
            base = int(base * 1.5)
            title = "COMBO! " + " + ".join(n for n, _ in parts[:2])
        else:
            title = parts[0][0]
        if special and abs(wp) < 0.2 and abs(wr) < 0.2:      # mooi recht geland
            base = int(base * 1.2)
            title = "PERFECT " + title
        sc.n["flips"] += nb + nf
        sc.n["spins"] += ns
        sc.n["rolls"] += nr
        sc.n["cars"] += info["cars"] + info["buses"]
        sc.n["hoops"] += info["hoops"]
        col = PINK if base >= 3000 else (FIRE if base >= 1200 else GOLD)
        self.award(t, title, base, col)
        self.play("big" if base >= 1200 else "trick", 0.8, t)
        if t.is_player:
            self.shake = max(self.shake, 5)

    def drive(self, t, dt, inp):
        a = self.arena
        thr, brk, steer, hop, boost, flip, roll, hand = inp
        if t.stun > 0:
            t.stun -= dt
            thr = brk = hop = boost = hand = False
            steer = flip = roll = 0
        t.hop_cd = max(0.0, t.hop_cd - dt)
        t.ram_cd = max(0.0, t.ram_cd - dt)
        g = a.height(t.x, t.y)
        if hop and not t.air and t.hop_cd <= 0 and t.z <= g + 4:
            t.hop_cd = 0.7
            self.takeoff(t, t.hop_v)
        if t.air:
            t.boosting = False
            t.vx *= 1 - 0.05 * dt
            t.vy *= 1 - 0.05 * dt
            info = t.info
            t.heading += steer * SPIN_RATE * dt
            info["spin"] += steer * SPIN_RATE * dt
            info["t"] += dt
            rolling = abs(math.sin(t.roll)) > 0.03 or abs(t.rw) > 0.5
            flipping = abs(wrap_rad(t.pitch)) > 0.18
            if roll and not flipping:                        # barrel roll (niet tegelijk met een flip)
                t.rw += (roll * ROLL_RATE - t.rw) * min(1.0, dt * 9)
            else:
                w = wrap_rad(t.roll)
                t.rw += (-w * 24 - t.rw * 6) * dt if abs(w) < 1.3 else -t.rw * 1.6 * dt
            if flip and not rolling:
                t.pw += (flip * t.flip_rate - t.pw) * min(1.0, dt * 9)
            else:
                w = wrap_rad(t.pitch)
                t.pw += (-w * 22 - t.pw * 5.5) * dt if abs(w) < 1.3 else -t.pw * 1.6 * dt    # vanzelf rechtzetten
            dp, dr = t.pw * dt, t.rw * dt
            t.pitch += dp
            t.roll += dr
            info["back" if dp > 0 else "front"] += abs(dp)
            info["roll"] += abs(dr)
            t.vz -= GRAV * dt
            t.z += t.vz * dt
            info["peak"] = max(info["peak"], t.z)
            if t.z <= g and t.vz < 0:
                vz = t.vz
                self.land(t, g)
                if not t.info["tiny"] and -vz > 420 and t.stun <= 0:        # kleine stuiter na een harde landing
                    self.takeoff(t, -vz * 0.2, True)
        else:
            pit = a.in_pit(t.x, t.y) and t.z < 6
            t.in_pit = pit
            kind = self.theme["pit"]
            grip = (0.8 if kind == "ice" else 1.0) * ((0.16 if kind != "mud" else 0.5) if pit else 1.0)
            dh = t.ground_physics(dt, thr, brk, steer, hand, boost, grip, 1.3 if (pit and kind == "mud") else 0.0)
            if g >= t.z:
                nz = min(g, t.z + 700 * dt)
                t.rise = (nz - t.z) / dt
                t.z = nz
            elif t.z - g > 6:                                # over de lip van een schans
                self.takeoff(t, 120 + t.rise * 2.7 if t.rise > 40 else 0.0)
                t.rise = 0.0
            else:
                t.z = g
                t.rise = 0.0
            # wheelie op nitro
            wheelie = t.boosting and t.fwd > 70 and t.stun <= 0
            target = 0.55 if wheelie else (t.pitch if t.stun > 0 else 0.0)
            t.pitch += (target - t.pitch) * min(1.0, dt * 6)
            if t.stun <= 0:
                t.roll += (0.0 - t.roll) * min(1.0, dt * 6)
            if wheelie:
                t.wheelie_t += dt
            elif t.wheelie_t > 0:
                if t.wheelie_t >= 0.8:
                    t.score.n["wheelie"] += t.wheelie_t
                    self.award(t, f"WHEELIE {t.wheelie_t:.1f}s", int(t.wheelie_t * 160), CYAN)
                    self.play("trick", 0.6, t)
                t.wheelie_t = 0.0
            # donuts: snel rondjes draaien op de plek
            if abs(dh) > 1.7 * dt and t.speed < 300 and t.slip > 50:
                t.donut += abs(dh)
                t.donut_gap = 0.0
                if t.donut >= TAU:
                    t.donut -= TAU
                    t.donut_n += 1
                    t.score.n["donuts"] += 1
                    self.award(t, flip_name("DONUT", t.donut_n), 180 + 70 * t.donut_n, LIME)
                    self.play("trick", 0.5, t)
            else:
                t.donut_gap += dt
                if t.donut_gap > 0.6:
                    t.donut, t.donut_n = 0.0, 0
        t.x += t.vx * dt
        t.y += t.vy * dt
        # muur
        for ax, lo, hi, vk in (("x", a.x0 + 70, a.x1 - 70, "vx"), ("y", a.y0 + 70, a.y1 - 70, "vy")):
            v = getattr(t, ax)
            if v < lo or v > hi:
                setattr(t, ax, clamp(v, lo, hi))
                vel = getattr(t, vk)
                if (v < lo and vel < 0) or (v > hi and vel > 0):
                    setattr(t, vk, -vel * 0.35)
                    if abs(vel) > 120:
                        self.play("bump", clamp(abs(vel) / 400, 0.2, 0.9), t)
                        self.burst(t.x, t.y, 6, (30, 30, 34), (60, 200), 3, (0.4, 0.8), (4, 7))
                        if t.is_player:
                            self.shake = max(self.shake, min(8, abs(vel) * 0.02))

    # ---- alles wat in de arena staat
    def explode(self, b, t=None):
        if not b.here:
            return
        b.away = b.respawn if self.mode != "crush" else 1e9
        self.burst(b.x, b.y, 26, FIRE, (80, 460), 2, (0.3, 0.8), (14, 30))
        self.burst(b.x, b.y, 12, (40, 38, 42), (40, 200), 4, (0.8, 1.6), (16, 30))
        self.burst(b.x, b.y, 10, (200, 40, 30), (150, 420), 3, (0.5, 1.1), (4, 8))
        self.spawn(b.x, b.y, 0, 0, 0.45, 150, WHITE, 5)
        self.play("boom", 1.0 if self.visible(b.x, b.y) else 0.3)
        if self.visible(b.x, b.y):
            self.shake = max(self.shake, 13)
            self.flash = max(self.flash, 0.22)
        for tk in self.trucks:                               # trucks in de buurt vliegen de lucht in
            d = math.hypot(tk.x - b.x, tk.y - b.y)
            if d < 120 and tk.z < 60:
                if not tk.air:
                    self.takeoff(tk, 600)
                    tk.info["boom"] = True
                else:
                    tk.vz = max(tk.vz, 500)
                if d > 1:
                    tk.vx += (tk.x - b.x) / d * 120
                    tk.vy += (tk.y - b.y) / d * 120
        if t:
            t.score.n["booms"] += 1
            self.award(t, "KABOOM!", 160, HOT, chain=False)
        for o in self.arena.barrels:                         # kettingreactie
            if o.here and o is not b and math.hypot(o.x - b.x, o.y - b.y) < 130:
                self.booms.append([0.13, o, t])
        self.world_scorch(b.x, b.y)

    def world_scorch(self, x, y):
        s = pygame.Surface((150, 150), pygame.SRCALPHA)
        for r, al in ((74, 40), (56, 60), (36, 80)):
            pygame.draw.circle(s, (10, 8, 8, al), (75, 75), r)
        self.arena.world.blit(s, (x - 75, y - 75))

    def objects(self, dt):
        a = self.arena
        playing = self.state == "play"
        for th in a.barrels + a.stacks + a.pickups:
            if th.away > 0 and th.away < 1e8:
                th.away -= dt
        for q in self.booms:
            q[0] -= dt
        for q in [q for q in self.booms if q[0] <= 0]:
            self.explode(q[1], q[2])
        self.booms = [q for q in self.booms if q[0] > 0]
        for t in self.trucks:
            low = t.z < a.height(t.x, t.y) + 30
            for j in a.wrecks:
                if j.touches(t.x, t.y, 56):
                    if t.air and t.z > 36 and not t.info["tiny"]:
                        if id(j) not in t.info["over"]:
                            t.info["over"].add(id(j))
                            t.info["cars"] += 1
                    elif not j.crushed and t.z < 30 and j.touches(t.x, t.y, 50):
                        j.crushed = True
                        t.score.n["crushes"] += 1
                        self.award(t, "CRUSH!", 100, FIRE, chain=False)
                        self.burst(j.x, j.y, 14, (210, 214, 224), (80, 280), 1, (0.2, 0.5), (2, 3.5))
                        self.burst(j.x, j.y, 8, (70, 72, 80), (60, 220), 3, (0.5, 1.0), (4, 8))
                        self.burst(j.x, j.y, 5, self.theme["dust"], (30, 90), 0, (0.5, 1.0), (10, 16))
                        self.play("crush", 0.8, t)
                        t.vx *= 0.86
                        t.vy *= 0.86
                        if t.is_player:
                            self.shake = max(self.shake, 4)
            for b in a.buses:
                if b.touches(t.x, t.y, 34):
                    if t.air and t.z > 44 and not t.info["tiny"]:
                        if id(b) not in t.info["over"]:
                            t.info["over"].add(id(b))
                            t.info["buses"] += 1
                    elif not b.crushed and t.z < 30 and b.touches(t.x, t.y, 22):
                        b.crushed = True
                        t.score.n["crushes"] += 1
                        self.award(t, "BUS CRUSH!", 400, HOT, chain=False)
                        self.burst(b.x, b.y, 26, (210, 214, 224), (80, 320), 1, (0.2, 0.6), (2, 4))
                        self.burst(b.x, b.y, 16, (200, 170, 60), (60, 260), 3, (0.5, 1.2), (5, 10))
                        self.burst(b.x, b.y, 8, (46, 44, 48), (20, 80), 4, (0.8, 1.4), (16, 26))
                        self.play("crush", 1.0, t)
                        self.play("boom", 0.4, t)
                        t.vx *= 0.6
                        t.vy *= 0.6
                        if t.is_player:
                            self.shake = max(self.shake, 9)
            if not playing:
                continue
            if low:
                for b in a.barrels:
                    if b.here and (t.x - b.x) ** 2 + (t.y - b.y) ** 2 < 58 ** 2:
                        self.explode(b, t)
                for s in a.stacks:
                    if s.here and (t.x - s.x) ** 2 + (t.y - s.y) ** 2 < 64 ** 2 and t.speed > 60:
                        s.away = s.respawn
                        self.award(t, "SMASH!", 60, STEEL, chain=False)
                        col = (236, 242, 250) if self.theme["pit"] == "ice" else (24, 24, 27)
                        for _ in range(9):
                            ang = math.atan2(t.vy, t.vx) + random.uniform(-1.1, 1.1)
                            sp = t.speed * random.uniform(0.5, 1.3)
                            self.spawn(s.x, s.y, math.cos(ang) * sp, math.sin(ang) * sp, random.uniform(0.7, 1.5), random.uniform(10, 16), col, 6)
                        self.play("smash", 0.8, t)
                        t.vx *= 0.85
                        t.vy *= 0.85
            for p in a.pickups:
                if p.here and (t.x - p.x) ** 2 + (t.y - p.y) ** 2 < 62 ** 2 and t.z < 90:
                    p.away = p.respawn
                    kind = "nitro" if (p.kind == "time" and self.mode == "crush") else p.kind
                    if kind == "nitro":
                        t.nitro = t.nitro_cap
                        t.score.events.append(["NITRO VOL!", "", CYAN, 0.0, 0])
                    elif kind == "x2":
                        t.x2_t = 12.0
                        t.score.events.append(["DUBBELE PUNTEN!", "12 seconden", GOLD, 0.0, 0])
                    elif t.is_player:
                        self.time_left += 10
                        t.score.events.append(["+10 SECONDEN", "", LIME, 0.0, 0])
                    self.burst(p.x, p.y, 12, {"nitro": CYAN, "x2": GOLD, "time": LIME}[p.kind], (80, 240), 1, (0.3, 0.6), (2, 4))
                    self.play("pickup", 0.8, t)
            if t.air and not t.info["tiny"] and 40 < t.z < 460:   # door een vuurring springen
                for k, (hx, hy, ha) in enumerate(a.hoops):
                    if ("h", k) not in t.info["over"] and (t.x - hx) ** 2 + (t.y - hy) ** 2 < 74 ** 2:
                        t.info["over"].add(("h", k))
                        t.info["hoops"] += 1
                        self.burst(hx, hy, 22, FIRE, (100, 380), 2, (0.3, 0.7), (12, 24))
                        self.play("fire", 0.9, t)
                        if t.is_player:
                            self.flash = max(self.flash, 0.15)

    # ---- effecten per truck
    def effects(self, t, dt):
        fx, fy = math.cos(t.heading), math.sin(t.heading)
        rx, ry = -fy, fx
        sp = t.speed
        on_ground = not t.air and t.z < 40
        wl = (t.x - fx * 42 + rx * 44, t.y - fy * 42 + ry * 44)
        wr = (t.x - fx * 42 - rx * 44, t.y - fy * 42 - ry * 44)
        if on_ground and sp > 40 and t.wheels and not self.arena.height(t.x, t.y):     # bandensporen op de vloer
            col = mix(self.theme["base"], self.theme["track"], 0.85 if t.slip > 60 else 0.55)
            pygame.draw.line(self.arena.world, col, t.wheels[0], wl, 9)
            pygame.draw.line(self.arena.world, col, t.wheels[1], wr, 9)
        t.wheels = (wl, wr) if on_ground else None
        if not self.visible(t.x, t.y):
            return
        dust = self.theme["dust"]
        if on_ground and sp > 90 and random.random() < clamp(sp / 400, 0.15, 0.95):
            for w in (wl, wr):
                self.spawn(w[0], w[1], random.uniform(-30, 30) - t.vx * 0.12, random.uniform(-30, 30) - t.vy * 0.12,
                           random.uniform(0.5, 1.0), random.uniform(7, 12) * (1.6 if t.slip > 90 else 1.0), dust)
        if on_ground and t.in_pit and sp > 40:
            col = {"mud": (96, 64, 36), "oil": (20, 18, 24), "ice": (226, 244, 255)}[self.theme["pit"]]
            self.burst(t.x, t.y, 2, col, (60, 220), 3 if self.theme["pit"] != "ice" else 1, (0.4, 0.8), (3, 6))
        if on_ground and t.slip > 120 and sp > 120:          # kluiten die wegspatten
            self.spawn(wl[0], wl[1], -t.vx * 0.3 + random.uniform(-80, 80), -t.vy * 0.3 + random.uniform(-80, 80), random.uniform(0.3, 0.6),
                       random.uniform(3, 5), mix(self.theme["base"], (0, 0, 0), 0.3), 3)
        if t.boosting:                                       # nitro-vlammen
            for sd in (-1, 1):
                ex, ey = t.x - fx * 64 + rx * sd * 14, t.y - fy * 64 + ry * sd * 14 - t.z * 0.5
                self.spawn(ex, ey, -fx * random.uniform(160, 280) + t.vx * 0.3, -fy * random.uniform(160, 280) + t.vy * 0.3,
                           random.uniform(0.12, 0.28), random.uniform(10, 18), random.choice([FIRE, GOLD, HOT, CYAN]), 2)
        if t.air and t.info and not t.info["tiny"] and (abs(t.pw) > 3 or abs(t.rw) > 3) and random.random() < 0.6:
            self.spawn(t.x + random.uniform(-30, 30), t.y - t.z * 0.5 + random.uniform(-30, 30), 0, 0, 0.3, 3, WHITE, 1)   # flip-glinstering
        if t.stun > 0 and random.random() < dt * 26:
            self.spawn(t.x + random.uniform(-20, 20), t.y + random.uniform(-20, 20), random.uniform(-30, 30), -random.uniform(20, 70),
                       random.uniform(0.7, 1.3), random.uniform(12, 20), (46, 44, 48), 4)

    def reset_truck(self):
        """R: de truck van de speler rechtop zetten."""
        p = self.player
        p.pitch = p.pw = p.roll = p.rw = p.vz = 0.0
        p.z = self.arena.height(p.x, p.y)
        p.air, p.stun = False, 0.0
        p.vx *= 0.3
        p.vy *= 0.3

    # ---- hoofdlogica
    def update(self, real_dt, keys):
        real_dt = min(real_dt, 0.05)
        self.slow = max(0.0, self.slow - real_dt)
        dt = real_dt * (0.4 if self.slow > 0 else 1.0)
        p, a = self.player, self.arena
        self.fx_t += real_dt
        playing = self.state == "play"
        if self.state == "countdown":
            self.countdown -= dt
            n = math.ceil(max(self.countdown, 0))
            if n != self.cd_last:
                self.cd_last = n
                if n in (1, 2, 3):
                    self.sfx.play("beep")
            if self.countdown <= 0:
                self.state, self.go_t = "play", 1.2
                self.sfx.play("go")
                self.sfx.play("horn", 0.6)
        elif playing:
            self.clock += dt
            self.go_t = max(0.0, self.go_t - dt)
            if self.mode == "crush":
                if self.crushed() >= self.targets:
                    self.finish()
            else:
                self.time_left -= dt
                if 0 < self.time_left <= 5 and int(self.time_left + dt) != int(self.time_left):
                    self.sfx.play("beep", 0.6)
                if self.time_left <= 0:
                    self.time_left = 0.0
                    self.finish()
        else:
            self.end_t += real_dt
        idle = (False, False, 0, False, False, 0, 0, False)
        for t in self.trucks:
            if not playing:
                inp = idle
            elif t.is_player:
                inp = self._input(keys)
            else:
                inp = next(b for b in self.bots if b.t is t).control(dt)
            self.drive(t, dt, inp)
            t.x2_t = max(0.0, t.x2_t - dt)
            t.score.bonus = (2 if t.x2_t > 0 else 1) * (2 if (self.frenzy > 0 and t.is_player) else 1)
        tr = self.trucks
        for i in range(len(tr)):                             # truck tegen truck
            for j in range(i + 1, len(tr)):
                x, y = tr[i], tr[j]
                imp = collide(x, y)
                if imp > 40:
                    self.burst((x.x + y.x) / 2, (x.y + y.y) / 2, int(min(12, imp / 22)), GOLD, (80, 280), 1, (0.2, 0.4), (2, 3))
                    if x.is_player or y.is_player:
                        self.shake = max(self.shake, min(9, imp * 0.03))
                        self.sfx.play("hit", clamp(imp / 300, 0.3, 1.0))
                    if imp > 260 and playing:                # beuk: de snelste krijgt punten
                        att = x if x.speed > y.speed else y
                        if att.ram_cd <= 0:
                            att.ram_cd = 1.5
                            self.award(att, "RAM!", 120, HOT, chain=False)
        self.objects(dt)
        for t in tr:
            t.score.update(dt)
            self.effects(t, dt)
        # ---- publiek
        if playing:
            if self.frenzy > 0:
                self.frenzy -= dt
                self.jet_t = max(self.jet_t, 0.2)
                if random.random() < 0.5:
                    self.crowd_flash(3)
                if self.frenzy <= 0:
                    self.hype = 0.0
            else:
                self.hype = max(0.0, self.hype - 2.2 * dt)
                if self.hype >= 100:
                    self.frenzy = 10.0
                    self.sfx.play("cheer", 1.0)
                    self.sfx.play("horn", 0.8)
                    self.flash = 0.35
                    p.score.events.append(["HET PUBLIEK WORDT GEK!", "alles telt dubbel", PINK, 0.0, 0])
            if random.random() < 0.03 + self.hype / 400:
                self.crowd_flash(1)
        if self.jet_t > 0:                                   # vlammenwerpers langs de muur
            self.jet_t -= dt
            for jx, jy in a.jets:
                if self.visible(jx, jy, 60) and random.random() < 0.8:
                    d = 1 if jy < a.h / 2 else -1
                    self.spawn(jx + random.uniform(-5, 5), jy, random.uniform(-25, 25), d * random.uniform(150, 330),
                               random.uniform(0.3, 0.6), random.uniform(16, 30), random.choice([FIRE, GOLD, HOT]), 2)
        # ---- deeltjes
        damp = max(0.0, 1 - 3.2 * dt)
        for q in self.parts:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] += dt
            if q[8] in (1, 3, 6):
                q[2] *= damp
                q[3] *= damp
        self.parts = [q for q in self.parts if q[4] < q[5]][-700:]
        for f in self.flashes:
            f[2] -= dt
        self.flashes = [f for f in self.flashes if f[2] > -0.14][-160:]
        self.shake *= max(0.0, 1 - 7 * real_dt)
        self.flash = max(0.0, self.flash - real_dt)
        # ---- camera (kijkt vooruit en tilt mee met de hoogte)
        tx = p.x + p.vx * 0.3 - W / 2
        ty = p.y + p.vy * 0.3 - H / 2 - max(0.0, p.z) * 0.45
        k = min(1, real_dt * 5)
        self.cam[0] = clamp(self.cam[0] + (tx - self.cam[0]) * k, 0, a.w - W)
        self.cam[1] = clamp(self.cam[1] + (ty - self.cam[1]) * k, 0, a.h - H)
        self.audio(real_dt)

    def finish(self):
        self.state = "finished"
        self.sfx.play("finish")
        self.sfx.play("horn", 0.7)
        self.sfx.play("cheer", 1.0)
        self.jet_t = 2.5
        self.crowd_flash(60)
        p = self.player
        for _ in range(90):                                  # confetti
            self.spawn(p.x + random.uniform(-500, 500), p.y - 300 + random.uniform(-150, 150), random.uniform(-60, 60), random.uniform(60, 190),
                       random.uniform(1.6, 3.2), random.uniform(4, 7), random.choice([GOLD, RED, CYAN, LIME, PINK, WHITE]), 7)

    def audio(self, dt):
        p = self.player
        spd = p.speed
        gears = p.vmax * 1.25 / 4
        target = 0.2 + 0.75 * ((spd % gears) / gears) * 0.6 + 0.4 * min(1.0, spd / (p.vmax * 1.25))
        if p.air:
            target = 0.95
        self.rpm += (target - self.rpm) * min(1.0, dt * 9)
        self.power += ((1.0 if p.boosting or p.air else 0.3 if spd > 30 else 0.15) - self.power) * min(1.0, dt * 8)
        near = 0.0
        for c in self.trucks:
            if not c.is_player:
                near = max(near, clamp(1 - math.hypot(c.x - p.x, c.y - p.y) / 700, 0, 1))
        self.sfx.loops(self.rpm, self.power, p.boosting, 0.0 if p.air else clamp(spd / 400, 0.0, 1.0), near,
                       1.0 if self.frenzy > 0 else self.hype / 140, mute=self.state == "finished" and self.end_t > 3)

    # ---------------------------------------------------------------- tekenen
    def draw_truck(self, s, t, cx, cy):
        sx, sy = t.x - cx, t.y - cy
        if not (-260 < sx < W + 260 and -260 < sy < H + 260):
            return
        z = max(0.0, t.z)
        ang = -math.degrees(t.heading)
        sh = pygame.transform.rotozoom(t.art.shadow, ang, max(0.5, 1 - z / 560))
        sh.set_alpha(int(255 * max(0.3, 1 - z / 420)))
        s.blit(sh, sh.get_rect(center=(sx + 8 + z * 0.25, sy + 10 + z * 0.25)))
        if self.night and z < 60:                            # koplampen in het donker
            cone = pygame.transform.rotate(self.app.assets["cone"], ang)
            s.blit(cone, cone.get_rect(center=(sx + math.cos(t.heading) * 50, sy + math.sin(t.heading) * 50)), special_flags=pygame.BLEND_RGB_ADD)
        img = t.art.proj(t.pitch, t.roll)
        k = min(1.9, 1 + z / 420) * (1 + 0.08 * max(abs(math.sin(t.pitch)), abs(math.sin(t.roll))))
        rot = pygame.transform.rotozoom(img, ang, k)
        lift = z * 0.5 + (abs(math.sin(t.pitch)) + abs(math.sin(t.roll))) * 14
        s.blit(rot, rot.get_rect(center=(sx, sy - lift)))
        if t.x2_t > 0:
            g = glow(120, dim(GOLD, 0.35 + 0.1 * (int(self.fx_t * 8) % 2)), 1.6)
            s.blit(g, (sx - 60, sy - lift - 60), special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, s):
        a, p = self.arena, self.player
        sx = sy = 0.0
        if self.shake > 0.3:
            sx, sy = random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)
        cx = int(clamp(self.cam[0] + sx, 0, a.w - W))
        cy = int(clamp(self.cam[1] + sy, 0, a.h - H))
        ft = self.fx_t
        s.blit(a.world, (0, 0), pygame.Rect(cx, cy, W, H))
        for fx_, fy_, t0 in self.flashes:                     # cameraflitsen op de tribune
            if t0 <= 0 and -20 < fx_ - cx < W + 20 and -20 < fy_ - cy < H + 20:
                g = glow(44, (255, 255, 255), 1.3)
                s.blit(g, (fx_ - cx - 22, fy_ - cy - 22), special_flags=pygame.BLEND_RGB_ADD)
        for o in a.wrecks + a.buses:
            if self.visible(o.x, o.y, 160):
                o.draw(s, cx, cy)
        spr = a.sprites
        for th in a.barrels + a.stacks:
            if th.here and self.visible(th.x, th.y, 60):
                img = spr[th.kind]
                s.blit(img, img.get_rect(center=(th.x - cx, th.y - cy)))
            elif 0 < th.away < 1.5 and int(ft * 10) % 2:      # komt bijna terug: knippert
                pygame.draw.circle(s, WHITE, (th.x - cx, th.y - cy), 20, 2)
        for pk in a.pickups:
            if pk.here and self.visible(pk.x, pk.y, 60):
                col = {"nitro": CYAN, "x2": GOLD, "time": LIME}[pk.kind]
                bob = math.sin(ft * 4 + pk.x) * 5
                g = glow(130, dim(col, 0.4 + 0.12 * math.sin(ft * 6 + pk.y) ** 2 // 0.06 * 0.06), 1.6)
                s.blit(g, (pk.x - cx - 65, pk.y - cy - 65), special_flags=pygame.BLEND_RGB_ADD)
                pygame.draw.ellipse(s, (0, 0, 0), (pk.x - cx - 20, pk.y - cy + 22, 40, 12))
                img = spr[pk.kind]
                s.blit(img, img.get_rect(center=(pk.x - cx, pk.y - cy - 8 + bob)))
        self.draw_parts(s, cx, cy, (0, 3, 6))
        for t in sorted(self.trucks, key=lambda t: (t.z, t.is_player)):
            self.draw_truck(s, t, cx, cy)
        for hx, hy, ha in a.hoops:                            # vuurringen (hangen boven de grond)
            if self.visible(hx, hy, 140):
                nx, ny = -math.sin(ha), math.cos(ha)
                ax_, ay_ = hx + nx * 78 - cx, hy + ny * 78 - cy
                bx_, by_ = hx - nx * 78 - cx, hy - ny * 78 - cy
                pygame.draw.line(s, (0, 0, 0), (ax_ + 14, ay_ + 22), (bx_ + 14, by_ + 22), 8)
                for q in ((ax_, ay_), (bx_, by_)):
                    pygame.draw.circle(s, (20, 20, 24), q, 13)
                    pygame.draw.circle(s, (110, 114, 128), q, 10)
                ring = self.rings[round(ha, 2)]
                s.blit(ring, ring.get_rect(center=(hx - cx, hy - cy - 30)))
                for k in range(9):
                    f = k / 8
                    fl = 0.6 + 0.4 * math.sin(ft * 11 + k * 2.1)
                    px, py = lerp(ax_, bx_, f), lerp(ay_, by_, f) - 30
                    g = glow(64, dim(FIRE, 0.5 + 0.3 * round(fl, 1)), 1.4)
                    s.blit(g, (px - 32, py - 36 - 6 * fl), special_flags=pygame.BLEND_RGB_ADD)
                    pygame.draw.polygon(s, GOLD, [(px - 5, py), (px + 5, py), (px + math.sin(ft * 9 + k) * 4, py - 12 - 10 * fl)])
        self.draw_parts(s, cx, cy, (1, 2, 4, 5, 7))
        if self.mode == "battle" and self.visible(p.x, p.y, 0):
            text(s, "JIJ", 15, (p.x - cx, p.y - cy - 72 - p.z * 0.5 + 3 * math.sin(ft * 5)), WHITE, "midbottom")
        for t in self.trucks:                                 # namen en punten van bots boven hun truck
            if not t.is_player and self.visible(t.x, t.y, 0):
                text(s, t.name, 15, (t.x - cx, t.y - cy - 70 - t.z * 0.5), GOLD, "midbottom")
                if t.score.events and t.score.events[-1][3] < 1.6:
                    e = t.score.events[-1]
                    text(s, f"{e[0]}  {e[1]}", 14, (t.x - cx, t.y - cy - 90 - t.z * 0.5 - e[3] * 26), e[2], "midbottom")
        A = self.app.assets
        # twee zwaaiende schijnwerpers + een volgspot op de speler
        for k in range(2):
            lx = a.w / 2 + math.sin(ft * 0.5 + k * 3.1) * a.w * 0.34 - cx
            ly = a.h / 2 + math.sin(ft * 0.8 + k * 1.3) * a.h * 0.26 - cy
            if -300 < lx < W + 300 and -300 < ly < H + 300:
                s.blit(A["spot"], (lx - 300, ly - 300), special_flags=pygame.BLEND_RGB_ADD)
        if p.air and p.info and not p.info["tiny"]:
            s.blit(A["spot2"], (p.x - cx - 200, p.y - cy - p.z * 0.5 - 200), special_flags=pygame.BLEND_RGB_ADD)
        if self.theme["pit"] == "ice":                        # sneeuwvlokken
            for k in range(70):
                fx_ = (k * 197.3 + ft * (20 + k % 7 * 6) - cx * 1.1) % W
                fy_ = (k * 91.7 + ft * (60 + k % 5 * 22) - cy * 1.1) % H
                pygame.draw.circle(s, (240, 246, 255), (fx_, fy_), 1 + k % 3)
        if self.frenzy > 0:
            s.blit(A["edge_pink"], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        elif p.boosting:
            s.blit(A["edge_fire"], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(A["vignette"], (0, 0))
        if self.flash > 0:
            A["white"].set_alpha(int(210 * min(1.0, self.flash * 3)))
            s.blit(A["white"], (0, 0))
        self.draw_hud(s)

    def draw_parts(self, s, cx, cy, kinds):
        for x, y, vx, vy, age, life, size, col, kind in self.parts:
            if kind not in kinds:
                continue
            px, py = x - cx, y - cy
            if not (-60 < px < W + 60 and -60 < py < H + 60):
                continue
            u = age / life
            if kind in (0, 4):                                # stof / rook
                imgs = self.dust_img if kind == 0 else self.smoke_img
                img = imgs[min(6, int(size * (0.6 + u * 1.8) / 7))]
                img.set_alpha(int(255 * (1 - u) ** 1.2))
                s.blit(img, (px - img.get_width() / 2, py - img.get_height() / 2))
            elif kind == 1:                                   # vonk
                pygame.draw.line(s, mix(col, (255, 255, 255), 0.5 * (1 - u)), (px, py), (px - vx * 0.03, py - vy * 0.03), max(1, int(size * (1 - u * 0.6))))
            elif kind == 2:                                   # vuur (additief)
                uq = int(u * 5) / 5                           # in stapjes, zodat de gloed uit de cache komt
                g = glow(int(size * (1.6 + uq) * 2) // 8 * 8 + 12, dim(mix(col, (120, 30, 10), uq), 1 - uq * 0.5), 1.4)
                s.blit(g, (px - g.get_width() / 2, py - g.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
            elif kind == 3:                                   # brokstuk
                a = age * 9 + x
                d = size * (1 - u * 0.4)
                pygame.draw.polygon(s, col, [(px + math.cos(a + k * 1.57) * d, py + math.sin(a + k * 1.57) * d * 0.7) for k in range(4)])
            elif kind == 5:                                   # schokgolf
                r = size * (0.3 + u * 1.6)
                pygame.draw.circle(s, mix(col, self.theme["base"], u), (px, py), r, max(1, int(8 * (1 - u))))
            elif kind == 6:                                   # rollende band / sneeuwbal
                pygame.draw.circle(s, (0, 0, 0), (px + 3, py + 4), size)
                pygame.draw.circle(s, col, (px, py), size)
                pygame.draw.circle(s, mix(col, (128, 128, 128), 0.5), (px, py), size, 3)
            else:                                             # confetti
                w = size * abs(math.sin(age * 8 + x))
                pygame.draw.rect(s, col, (px - w / 2, py - size / 2, max(1, w), size))

    def draw_hud(self, s):
        p, sc = self.player, self.player.score
        ft = self.fx_t
        # ---- linksboven: score + combo
        panel(s, (16, 14, 320, 116))
        text(s, "SCORE", 15, (34, 20), FIRE)
        s.blit(chrome(fmt_pts(sc.total), 46, G_FIRE if sc.bonus == 1 else G_PINK, o=2), (30, 34))
        if sc.bonus > 1:
            text(s, f"x{sc.bonus} BONUS", 16, (322, 22), PINK if int(ft * 6) % 2 else GOLD, "topright")
        text(s, f"COMBO  x{sc.mult:.1f}" if sc.chain else "COMBO  -", 16, (34, 100), GOLD if sc.chain else (150, 120, 100))
        if sc.chain:
            pygame.draw.rect(s, (50, 30, 12), (176, 106, 144, 10))
            pygame.draw.rect(s, GOLD if sc.chain_t > 1.5 or int(ft * 8) % 2 else RED, (176, 106, int(144 * clamp(sc.chain_t / 5, 0, 1)), 10))
        # ---- midden boven: tijd (of wrakken) + hype
        panel(s, (W // 2 - 150, 14, 300, 96))
        if self.mode == "crush":
            text(s, f"WRAKKEN  {self.crushed()} / {self.targets}", 16, (W // 2, 20), FIRE, "midtop")
            img = chrome(fmt_time(self.clock), 42, G_STEEL, o=2)
        else:
            tl = max(0, math.ceil(self.time_left))
            text(s, MODES[self.mode], 15, (W // 2, 20), FIRE, "midtop")
            img = chrome(f"{tl // 60}:{tl % 60:02d}", 42, G_FIRE if tl > 10 or int(ft * 4) % 2 else G_STEEL, o=2)
        s.blit(img, img.get_rect(midtop=(W // 2, 32)))
        frenzy = self.frenzy > 0
        hazard(s, (W // 2 - 136, 88, 272, 14), ft * 40, (60, 40, 20), (24, 16, 12))
        wbar = int(272 * (self.frenzy / 10 if frenzy else self.hype / 100))
        if wbar > 0:
            col = (PINK if int(ft * 10) % 2 else GOLD) if frenzy else mix(FIRE, PINK, self.hype / 100)
            pygame.draw.rect(s, col, (W // 2 - 136, 88, wbar, 14))
        text(s, "PUBLIEK GAAT LOS!  x2" if frenzy else "HYPE", 12, (W // 2, 87), WHITE, "midtop")
        # ---- rechtsboven: stand (battle) of beste stunt
        if self.mode == "battle":
            order = self.ranking()
            panel(s, (W - 296, 14, 280, 40 + 27 * len(order)))
            text(s, "STAND", 15, (W - 278, 20), FIRE)
            for i, t in enumerate(order):
                col = GOLD if t.is_player else (230, 220, 210)
                pygame.draw.circle(s, t.color, (W - 272, 59 + i * 27), 7)
                pygame.draw.circle(s, WHITE, (W - 272, 59 + i * 27), 7, 1)
                text(s, f"{i + 1}. {t.name}", 16, (W - 258, 47 + i * 27), col)
                text(s, fmt_pts(t.score.total), 16, (W - 30, 47 + i * 27), col, "topright")
        else:
            panel(s, (W - 336, 14, 320, 86))
            if self.mode == "free":
                name, col, need = medal_for("free", sc.total, self)
                text(s, "MEDAILLE", 15, (W - 318, 20), FIRE)
                text(s, name or "nog geen", 22, (W - 318, 40), col)
                text(s, f"doel  {fmt_pts(need)}", 15, (W - 318, 72), (220, 210, 200))
            else:
                name, col, need = medal_for("crush", self.clock, self)
                text(s, "MEDAILLE-TIJD", 15, (W - 318, 20), FIRE)
                text(s, name or "te traag", 22, (W - 318, 40), col)
                text(s, f"binnen  {fmt_time(need)}", 15, (W - 318, 72), (220, 210, 200))
        # ---- stuntmeldingen
        y = 122
        for title, txt_, col, age, pts in sc.events[::-1][:3]:
            k = clamp(min(age * 7, (2.6 - age) * 2.5), 0, 1)
            big = pts >= 1200
            img = chrome(title, 38 if big else 24, G_PINK if col == PINK else G_FIRE if col in (FIRE, HOT, RED) else G_ICE if col == CYAN
                         else G_LIME if col == LIME else G_STEEL if col == STEEL else G_GOLD, o=3 if big else 2)
            if k < 1:
                img = img.copy()
                img.set_alpha(int(255 * k))
            r = img.get_rect(midtop=(W // 2 + (1 - min(1, age * 6)) * 220, y))
            s.blit(img, r)
            if txt_:
                text(s, txt_, 18 if big else 15, (W // 2, r.bottom - 7), WHITE, "midtop")
            y = r.bottom + (16 if txt_ else 0)
        # ---- live stunt-info in de lucht
        if p.air and p.info and not p.info["tiny"]:
            info = p.info
            nb, nf = int((info["back"] + 0.9) // TAU), int((info["front"] + 0.9) // TAU)
            ns, nr = int((abs(info["spin"]) + 1.0) // TAU), int((info["roll"] + 0.9) // TAU)
            bits = [f"LUCHT {info['t']:.1f}s"]
            for n, nm in ((nb, "BACKFLIP"), (nf, "FRONTFLIP"), (nr, "BARREL ROLL")):
                if n:
                    bits.append(flip_name(nm, n))
            if ns:
                bits.append(f"{ns * 360} SPIN")
            if info["hoops"]:
                bits.append("RING OF FIRE")
            if info["cars"] + info["buses"]:
                bits.append(f"OVER {info['cars'] + info['buses']}")
            line = "   +   ".join(bits)
            wd = render(line, 20).get_width() + 44
            panel(s, (W // 2 - wd // 2, H - 96, wd, 38), edge=GOLD)
            text(s, line, 20, (W // 2, H - 92), GOLD, "midtop")
        elif p.wheelie_t > 0.3:
            text(s, f"WHEELIE  {p.wheelie_t:.1f}s", 22, (W // 2, H - 92), CYAN, "midtop")
        elif p.donut_n or p.donut > 2:
            text(s, f"DONUT  {p.donut_n}  ({int(math.degrees(p.donut))})", 22, (W // 2, H - 92), LIME, "midtop")
        elif p.stun > 0:
            text(s, "CRASH!   druk R om rechtop te zetten", 20, (W // 2, H - 92), RED if int(ft * 6) % 2 else WHITE, "midtop")
        # ---- rechtsonder: snelheid + nitro
        panel(s, (W - 286, H - 124, 270, 108))
        img = chrome(f"{int(p.speed * 0.3):3d}", 54, G_STEEL, o=2)
        s.blit(img, img.get_rect(bottomright=(W - 110, H - 44)))
        text(s, "km/u", 15, (W - 104, H - 70), STEEL)
        if p.x2_t > 0:
            text(s, f"x2  {p.x2_t:.0f}s", 20, (W - 34, H - 112), GOLD, "topright")
        text(s, "NITRO", 13, (W - 270, H - 40), FIRE)
        pygame.draw.rect(s, (40, 22, 10), (W - 212, H - 38, 180, 12))
        nw = int(180 * p.nitro / p.nitro_cap)
        pygame.draw.rect(s, WHITE if p.boosting and int(ft * 24) % 2 else (FIRE if p.nitro > 15 else RED), (W - 212, H - 38, nw, 12))
        for k in range(1, 9):
            pygame.draw.line(s, (16, 10, 8), (W - 212 + k * 20, H - 38), (W - 212 + k * 20, H - 27), 2)
        # ---- linksonder: radar
        rw, rh = self.radar.get_size()
        panel(s, (16, H - rh - 34, rw + 20, rh + 20))
        ox, oy = 26, H - rh - 24
        s.blit(self.radar, (ox, oy))
        a = self.arena
        for w in a.wrecks + a.buses:
            if w.crushed:
                pygame.draw.circle(s, (70, 60, 56), (ox + (w.x - a.x0) * self.rk, oy + (w.y - a.y0) * self.rk), 3)
        for pk in a.pickups:
            if pk.here:
                pygame.draw.circle(s, {"nitro": CYAN, "x2": GOLD, "time": LIME}[pk.kind], (ox + (pk.x - a.x0) * self.rk, oy + (pk.y - a.y0) * self.rk), 3)
        for t in self.trucks[::-1]:
            q = (ox + (t.x - a.x0) * self.rk, oy + (t.y - a.y0) * self.rk)
            pygame.draw.circle(s, (0, 0, 0), q, 6)
            pygame.draw.circle(s, (WHITE if int(ft * 6) % 2 else GOLD) if t.is_player else t.color, q, 5 if t.is_player else 4)
        # ---- aftellen / einde
        if self.state == "countdown":
            n = math.ceil(max(self.countdown, 0))
            if n <= 3:
                f = self.countdown % 1.0
                img = chrome(str(max(1, n)), int(150 + 90 * f), G_FIRE, o=6)
                s.blit(img, img.get_rect(center=(W // 2, 250)))
            else:
                img = chrome(a.spec["name"], 76, G_STEEL, o=5)
                s.blit(img, img.get_rect(center=(W // 2, 240)))
                text(s, MODES[self.mode], 30, (W // 2, 300), FIRE, "midtop")
        elif self.go_t > 0:
            img = chrome("GO!", 170, G_LIME, o=6)
            img.set_alpha(int(255 * clamp(self.go_t / 0.6, 0, 1)))
            s.blit(img, img.get_rect(center=(W // 2, 250)))
        elif self.state == "finished":
            img = chrome("KLAAR!" if self.mode == "crush" else "TIJD OM!", 130, G_FIRE, o=6)
            s.blit(img, img.get_rect(center=(W // 2, 300)))
