"""
Top-down racegame tegen een AI - gemaakt met pygame.

Installeren:   pip install pygame
Starten:       python racegame.py

Besturing:
    Pijltje omhoog / W   = gas
    Pijltje omlaag / S   = remmen / achteruit
    Pijltje links/rechts (of A/D) = sturen
    R = terug naar menu, ESC = afsluiten
"""
import math
import sys

import pygame

# ----------------------------------------------------------------- instellingen
W, H = 1200, 800
CX, CY = W // 2, H // 2

# Het circuit bestaat uit twee ellipsen: buitenrand en binnenrand
OUT_A, OUT_B = 540, 340
IN_A, IN_B = 300, 130
MID_A, MID_B = (OUT_A + IN_A) / 2, (OUT_B + IN_B) / 2   # ideale racelijn

LAPS = 5
N_WP = 120            # aantal waypoints voor de AI
TAU = 2 * math.pi

GRASS = (40, 140, 60)
ASPHALT = (80, 80, 88)

DIFFICULTY = {          # naam: (max snelheid AI, lookahead)
    1: ("Makkelijk", 250, 7),
    2: ("Normaal", 285, 6),
    3: ("Moeilijk", 315, 6),
}


# ----------------------------------------------------------------- hulpfuncties
def on_track(x, y):
    dx, dy = x - CX, y - CY
    binnen_buiten = (dx / OUT_A) ** 2 + (dy / OUT_B) ** 2 <= 1
    buiten_binnen = (dx / IN_A) ** 2 + (dy / IN_B) ** 2 >= 1
    return binnen_buiten and buiten_binnen


def wrap_deg(a):
    return (a + 180) % 360 - 180


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def build_track():
    """Tekent het circuit eenmalig op een surface."""
    s = pygame.Surface((W, H))
    s.fill(GRASS)
    outer = pygame.Rect(CX - OUT_A, CY - OUT_B, OUT_A * 2, OUT_B * 2)
    inner = pygame.Rect(CX - IN_A, CY - IN_B, IN_A * 2, IN_B * 2)
    pygame.draw.ellipse(s, ASPHALT, outer)
    pygame.draw.ellipse(s, GRASS, inner)
    pygame.draw.ellipse(s, (240, 240, 240), outer, 6)
    pygame.draw.ellipse(s, (240, 240, 240), inner, 6)

    # onderbroken middenlijn
    for i in range(0, 200, 2):
        t1, t2 = TAU * i / 200, TAU * (i + 1) / 200
        p1 = (CX + MID_A * math.cos(t1), CY + MID_B * math.sin(t1))
        p2 = (CX + MID_A * math.cos(t2), CY + MID_B * math.sin(t2))
        pygame.draw.line(s, (200, 200, 120), p1, p2, 2)

    # start/finish lijn (geblokt) bovenaan in het midden
    top, bottom = CY - OUT_B + 6, CY - IN_B - 6
    size = 10
    for row, y in enumerate(range(top, bottom, size)):
        for col in range(2):
            kleur = (255, 255, 255) if (row + col) % 2 == 0 else (0, 0, 0)
            pygame.draw.rect(s, kleur, (CX - size + col * size, y, size, size))
    return s


# ----------------------------------------------------------------- auto
class Car:
    def __init__(self, x, y, color, max_speed, accel=220):
        self.x, self.y = x, y
        self.angle = 0.0          # graden, 0 = naar rechts, positief = rechtsom
        self.speed = 0.0
        self.max_speed = max_speed
        self.accel = accel
        self.color = color

        # voortgang rond het circuit
        self.prev_theta = self._theta()
        self.progress = self.prev_theta + math.pi / 2   # startlijn = -90 graden
        self.finished = False

        self.sprite = pygame.Surface((40, 22), pygame.SRCALPHA)
        pygame.draw.rect(self.sprite, color, (0, 0, 40, 22), border_radius=6)
        pygame.draw.rect(self.sprite, (30, 40, 70), (22, 3, 9, 16), border_radius=3)
        pygame.draw.rect(self.sprite, (20, 20, 20), (5, 0, 9, 3))
        pygame.draw.rect(self.sprite, (20, 20, 20), (5, 19, 9, 3))
        pygame.draw.rect(self.sprite, (20, 20, 20), (27, 0, 9, 3))
        pygame.draw.rect(self.sprite, (20, 20, 20), (27, 19, 9, 3))

    def _theta(self):
        return math.atan2((self.y - CY) / MID_B, (self.x - CX) / MID_A)

    @property
    def laps_done(self):
        return max(0, int(self.progress // TAU))

    def update(self, dt, throttle, brake, steer):
        if throttle:
            self.speed += self.accel * dt
        if brake:
            if self.speed > 0:
                self.speed -= 450 * dt
            else:
                self.speed -= self.accel * 0.5 * dt
        if not throttle and not brake:       # uitrollen
            self.speed -= math.copysign(min(abs(self.speed), 120 * dt), self.speed)

        # op het gras ga je veel langzamer
        limit = self.max_speed if on_track(self.x, self.y) else self.max_speed * 0.4
        if self.speed > limit:
            self.speed = max(limit, self.speed - 500 * dt)
        self.speed = max(self.speed, -self.max_speed * 0.3)

        grip = clamp(self.speed / 120, -1, 1)
        self.angle += steer * 160 * grip * dt

        rad = math.radians(self.angle)
        self.x = clamp(self.x + math.cos(rad) * self.speed * dt, 0, W)
        self.y = clamp(self.y + math.sin(rad) * self.speed * dt, 0, H)

        # voortgang bijhouden (hoek rond het circuit)
        theta = self._theta()
        delta = theta - self.prev_theta
        if delta > math.pi:
            delta -= TAU
        elif delta < -math.pi:
            delta += TAU
        self.progress += delta
        self.prev_theta = theta

    def draw(self, screen):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        screen.blit(rot, rot.get_rect(center=(self.x, self.y)))


# ----------------------------------------------------------------- AI
class AIDriver:
    def __init__(self, car, lookahead, lane=1.0):
        self.car = car
        self.lookahead = lookahead
        self.waypoints = [
            (CX + MID_A * lane * math.cos(-math.pi / 2 + TAU * i / N_WP),
             CY + MID_B * lane * math.sin(-math.pi / 2 + TAU * i / N_WP))
            for i in range(N_WP)
        ]

    def control(self):
        c = self.car
        theta = math.atan2((c.y - CY) / MID_B, (c.x - CX) / MID_A)
        nearest = round(((theta + math.pi / 2) % TAU) / TAU * N_WP) % N_WP
        tx, ty = self.waypoints[(nearest + self.lookahead) % N_WP]

        wanted = math.degrees(math.atan2(ty - c.y, tx - c.x))
        diff = wrap_deg(wanted - c.angle)
        steer = clamp(diff / 20, -1, 1)

        throttle = abs(diff) < 40 or c.speed < 150
        brake = c.speed > 200 and abs(diff) > 55
        return throttle, brake, steer


# ----------------------------------------------------------------- spel
def collide(a, b):
    dx, dy = b.x - a.x, b.y - a.y
    dist = math.hypot(dx, dy) or 0.001
    if dist < 30:
        push = (30 - dist) / 2
        nx, ny = dx / dist, dy / dist
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push
        a.speed *= 0.97
        b.speed *= 0.97


def new_race(level):
    _, ai_speed, look = DIFFICULTY[level]
    start_x = CX - 50
    player = Car(start_x, CY - OUT_B + 80, (220, 40, 40), 300)
    ai_car = Car(start_x, CY - OUT_B + 140, (50, 110, 230), ai_speed)
    return player, ai_car, AIDriver(ai_car, look)


def draw_text(screen, font, text, pos, color=(255, 255, 255), center=False):
    img = font.render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    screen.blit(img, rect)


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Top-down Racer vs AI")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26)
    big = pygame.font.SysFont("arial", 72, bold=True)
    track = build_track()

    state = "menu"
    level = 2
    player = ai_car = ai = None
    countdown = 3.0
    race_time = 0.0
    winner = None

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if state == "menu" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    level = event.key - pygame.K_0
                if state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    player, ai_car, ai = new_race(level)
                    countdown, race_time, winner = 3.0, 0.0, None
                    state = "countdown"
                if event.key == pygame.K_r:
                    state = "menu"

        keys = pygame.key.get_pressed()

        # ---- logica
        if state == "countdown":
            countdown -= dt
            if countdown <= 0:
                state = "race"
        elif state == "race":
            race_time += dt
            throttle = keys[pygame.K_UP] or keys[pygame.K_w]
            brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
            steer = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            player.update(dt, throttle, brake, steer)
            ai_car.update(dt, *ai.control())
            collide(player, ai_car)

            for car, naam in ((player, "Jij"), (ai_car, "De AI")):
                if car.progress >= LAPS * TAU:
                    winner = naam
                    state = "finished"
                    break

        # ---- tekenen
        screen.blit(track, (0, 0))
        if player:
            ai_car.draw(screen)
            player.draw(screen)

        if state in ("countdown", "race", "finished") and player:
            positie = 1 if player.progress >= ai_car.progress else 2
            lap = min(player.laps_done + 1, LAPS)
            draw_text(screen, font, f"Ronde {lap}/{LAPS}", (CX, CY - 40), center=True)
            draw_text(screen, font, f"Positie {positie}/2", (CX, CY), center=True)
            draw_text(screen, font, f"Tijd {race_time:5.1f}s", (CX, CY + 40), center=True)
            draw_text(screen, font, f"{abs(player.speed) / 3:3.0f} km/h", (CX, CY + 80), center=True)

        if state == "menu":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            draw_text(screen, big, "TOP-DOWN RACER", (CX, 200), center=True)
            draw_text(screen, font, "Kies moeilijkheid met 1 / 2 / 3, start met ENTER", (CX, 300), center=True)
            for k, (naam, _, _) in DIFFICULTY.items():
                kleur = (255, 220, 60) if k == level else (200, 200, 200)
                draw_text(screen, font, f"{k}. {naam}", (CX, 350 + k * 40), kleur, center=True)
            draw_text(screen, font, "Pijltjes/WASD = rijden   R = menu   ESC = stoppen", (CX, 560), center=True)

        if state == "countdown":
            draw_text(screen, big, str(math.ceil(countdown)), (CX, 120), (255, 220, 60), center=True)

        if state == "race" and race_time < 1:
            draw_text(screen, big, "GO!", (CX, 120), (80, 255, 80), center=True)

        if state == "finished":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            tekst = "Je hebt gewonnen!" if winner == "Jij" else "De AI heeft gewonnen!"
            draw_text(screen, big, tekst, (CX, CY - 30), center=True)
            draw_text(screen, font, f"Tijd: {race_time:.1f}s   -   druk op R voor het menu", (CX, CY + 40), center=True)

        pygame.display.flip()


if __name__ == "__main__":
    main()
