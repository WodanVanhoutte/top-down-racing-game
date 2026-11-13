"""
td_race.py  -  het rijden zelf: auto's, drift-fysica, bots, punten, effecten en de HUD.
"""
import math
import random

import pygame

from td_core import (BOT_NAMES, CARS, CYAN, GREEN, H, J, JB, NEON, ORANGE, PINK, PURPLE, RED, TAU, W, WHITE, YELLOW,
                     car_params, chrome, clamp, dim, fmt_pts, fmt_time, glow, lerp, mix, panel, render, text, wrap_rad)
from td_track import HALF, LIFT, TILE, WALL

TURN_RATE = 3.3         # stuursnelheid (rad/s)
TURN_LOSS = 0.38        # minder wendbaar bij hoge snelheid
BRAKE = 720
NITRO_USE = 30
NITRO_REGEN = 5
KMH = 0.36              # px/s -> km/u op de teller


# ------------------------------------------------------------------ auto
class Car:
    def __init__(self, track, art, slot, model, stats, name, glow_col, is_player=False):
        idx = -6 - slot * 6                                  # startvak (zie Track._start_line)
        lat = 46 if slot % 2 else -46
        self.x, self.y = track.P(idx, lat, False)
        self.idx = idx % track.n
        self.progress = idx                                  # negatief: nog voor de startlijn
        self.heading = track.headings[self.idx]
        self.vx = self.vy = 0.0
        p = car_params(stats)
        self.vmax, self.accel, self.drift_stat = p["vmax"], p["accel"], p["drift"]
        self.nitro_cap = p["nitro"]
        self.nitro = self.nitro_cap * 0.6
        self.name, self.is_player, self.glow_col = name, is_player, glow_col
        self.sprite = art.spr[model]
        self.color = art.col[model]
        self.shadow = pygame.mask.from_surface(self.sprite).to_surface(setcolor=(0, 0, 0, 110), unsetcolor=(0, 0, 0, 0))
        self.boosting = self.braking = False
        self.lat = lat
        self.z = 0.0
        self.upper = False                                   # rijdt op een verhoogd stuk (tekenlaag)
        self.slip = 0.0                                      # zijwaartse snelheid
        self.ang = 0.0                                       # slijphoek (rad)
        self.laps = 0
        self.lap_times = []
        self.last_lap_t = 0.0
        self.finished = False
        self.finish_time = None
        self.trail = []                                      # lichtsporen van de achterlichten
        self.wheels = None                                   # vorige plek van de achterwielen (remsporen)
        self.stuck = 0.0
        self.throttle = False

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def physics(self, dt, throttle, brake, steer, hand=False, boost=False, grip_mult=1.0):
        """Drift-fysica: de auto heeft een voorwaartse en een zijwaartse snelheid.
        Hoe lager de 'grip', hoe trager de zijwaartse snelheid verdwijnt -> de auto glijdt."""
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        vf = self.vx * fx + self.vy * fy
        turn = TURN_RATE * (0.94 + self.drift_stat * 0.012) * (1 - TURN_LOSS * min(1, abs(vf) / self.vmax))
        self.heading += steer * turn * clamp(vf / 140, -1, 1) * dt * (1.35 if hand else 1.0)

        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        vf = self.vx * fx + self.vy * fy
        vl = self.vx * rx + self.vy * ry

        boosting = bool(boost and throttle and self.nitro > 0)
        if boosting:
            self.nitro = max(0.0, self.nitro - NITRO_USE * dt)
        else:
            self.nitro = min(self.nitro_cap, self.nitro + NITRO_REGEN * dt)
        self.boosting = boosting
        accel = self.accel * (1.75 if boosting else 1.0)
        vmax = self.vmax * (1.22 if boosting else 1.0)
        if throttle:
            vf += accel * dt
        self.braking = bool(brake and vf > 20)
        if brake:
            vf -= (BRAKE if vf > 20 else accel * 0.5) * dt
        vf -= vf * (accel / vmax) * dt
        if not throttle and not brake:
            vf -= math.copysign(min(abs(vf), 90 * dt), vf)
        if hand:
            vf -= vf * 0.3 * dt
        vf = max(vf, -self.vmax * 0.3)

        grip = (7.9 - self.drift_stat * 0.16) * grip_mult             # glad asfalt: de auto breekt makkelijk uit
        if throttle:
            grip *= 1 - (0.30 + 0.008 * self.drift_stat) * abs(steer) * min(1.0, abs(vf) / 260)   # gas + sturen: de achterkant komt los
        else:
            grip *= 1.35                                              # gas los: de grip komt terug
        if hand:
            grip = 3.2 * grip_mult
        vl0 = vl
        vl *= math.exp(-grip * dt)
        m1, m2 = math.hypot(vf, vl0), math.hypot(vf, vl)              # een slip houdt snelheid vast (powerslide)
        mt = m2 + (m1 - m2) * (0.55 + self.drift_stat * 0.016)
        vf = math.copysign(math.sqrt(max(0.0, mt * mt - vl * vl)), vf if vf else 1.0)

        self.vx = fx * vf + rx * vl
        self.vy = fy * vf + ry * vl
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.slip = abs(vl)
        self.throttle = throttle
        sp = math.hypot(self.vx, self.vy)
        self.ang = abs(wrap_rad(math.atan2(self.vy, self.vx) - self.heading)) if sp > 120 else 0.0

    def follow_track(self, track):
        """Zoekt het dichtste punt van de middenlijn en botst tegen de vangrail.
        Geeft de botssterkte terug (0 = geen botsing)."""
        n = track.n
        best, best_off = 1e18, 0
        for off in range(-25, 26):
            px, py = track.pts[(self.idx + off) % n]
            d = (px - self.x) ** 2 + (py - self.y) ** 2
            if d < best:
                best, best_off = d, off
        self.idx = (self.idx + best_off) % n
        self.progress += best_off
        px, py = track.pts[self.idx]
        nx, ny = track.normals[self.idx]
        lat = (self.x - px) * nx + (self.y - py) * ny
        hit = 0.0
        if abs(lat) > WALL:
            side = 1 if lat > 0 else -1
            self.x -= nx * (lat - side * WALL)
            self.y -= ny * (lat - side * WALL)
            vn = (self.vx * nx + self.vy * ny) * side
            if vn > 0:
                hit = vn
                self.vx -= nx * side * vn * 1.4
                self.vy -= ny * side * vn * 1.4
                k = 1 - min(0.4, vn / 800)
                self.vx *= k
                self.vy *= k
            lat = side * WALL
        self.lat = lat
        self.z = track.z[self.idx]
        self.upper = track.zmax[self.idx] > 0
        return hit

    def respawn(self, track):
        self.x, self.y = track.pts[self.idx]
        self.heading = track.headings[self.idx]
        self.vx = self.vy = 0.0
        self.trail.clear()
        self.wheels = None


def collide(a, b):
    """Botsing tussen twee auto's (alleen als ze op dezelfde hoogte rijden)."""
    if abs(a.z - b.z) > 0.35:
        return 0.0
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy)
    if d >= 36 or d < 0.01:
        return 0.0
    nx, ny = dx / d, dy / d
    push = (36 - d) / 2
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


class Bot:
    """Bestuurt een auto: stuurt naar een punt verderop en remt voor bochten."""

    def __init__(self, car, skill):
        self.car, self.skill = car, skill
        self.lane = random.uniform(-45, 45)
        self.t = random.uniform(0, 10)

    def drive(self, track, dt, lead):
        c = self.car
        n = track.n
        self.t += dt
        v = c.speed
        look = int(7 + v / 36)
        lane = self.lane + math.sin(self.t * 0.4) * 18
        tx, ty = track.P(c.idx + look, lane, False)
        diff = wrap_rad(math.atan2(ty - c.y, tx - c.x) - c.heading)
        steer = clamp(diff * 2.8, -1, 1)
        vt = c.vmax * 1.3
        kmax = 0.0
        for d in range(2, 52, 3):
            k = abs(track.curv[(c.idx + d) % n])
            kmax = max(kmax, k)
            if k > 1e-5:
                vt = min(vt, math.sqrt(360 * self.skill / k) + d * 4.2)
        vt *= 1 + clamp(lead, -0.08, 0.10)                    # elastiek: achterstand = iets sneller
        boost = kmax < 1 / 1500 and c.nitro > 25 and abs(diff) < 0.2
        c.physics(dt, v < vt, v > vt + 40, steer, False, boost)


# ------------------------------------------------------------------ de race
MODES = {"drift": ("ドリフトアタック", "DRIFT ATTACK"), "race": ("ストリートレース", "STREET RACE")}
RANKS = [(0, "ドリフト", "DRIFT"), (1500, "いいね!", "NICE!"), (5000, "すごい!", "SUGOI!"), (12000, "最高!!", "SAIKOU!!"),
         (25000, "神ドリフト!!", "KAMI DRIFT!!")]


def medal_for(score, track, laps):
    """Medaille in Drift Attack: hangt af van de lengte van het circuit en het aantal ronden."""
    base = track.n * laps
    for k, (name, col, f) in enumerate((("金 GOLD", (255, 215, 80), 34), ("銀 SILVER", (210, 220, 235), 19), ("銅 BRONZE", (225, 140, 80), 9))):
        if score >= base * f:
            return name, col, base * f
    return None, (150, 150, 170), base * 9


class Race:
    def __init__(self, app, track, mode, laps, nbots, rain):
        self.app, self.t, self.mode, self.laps, self.rain = app, track, mode, laps, rain
        self.sfx = app.sfx
        save = app.save
        me = CARS[save["car"]]
        nb = nbots if mode == "race" else 0
        self.player = Car(track, app.art, nb, me[0], me[3], "YOU", NEON[save["glow"]], True)
        self.cars, self.bots = [self.player], []
        others = [c for k, c in enumerate(CARS) if k != save["car"]]
        random.shuffle(others)
        names = random.sample(BOT_NAMES, len(BOT_NAMES))
        for k in range(nb):
            oc = others[k % len(others)]
            car = Car(track, app.art, k, oc[0], oc[3], names[k], random.choice(NEON))
            self.cars.append(car)
            self.bots.append(Bot(car, 0.90 + 0.05 * (nb - k) / nb + 0.04 * track.spec["diff"] / 3))
        self.clock = -3.6                                     # < 0: aftellen
        self.count_shown = 4
        self.done = False
        self.done_t = 0.0
        self.cam = [self.player.x - W / 2, self.player.y - H / 2]
        self.cam_prev = list(self.cam)
        self.shake = 0.0
        self.flash = 0.0                                      # witte flits
        self.red = 0.0                                        # rode rand na een botsing
        # drift-punten
        self.score = 0
        self.chain = 0.0
        self.drift_t = 0.0
        self.gap = 9.0
        self.flicks = 0
        self.dir = 0
        self.best_chain = 0
        self.clips = 0
        self.clip_done = set()
        self.pop = []                                         # zwevende meldingen: [tekst, kleur, leeftijd, groot]
        self.banner = None                                    # [jp, lat, kleur, leeftijd]
        self.was_up = False
        self.was_full = False
        # effecten (laag 0 = straat, laag 1 = verhoogd)
        self.smoke = ([], [])
        self.sparks = ([], [])
        self.flames = ([], [])
        self.ghosts = ([], [])
        self.ghost_t = 0.0
        self.backfire_t = 0.0
        self.lines = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.5, 1.0)] for _ in range(46)]
        self.petals = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0, TAU), random.uniform(0.6, 1.3)] for _ in range(34)]
        self.drops = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.7, 1.3)] for _ in range(150)] if rain else []
        self.ripples = []
        self.time_fx = 0.0
        self.smoke_img = []
        for s in (18, 26, 36, 48, 62, 78):
            img = pygame.Surface((s, s), pygame.SRCALPHA)
            for r in range(s // 2, 0, -1):
                pygame.draw.circle(img, (214, 218, 236, int(150 * (1 - r / (s / 2)) ** 0.8)), (s // 2, s // 2), r)
            self.smoke_img.append(img)
        self.mini, self.mk, self.mox, self.moy = track.minimap((230, 150))
        self.sfx.start_loops()

    # ------------------------------------------------------------ logica
    def pop_up(self, jp, lat, color, big=False):
        self.pop.append([J(jp, lat), color, 0.0, big])
        if len(self.pop) > 4:
            self.pop.pop(0)

    @property
    def mult(self):
        return min(8, 1 + int(self.drift_t / 2.0) + self.flicks)

    def bank(self):
        """De lopende drift-keten wordt bij de score geteld (en vult de nitro bij)."""
        pts = int(self.chain)
        if pts <= 0:
            return
        self.score += pts
        self.best_chain = max(self.best_chain, pts)
        rank = [r for r in RANKS if pts >= r[0]][-1]
        self.pop_up(f"{rank[1]}  +{fmt_pts(pts)}", f"{rank[2]}  +{fmt_pts(pts)}", (YELLOW, GREEN, CYAN, PINK, WHITE)[RANKS.index(rank)], True)
        self.player.nitro = min(self.player.nitro_cap, self.player.nitro + pts / 110)
        self.sfx.play("bank", 0.7)
        if pts >= 5000:
            self.flash = 0.35
        self.chain, self.drift_t, self.flicks, self.dir = 0.0, 0.0, 0, 0

    def update_drift(self, dt, hit):
        p, t = self.player, self.t
        sp = p.speed
        drifting = 0.2 < p.ang < 2.3 and sp > 170
        if hit > 110:
            if self.chain > 300:
                self.pop_up(f"失敗  CRASH -{fmt_pts(self.chain)}", f"CRASH  -{fmt_pts(self.chain)}", RED, True)
                self.sfx.play("fail", 0.7)
            self.chain, self.drift_t, self.flicks, self.dir = 0.0, 0.0, 0, 0
            return
        if drifting:
            zi = t.zone_at[p.idx]
            near = abs(p.lat) > WALL - 34                    # vlak langs de vangrail = meer punten
            rate = sp * p.ang * 1.0 * (2.0 if zi >= 0 else 1.0) * (1.5 if near else 1.0)
            self.chain += rate * dt * self.mult
            self.drift_t += dt
            self.gap = 0.0
            fx, fy = math.cos(p.heading), math.sin(p.heading)
            d = 1 if (p.vx * -fy + p.vy * fx) > 0 else -1
            if p.ang > 0.32 and d != self.dir:
                if self.dir != 0:
                    self.flicks += 1
                    self.pop_up("切り返し!  FLICK", "FLICK!", CYAN)
                self.dir = d
            if zi >= 0 and zi not in self.clip_done:         # clipping point in de binnenbocht
                cx, cy = t.zones[zi]["clip"]
                if (p.x - cx) ** 2 + (p.y - cy) ** 2 < 58 ** 2:
                    self.clip_done.add(zi)
                    self.clips += 1
                    self.chain += 400 * self.mult
                    self.pop_up(f"クリップ!  CLIP +{400 * self.mult}", f"CLIP! +{400 * self.mult}", YELLOW)
                    self.sfx.play("clip", 0.7)
        else:
            self.gap += dt
            if self.gap > 1.0:
                self.bank()

    def update(self, dt, keys):
        t, p = self.t, self.player
        self.time_fx += dt
        self.clock += dt
        racing = self.clock >= 0
        if not racing:                                        # aftellen: 3, 2, 1
            k = int(math.ceil(-self.clock))
            if k < self.count_shown and k <= 3:
                self.count_shown = k
                self.sfx.play("beep")
        elif self.count_shown > 0:
            self.count_shown = 0
            self.sfx.play("go")
        grip = 0.84 if self.rain else 1.0

        # ---- speler
        thr = brk = hand = boost = False
        steer = 0.0
        if racing and not p.finished:
            thr = keys[pygame.K_UP] or keys[pygame.K_w]
            brk = keys[pygame.K_DOWN] or keys[pygame.K_s]
            steer = (1.0 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0.0) - (1.0 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0.0)
            hand = keys[pygame.K_SPACE]
            boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        was_boost, was_thr = p.boosting, p.throttle
        if p.finished:                                        # na de finish rijdt de auto zelf uit
            self.auto.drive(t, dt, -0.3)
        else:
            p.physics(dt, thr, brk, steer, hand, boost, grip)
        if p.boosting and not was_boost:
            self.sfx.play("boost", 0.5)
            self.shake = max(self.shake, 7)
        if was_boost and not p.boosting:                      # nitro op of losgelaten: afblaasventiel
            self.sfx.play("blowoff", 0.4)
        if was_thr and not p.throttle and p.speed > p.vmax * 0.6 and self.backfire_t <= 0:   # gas los: knal uit de uitlaat
            self.backfire_t = 0.5
            self.sfx.play("pop", 0.6)
            self.exhaust(p, 5, ORANGE)
        self.backfire_t -= dt
        hit = p.follow_track(t)
        if hit > 60:
            self.wall_fx(p, hit)
        for b in self.bots:
            c = b.car
            if racing:
                lead = (p.progress - c.progress) / 900 if not c.finished else -0.3
                b.drive(t, dt, lead)
                c.stuck = c.stuck + dt if c.speed < 25 else 0.0
                if c.stuck > 2.0:
                    c.respawn(t)
                    c.stuck = 0.0
            h = c.follow_track(t)
            if h > 120 and self.on_screen(c):
                self.wall_fx(c, h, quiet=True)
        for i, a in enumerate(self.cars):
            for b in self.cars[i + 1:]:
                h = collide(a, b)
                if h > 80:
                    self.spark_burst((a.x + b.x) / 2, (a.y + b.y) / 2 - a.z * LIFT, 8, a.upper)
                    if a.is_player or b.is_player:
                        self.sfx.play("bump", min(1.0, h / 300))
                        self.shake = max(self.shake, min(9, h / 40))

        if racing and not p.finished:
            self.update_drift(dt, hit)

        # ---- ronden en finish
        for c in self.cars:
            if racing and not c.finished and c.progress >= (c.laps + 1) * t.n:
                c.laps += 1
                c.lap_times.append(self.clock - c.last_lap_t)
                c.last_lap_t = self.clock
                if c.is_player:
                    self.clip_done.clear()
                    self.flash = 0.3
                if c.laps >= self.laps:
                    c.finished = True
                    c.finish_time = self.clock
                    if c.is_player:
                        self.bank()
                        self.done = True
                        self.auto = Bot(p, 0.8)
                        self.sfx.play("finish")
                        self.pop_up("フィニッシュ!", "FINISH!", YELLOW, True)
                elif c.is_player:
                    self.sfx.play("lap")
                    if c.laps == self.laps - 1:
                        self.banner = ["ファイナルラップ", "LAATSTE RONDE", PINK, 0.0]
                    else:
                        self.banner = [f"ラップ {c.laps + 1}", f"RONDE {c.laps + 1} / {self.laps}", CYAN, 0.0]
        if self.done:
            self.done_t += dt

        # ---- op- en afritten melden
        if p.z > 0 and not self.was_up:
            self.banner = ["▲ 高速入口", "OPRIT  -  OMHOOG", GREEN, 0.0]
        if p.z >= 1 and not self.was_full:
            self.was_full = True
        if self.was_full and p.z < 1:
            self.was_full = False
            self.banner = ["▼ 出口", "AFRIT  -  OMLAAG", YELLOW, 0.0]
        self.was_up = p.z > 0
        if self.banner:
            self.banner[3] += dt
            if self.banner[3] > 2.4:
                self.banner = None

        self.update_fx(dt)
        self.update_camera(dt)

        # ---- geluid
        sp = p.speed
        gear, frac = self.gear(sp)
        near = sum(1 for b in self.bots if (b.car.x - p.x) ** 2 + (b.car.y - p.y) ** 2 < 500 ** 2)
        self.sfx.loops(rpm=0.15 + 0.85 * frac if sp > 8 or thr else 0.0, power=1.0 if thr else 0.25, boosting=p.boosting,
                       skid=clamp((p.slip - 60) / 220, 0, 1), bots=min(1.0, near / 2), rain=1.0 if self.rain else 0.0)

    def gear(self, sp):
        g = int(clamp(sp / (self.player.vmax * 1.05) * 5, 0, 4.999))
        lo, hi = g * self.player.vmax * 1.05 / 5, (g + 1) * self.player.vmax * 1.05 / 5
        return g + 1, clamp((sp - lo) / (hi - lo), 0, 1) * 0.75 + 0.25 * (g / 4)

    def on_screen(self, c, m=120):
        return -m < c.x - self.cam[0] < W + m and -m < c.y - self.cam[1] < H + m

    def standings(self):
        return sorted(self.cars, key=lambda c: (c.finish_time if c.finished else 1e9, -c.progress))

    def position(self):
        return self.standings().index(self.player) + 1

    # ------------------------------------------------------------ effecten
    def spark_burst(self, x, y, count, upper, color=None):
        lst = self.sparks[1 if upper else 0]
        for _ in range(count):
            a, v = random.uniform(0, TAU), random.uniform(80, 420)
            lst.append([x, y, math.cos(a) * v, math.sin(a) * v, 0.0, random.uniform(0.2, 0.55), color or random.choice([YELLOW, ORANGE, WHITE])])

    def wall_fx(self, c, hit, quiet=False):
        self.spark_burst(c.x, c.y - c.z * LIFT, int(clamp(hit / 14, 5, 26)), c.upper)
        if not quiet:
            self.sfx.play("hit", min(1.0, hit / 320))
            self.shake = max(self.shake, min(16, hit / 22))
            self.red = min(1.0, hit / 300)

    def exhaust(self, c, count, color):
        fx, fy = math.cos(c.heading), math.sin(c.heading)
        lst = self.flames[1 if c.upper else 0]
        for _ in range(count):
            v = random.uniform(40, 200)
            lst.append([c.x - fx * 30 + random.uniform(-4, 4), c.y - c.z * LIFT - fy * 30 + random.uniform(-4, 4),
                        c.vx * 0.6 - fx * v, c.vy * 0.6 - fy * v, 0.0, random.uniform(0.12, 0.3), color])

    def mark(self, c, a, b):
        """Remspoor van punt a naar punt b: op de grond of op het verhoogde wegdek."""
        col = (9, 9, 14)
        if not self.t.up[c.idx]:
            pygame.draw.line(self.t.world, col, a, b, 5)
            return
        lift = c.z * LIFT
        a, b = (a[0], a[1] - lift), (b[0], b[1] - lift)
        for tx in {int(a[0] // TILE), int(b[0] // TILE)}:
            for ty in {int(a[1] // TILE), int(b[1] // TILE)}:
                tile = self.t.tiles.get((tx, ty))
                if tile:
                    pygame.draw.line(tile, (*col, 255), (a[0] - tx * TILE, a[1] - ty * TILE), (b[0] - tx * TILE, b[1] - ty * TILE), 5)

    def update_fx(self, dt):
        self.shake = max(0.0, self.shake - 34 * dt)
        self.flash = max(0.0, self.flash - dt)
        self.red = max(0.0, self.red - 1.6 * dt)
        for c in self.cars:
            sp = c.speed
            fx, fy = math.cos(c.heading), math.sin(c.heading)
            rx, ry = -fy, fx
            L = 1 if c.upper else 0
            vis = self.on_screen(c)
            sliding = c.slip > 95 and sp > 120
            # remsporen
            wl = (c.x - fx * 20 + rx * 11, c.y - fy * 20 + ry * 11)
            wr = (c.x - fx * 20 - rx * 11, c.y - fy * 20 - ry * 11)
            if sliding and c.wheels:
                self.mark(c, c.wheels[0], wl)
                self.mark(c, c.wheels[1], wr)
            c.wheels = (wl, wr) if sliding else None
            if not vis:
                c.trail.clear()
                continue
            lift = c.z * LIFT
            if sliding and len(self.smoke[L]) < 220:          # bandenrook (gekleurd door de neon onder de auto)
                for w in (wl, wr):
                    if random.random() < 0.75:
                        self.smoke[L].append([w[0], w[1] - lift, c.vx * 0.22 + random.uniform(-26, 26), c.vy * 0.22 + random.uniform(-26, 26),
                                              0.0, random.uniform(0.6, 1.15), random.uniform(0.8, 1.4)])
            if c.boosting:                                    # nitro-vlammen + nabeelden
                self.exhaust(c, 3, CYAN if random.random() < 0.6 else PURPLE)
            if self.rain and sp > 150 and random.random() < 0.5:   # opspattend water
                self.sparks[L].append([c.x - fx * 26, c.y - lift - fy * 26, -fx * 60 + random.uniform(-70, 70),
                                       -fy * 60 + random.uniform(-70, 70), 0.0, 0.3, (150, 190, 230)])
            if sp > 200:                                      # lichtsporen van de achterlichten
                c.trail.append((c.x - fx * 27 + rx * 9, c.y - lift - fy * 27 + ry * 9, c.x - fx * 27 - rx * 9, c.y - lift - fy * 27 - ry * 9, L))
                if len(c.trail) > 16:
                    c.trail.pop(0)
            elif c.trail:
                c.trail.pop(0)
        p = self.player
        self.ghost_t -= dt
        if p.boosting and self.ghost_t <= 0:
            self.ghost_t = 0.045
            img = pygame.transform.rotozoom(p.sprite, -math.degrees(p.heading), 1 + 0.1 * p.z)
            img.fill((90, 190, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.ghosts[1 if p.upper else 0].append([img, p.x, p.y - p.z * LIFT, 0.0])
        for L in (0, 1):
            for s in self.smoke[L]:
                s[0] += s[2] * dt
                s[1] += s[3] * dt
                s[2] *= 1 - 1.5 * dt
                s[3] *= 1 - 1.5 * dt
                s[4] += dt
            self.smoke[L][:] = [s for s in self.smoke[L] if s[4] < s[5]]
            for lst in (self.sparks[L], self.flames[L]):
                for s in lst:
                    s[0] += s[2] * dt
                    s[1] += s[3] * dt
                    s[2] *= 1 - 3 * dt
                    s[3] *= 1 - 3 * dt
                    s[4] += dt
                lst[:] = [s for s in lst if s[4] < s[5]]
            for g in self.ghosts[L]:
                g[3] += dt
            self.ghosts[L][:] = [g for g in self.ghosts[L] if g[3] < 0.3]
        for q in self.pop:
            q[2] += dt
        self.pop[:] = [q for q in self.pop if q[2] < 1.7]
        if self.rain:
            if random.random() < 0.7:
                self.ripples.append([self.cam[0] + random.uniform(0, W), self.cam[1] + random.uniform(0, H), 0.0])
            for r in self.ripples:
                r[2] += dt
            self.ripples[:] = [r for r in self.ripples if r[2] < 0.5]

    def update_camera(self, dt):
        p = self.player
        tx = p.x + p.vx * 0.30 - W / 2
        ty = p.y - p.z * LIFT + p.vy * 0.30 - H / 2
        k = 1 - math.exp(-5.5 * dt)
        self.cam_prev = list(self.cam)
        self.cam[0] = clamp(lerp(self.cam[0], tx, k), 0, self.t.w - W)
        self.cam[1] = clamp(lerp(self.cam[1], ty, k), 0, self.t.h - H)

    # ------------------------------------------------------------ tekenen
    def draw_layer(self, s, L, cx, cy):
        A = self.app.assets
        for c in self.cars:                                   # lichtsporen
            n = len(c.trail)
            for k in range(1, n):
                a, b = c.trail[k - 1], c.trail[k]
                if b[4] != L:
                    continue
                f = k / n
                col = (int(60 + 195 * f), int(20 + 180 * f), 255) if c.boosting else (int(230 * f), int(24 * f), int(40 * f))
                wd = 4 if c.boosting else 3
                pygame.draw.line(s, col, (a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy), wd)
                pygame.draw.line(s, col, (a[2] - cx, a[3] - cy), (b[2] - cx, b[3] - cy), wd)
        for img, x, y, age in self.ghosts[L]:                 # nitro-nabeelden
            img.set_alpha(int(150 * (1 - age / 0.3)))
            s.blit(img, img.get_rect(center=(x - cx, y - cy)))
        for c in self.cars:
            if c.upper == bool(L) and self.on_screen(c):
                self.draw_car(s, c, cx, cy)
        for x, y, vx, vy, age, life, size in self.smoke[L]:   # rook
            f = age / life
            img = self.smoke_img[min(5, int((0.8 + f * 4.4) * size))]
            img.set_alpha(int(150 * (1 - f) ** 1.3))
            s.blit(img, (x - cx - img.get_width() / 2, y - cy - img.get_height() / 2))
        for x, y, vx, vy, age, life, col in self.flames[L]:   # vlammen (additief = gloeien)
            f = 1 - age / life
            g = glow(int(16 + 30 * f) // 4 * 4 + 12, dim(col, 0.9))
            s.blit(g, (x - cx - g.get_width() / 2, y - cy - g.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
        for x, y, vx, vy, age, life, col in self.sparks[L]:   # vonken
            f = 1 - age / life
            pygame.draw.line(s, dim(col, 0.4 + 0.6 * f), (x - cx, y - cy), (x - cx - vx * 0.035, y - cy - vy * 0.035), 2)

    def draw_car(self, s, c, cx, cy, ghost=False):
        A = self.app.assets
        ox, oy = c.x - cx, c.y - c.z * LIFT - cy
        deg = -math.degrees(c.heading)
        fx, fy = math.cos(c.heading), math.sin(c.heading)
        rx, ry = -fy, fx
        if ghost:                                             # doorschijnend silhouet onder een brug
            sp = pygame.transform.rotozoom(c.sprite, deg, 1.0)
            sp.set_alpha(90)
            s.blit(sp, sp.get_rect(center=(ox, oy)))
            pygame.draw.circle(s, c.glow_col, (ox, oy), 40, 2)
            return
        g = glow(150, dim(c.glow_col, 0.5 + 0.05 * int(2 + 2 * math.sin(self.time_fx * 6))), 1.5)   # neon onder de auto (pulseert)
        s.blit(g, (ox - 75, oy - 75), special_flags=pygame.BLEND_RGB_ADD)
        cone = pygame.transform.rotate(A["cone"], deg)                                    # koplampen
        s.blit(cone, cone.get_rect(center=(ox + fx * 16, oy + fy * 16)), special_flags=pygame.BLEND_RGB_ADD)
        scale = 1 + 0.1 * c.z
        sh = pygame.transform.rotozoom(c.shadow, deg, scale)
        s.blit(sh, sh.get_rect(center=(ox + 6, oy + 8)))
        sp = pygame.transform.rotozoom(c.sprite, deg, scale)
        s.blit(sp, sp.get_rect(center=(ox, oy)))
        tail = A["red"] if c.braking else A["red_dim"]                                    # achterlichten / remlichten
        for sd in (-1, 1):
            s.blit(tail, tail.get_rect(center=(ox - fx * 27 + rx * sd * 9, oy - fy * 27 + ry * sd * 9)), special_flags=pygame.BLEND_RGB_ADD)
        if c.boosting:
            b = A["blue"]
            s.blit(b, b.get_rect(center=(ox - fx * 36, oy - fy * 36)), special_flags=pygame.BLEND_RGB_ADD)
        if c.is_player and len(self.cars) > 1:
            text(s, "1P", 13, (ox, oy - 44 + 3 * math.sin(self.time_fx * 5)), YELLOW, "center", True, True)
            pygame.draw.polygon(s, YELLOW, [(ox - 5, oy - 34), (ox + 5, oy - 34), (ox, oy - 27)])

    def draw(self, s):
        t, p, A = self.t, self.player, self.app.assets
        sx = random.uniform(-1, 1) * self.shake
        sy = random.uniform(-1, 1) * self.shake
        cx = int(clamp(self.cam[0] + sx, 0, t.w - W))
        cy = int(clamp(self.cam[1] + sy, 0, t.h - H))
        s.blit(t.world, (0, 0), (cx, cy, W, H))
        for x, y, age in self.ripples:                         # regenkringen op de grond
            r = 3 + age * 22
            pygame.draw.ellipse(s, (70, 84, 120), (x - cx - r, y - cy - r * 0.6, 2 * r, 1.2 * r), 1)
        tf = self.time_fx
        for on, off, x, y, col, ph in t.live:                  # flikkerende reclameborden
            if -260 < x - cx < W + 20 and -160 < y - cy < H + 20:
                lit = not (math.sin(tf * 1.3 + ph) > 0.93 and int(tf * 17 + ph) % 3 == 0)
                s.blit(on if lit else off, (x - cx, y - cy))
                if lit:
                    v = 0.16 + 0.07 * math.sin(tf * 3 + ph)
                    g = glow(260, (int(col[0] * 0.25), int(col[1] * 0.25), int(col[2] * 0.25)), 1.6)
                    if int(tf * 2 + ph) % 2 or v > 0.18:
                        s.blit(g, (x - cx + on.get_width() / 2 - 130, y - cy + on.get_height() / 2 - 130), special_flags=pygame.BLEND_RGB_ADD)
        self.draw_layer(s, 0, cx, cy)
        for ty in range(cy // TILE, (cy + H) // TILE + 1):     # verhoogde wegen (boven de auto's op straat)
            for tx in range(cx // TILE, (cx + W) // TILE + 1):
                tile = t.tiles.get((tx, ty))
                if tile:
                    s.blit(tile, (tx * TILE - cx, ty * TILE - cy))
        if not p.upper and t.under(p.x, p.y):
            self.draw_car(s, p, cx, cy, ghost=True)
        self.draw_layer(s, 1, cx, cy)
        for img, x, y in t.overs:                              # poorten en borden boven de weg
            if -img.get_width() < x - cx < W and -img.get_height() < y - cy < H:
                s.blit(img, (x - cx, y - cy))
        self.draw_screen_fx(s)
        self.draw_hud(s)

    def draw_screen_fx(self, s):
        p, A = self.player, self.app.assets
        dx, dy = self.cam[0] - self.cam_prev[0], self.cam[1] - self.cam_prev[1]
        tf = self.time_fx
        if self.rain:                                          # regen
            for d in self.drops:
                d[0] = (d[0] - dx * 1.2 - 5 * d[2]) % W
                d[1] = (d[1] - dy * 1.2 + 19 * d[2]) % H
                pygame.draw.line(s, (120, 140, 180), (d[0], d[1]), (d[0] - 4 * d[2], d[1] + 15 * d[2]), 1)
        else:                                                  # kersenbloesem die door het beeld waait
            for q in self.petals:
                q[2] += 0.05
                q[0] = (q[0] - dx * 1.15 - 0.9 * q[3] + math.sin(q[2]) * 0.6) % W
                q[1] = (q[1] - dy * 1.15 + 0.7 * q[3]) % H
                a = q[2]
                pygame.draw.line(s, (255, 190, 215), (q[0], q[1]), (q[0] + math.cos(a) * 5, q[1] + math.sin(a) * 3), 3)
        sp = p.speed
        v = clamp((sp - p.vmax * 0.78) / (p.vmax * 0.35), 0, 1)
        if p.boosting:
            v = max(v, 0.9)
        if v > 0.02 and sp > 1:                                # snelheidsstrepen
            ux, uy = p.vx / sp, p.vy / sp
            col = mix((70, 90, 130), (150, 230, 255) if p.boosting else (200, 210, 230), v)
            for q in self.lines:
                q[0] = (q[0] - ux * sp * 0.05 * q[2]) % W
                q[1] = (q[1] - uy * sp * 0.05 * q[2]) % H
                ed = max(abs(q[0] - W / 2) / (W / 2), abs(q[1] - H / 2) / (H / 2))
                if ed > 0.45:
                    L = (18 + 110 * v) * q[2] * ed
                    pygame.draw.line(s, dim(col, ed), (q[0], q[1]), (q[0] - ux * L, q[1] - uy * L), 2 if q[2] > 0.8 else 1)
        if p.boosting:
            s.blit(A["edge_blue"], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.red > 0.05:
            A["edge_red"].set_alpha(int(255 * self.red))
            s.blit(A["edge_red"], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(A["vignette"], (0, 0))
        if self.flash > 0:
            A["white"].set_alpha(int(200 * self.flash))
            s.blit(A["white"], (0, 0))

    def draw_hud(self, s):
        p, t = self.player, self.t
        tf = self.time_fx
        # ---- linksboven: modus, ronde, tijd / positie
        panel(s, (16, 14, 250, 92), edge=CYAN)
        text(s, JB(*MODES[self.mode]), 14, (28, 20), PINK, bold=True)
        text(s, f"LAP {min(self.laps, p.laps + 1)}/{self.laps}", 26, (28, 40), WHITE, bold=True, italic=True)
        text(s, fmt_time(max(0.0, self.clock if not p.finished else p.finish_time)), 22, (28, 74), CYAN, bold=True)
        if self.mode == "race":
            pos = self.position()
            img = chrome(f"{pos}", 64, (255, 255, 180), (255, 200, 40), (200, 60, 0), (255, 240, 120))
            s.blit(img, (176, 12))
            text(s, f"/{len(self.cars)}", 20, (230, 62), WHITE, bold=True, italic=True)
        # ---- rechtsboven: score
        panel(s, (W - 286, 14, 270, 92), edge=PINK)
        text(s, JB("スコア", "SCORE"), 15, (W - 274, 20), CYAN, bold=True)
        s.blit(chrome(fmt_pts(self.score), 40, (255, 255, 255), (255, 170, 230), (180, 20, 120), (255, 220, 240), o=2), (W - 278, 36))
        if self.mode == "drift":
            name, col, need = medal_for(self.score, t, self.laps)
            text(s, (name or "---") + f"   →  {fmt_pts(need)}", 14, (W - 274, 86), col, bold=True)
        else:
            text(s, JB("ドリフト = ニトロ", "DRIFT VULT NITRO"), 14, (W - 274, 86), YELLOW, bold=True)
        # ---- midden boven: lopende drift
        if self.chain > 0:
            pulse = 1 + 0.06 * math.sin(tf * 18)
            col = (WHITE, CYAN, GREEN, YELLOW, ORANGE, PINK, PURPLE, RED)[self.mult - 1]
            img = chrome(fmt_pts(self.chain), int(54 * pulse), (255, 255, 255), col, dim(col, 0.45), (255, 255, 255))
            s.blit(img, img.get_rect(center=(W // 2 - 30, 62)))
            m = chrome(f"x{self.mult}", 40, (255, 255, 200), YELLOW, (220, 60, 0), (255, 240, 150), o=2)
            s.blit(m, (W // 2 + img.get_width() // 2 - 20, 36))
            wbar = int(200 * clamp(1 - self.gap / 1.0, 0, 1))  # zo lang blijft de keten nog leven
            pygame.draw.rect(s, (30, 20, 50), (W // 2 - 100, 100, 200, 6))
            pygame.draw.rect(s, col, (W // 2 - 100, 100, wbar, 6))
            if t.zone_at[p.idx] >= 0:
                text(s, JB("ドリフトゾーン", "DRIFT ZONE  x2"), 16, (W // 2, 112), PINK if int(tf * 6) % 2 else YELLOW, "midtop", True)
        elif t.zone_at[p.idx] >= 0 and self.clock > 0:
            text(s, JB("ドリフトゾーン", "DRIFT ZONE  x2"), 18, (W // 2, 40), PINK if int(tf * 6) % 2 else YELLOW, "midtop", True)
        y = 150
        for txt_, col, age, big in self.pop:                   # meldingen
            a = clamp(min(age * 8, (1.7 - age) * 3), 0, 1)
            img = render(txt_, 34 if big else 24, col, True, True)
            sh = render(txt_, 34 if big else 24, (0, 0, 0), True, True)
            if a < 1:
                img, sh = img.copy(), sh.copy()
                img.set_alpha(int(255 * a))
                sh.set_alpha(int(255 * a))
            r = img.get_rect(center=(W // 2 + (1 - min(1, age * 6)) * 160, y - age * 12))
            s.blit(sh, r.move(3, 3))
            s.blit(img, r)
            y += 44 if big else 32
        if self.banner:                                        # groot bericht (ronde, oprit, afrit)
            jp, lat, col, age = self.banner
            k = clamp(min(age * 5, (2.4 - age) * 4), 0, 1)
            bw = 440
            x = int(W / 2 - bw / 2 - (1 - k) * 700)
            panel(s, (x, H - 190, bw, 60), tint=(6, 50, 34) if col in (GREEN, YELLOW) else (30, 6, 40), alpha=215, edge=col)
            text(s, J(jp, lat), 26, (x + bw // 2, H - 186), col, "midtop", True)
            text(s, lat, 13, (x + bw // 2, H - 150), WHITE, "midtop", True)
        # ---- rechtsonder: snelheid, toeren, versnelling, nitro
        sp = p.speed
        th = t.headings[p.idx]
        if p.vx * math.cos(th) + p.vy * math.sin(th) < -80 and int(tf * 4) % 2 and not p.finished:
            text(s, JB("逆走!", "VERKEERDE RICHTING"), 34, (W // 2, H // 2 + 110), RED, "center", True, True)
        gear, frac = self.gear(sp)
        panel(s, (W - 306, H - 150, 290, 134), edge=CYAN)
        img = chrome(f"{int(sp * KMH):3d}", 66, (255, 255, 255), (150, 240, 255), (20, 80, 200), (220, 250, 255))
        s.blit(img, img.get_rect(bottomright=(W - 108, H - 54)))
        text(s, "km/h", 16, (W - 104, H - 86), CYAN, bold=True, italic=True)
        text(s, J("ギア", "GEAR"), 12, (W - 60, H - 142), WHITE, bold=True)
        s.blit(chrome("R" if (p.vx * math.cos(p.heading) + p.vy * math.sin(p.heading)) < -5 else str(gear), 44,
                      (255, 255, 200), YELLOW, (230, 80, 0), (255, 250, 180), o=2), (W - 66, H - 128))
        for k in range(20):                                    # toerenteller in blokjes
            on = k / 20 < frac
            col = (60, 255, 140) if k < 12 else (255, 220, 60) if k < 16 else (255, 60, 70)
            if frac > 0.93 and k >= 16 and int(tf * 20) % 2:
                col = WHITE
            hb = 8 + (k // 4) * 2
            pygame.draw.rect(s, col if on else dim(col, 0.18), (W - 296 + k * 13, H - 36 - hb, 10, hb))
        text(s, "N2O", 13, (W - 296, H - 30), CYAN, bold=True)
        pygame.draw.rect(s, (16, 24, 50), (W - 258, H - 28, 230, 9))
        nw = int(230 * p.nitro / p.nitro_cap)
        pygame.draw.rect(s, WHITE if p.boosting and int(tf * 24) % 2 else (CYAN if p.nitro > 15 else RED), (W - 258, H - 28, nw, 9))
        for k in range(1, 10):
            pygame.draw.line(s, (8, 6, 24), (W - 258 + k * 23, H - 28), (W - 258 + k * 23, H - 20), 2)
        # ---- linksonder: kaart + hoogtemeter
        panel(s, (16, H - 176, 262, 160), edge=PINK)
        s.blit(self.mini, (20, H - 172))
        for c in self.cars[::-1]:
            mx, my = 20 + self.mox + c.x * self.mk, H - 172 + self.moy + c.y * self.mk
            pygame.draw.circle(s, (0, 0, 0), (mx, my), 5 if c.is_player else 4)
            pygame.draw.circle(s, WHITE if c.is_player and int(tf * 6) % 2 else c.color if not c.is_player else YELLOW, (mx, my), 4 if c.is_player else 3)
        pygame.draw.rect(s, (16, 24, 50), (256, H - 150, 12, 110))
        hh = int(110 * p.z)
        pygame.draw.rect(s, mix(CYAN, PINK, p.z), (256, H - 40 - hh, 12, max(2, hh)))
        text(s, J("高", "H"), 13, (262, H - 168), PINK, "midtop", True)
        text(s, J("地", "G"), 13, (262, H - 38), CYAN, "midtop", True)
        # ---- aftellen
        if self.clock < 0.9:
            k = int(math.ceil(-self.clock))
            if 1 <= k <= 3:
                f = (-self.clock) % 1.0
                img = chrome(str(k), int(130 + 80 * f), (255, 255, 255), (255, 120, 200), (160, 0, 90), (255, 220, 240), o=5)
                s.blit(img, img.get_rect(center=(W // 2, 190)))
                text(s, J("三二一"[3 - k], "READY"), 34, (W // 2 + 120, 150), YELLOW, "center", True)
            elif k <= 0:
                img = chrome(J("発進!", "GO!"), 150, (255, 255, 200), (120, 255, 160), (0, 120, 60), (220, 255, 220), o=5)
                img.set_alpha(int(255 * clamp(1 - self.clock / 0.9, 0, 1)))
                s.blit(img, img.get_rect(center=(W // 2, 190)))
            else:
                text(s, t.spec["name"], 30, (W // 2, H // 2 - 60), WHITE, "center", True, True)
                img = chrome(J(t.spec["jp"], t.spec["name"]), 70, (255, 255, 255), (150, 240, 255), (20, 80, 200), (220, 250, 255))
                s.blit(img, img.get_rect(center=(W // 2, H // 2 - 130)))
