#!/usr/bin/env python3
"""
Trophic - a living ecosystem (pygame edition)

A closed food web of flora, herbivores, carnivores, apex predators and
parasites. Every animal carries genes (speed, size, sense, metabolism,
reproduction threshold) that mutate on reproduction, so natural selection
acts on the population while you watch.

Setup:
    pip install pygame
Run:
    python trophic.py

Controls:
    SPACE        pause / resume
    1 / 2 / 3    speed 1x / 2x / 4x
    UP / DOWN    mutation rate +/- 0.1
    R            reseed the ecosystem
    Click        inspect a creature's genes
    ESC          quit
"""

import math
import random
import sys

import pygame

# --------------------------------------------------------------------------
# layout / palette
# --------------------------------------------------------------------------
WORLD_W, WORLD_H = 900, 680
SIDE_W = 300
WIN_W, WIN_H = WORLD_W + SIDE_W, WORLD_H
FPS = 60
PAD = 14

BG = (12, 20, 16)
PANEL = (18, 28, 21)
PANEL_ALT = (15, 24, 18)
BORDER = (36, 52, 41)
TEXT = (232, 229, 216)
TEXT_DIM = (138, 150, 137)
TEXT_FAINT = (92, 103, 94)
ACCENT = (217, 164, 65)

COLORS = {
    "plant": (95, 154, 76),
    "herbivore": (163, 209, 127),
    "carnivore": (193, 90, 52),
    "predator": (217, 178, 62),
    "parasite": (154, 114, 199),
}
NAMES = {
    "plant": "Flora",
    "herbivore": "Herbivores",
    "carnivore": "Carnivores",
    "predator": "Apex predators",
    "parasite": "Parasites",
}
DESCS = {
    "plant": "grows freely, feeds herbivores",
    "herbivore": "grazes flora, flees predation",
    "carnivore": "hunts herbivores",
    "predator": "hunts carnivores & herbivores",
    "parasite": "drains any host it attaches to",
}

# --------------------------------------------------------------------------
# species configuration
# --------------------------------------------------------------------------
SPECIES = {
    "herbivore": dict(speed=52, sense=95, max_e=100, start_e=52, metab=0.85,
                      repro=0.82, repro_cost=0.5, gain=20, max_age=60,
                      radius=5.5, eats=("plant",), fears=("carnivore", "predator")),
    "carnivore": dict(speed=66, sense=135, max_e=125, start_e=60, metab=1.05,
                      repro=0.80, repro_cost=0.5, gain=52, max_age=52,
                      radius=7.0, eats=("herbivore",), fears=("predator",)),
    "predator": dict(speed=58, sense=150, max_e=160, start_e=85, metab=1.6,
                     repro=0.88, repro_cost=0.55, gain=52, max_age=70,
                     radius=8.5, eats=("carnivore", "herbivore"), fears=()),
}
CAPS = {"plant": 140, "herbivore": 90, "carnivore": 40, "predator": 8, "parasite": 55}
ANIMALS = ("herbivore", "carnivore", "predator")


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def shade(color, f):
    """Blend a colour toward the background; f=1 is full colour."""
    f = clamp(f, 0.0, 1.0)
    return tuple(int(BG[i] + (color[i] - BG[i]) * f) for i in range(3))


# --------------------------------------------------------------------------
# entities
# --------------------------------------------------------------------------
class Plant:
    __slots__ = ("x", "y", "dead")

    def __init__(self, x, y):
        self.x, self.y, self.dead = x, y, False


class Animal:
    def __init__(self, kind, x, y, genes):
        spec = SPECIES[kind]
        self.kind = kind
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.wander = random.uniform(0, math.tau)
        self.g = genes
        self.energy = spec["start_e"]
        self.age = 0.0
        self.last_repro = 0.0
        self.parasites = []
        self.dead = False


class Parasite:
    def __init__(self, x, y, genes):
        self.x, self.y = x, y
        self.g = genes
        self.host = None
        self.energy = 20.0
        self.age = 0.0
        self.wander = random.uniform(0, math.tau)
        self.dead = False


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
class Sim:
    def __init__(self):
        self.mutation = 1.0
        self.reset()

    # -- setup -------------------------------------------------------------
    def reset(self):
        self.pops = {k: [] for k in COLORS}
        self.tick = 0
        self.births = 0
        self.deaths = 0
        self.history = []
        self.last_sample = 0
        self.ever_seen = {k: False for k in COLORS}
        self.extinct = {k: False for k in COLORS}
        self.extinct_since = {}
        self.events = []
        self.selected = None

        for _ in range(70):
            self.spawn_plant(None)
        for _ in range(26):
            self.spawn_animal("herbivore", *self.rand_pos())
        for _ in range(10):
            self.spawn_animal("carnivore", *self.rand_pos())
        for _ in range(3):
            self.spawn_animal("predator", *self.rand_pos())
        for _ in range(7):
            self.spawn_parasite(*self.rand_pos())

    @staticmethod
    def rand_pos():
        return (random.uniform(PAD, WORLD_W - PAD), random.uniform(PAD, WORLD_H - PAD))

    # -- genetics ----------------------------------------------------------
    @staticmethod
    def new_genes():
        return {
            "speed": clamp(1 + random.gauss(0, 0.15), 0.55, 1.75),
            "size": clamp(1 + random.gauss(0, 0.15), 0.55, 1.75),
            "sense": clamp(1 + random.gauss(0, 0.15), 0.55, 1.75),
            "metab": clamp(1 + random.gauss(0, 0.10), 0.6, 1.6),
            "repro": clamp(1 + random.gauss(0, 0.10), 0.6, 1.5),
        }

    def mutate(self, g):
        r = self.mutation
        return {
            "speed": clamp(g["speed"] + random.gauss(0, 0.10 * r), 0.5, 1.9),
            "size": clamp(g["size"] + random.gauss(0, 0.10 * r), 0.5, 1.9),
            "sense": clamp(g["sense"] + random.gauss(0, 0.10 * r), 0.5, 1.9),
            "metab": clamp(g["metab"] + random.gauss(0, 0.07 * r), 0.55, 1.7),
            "repro": clamp(g["repro"] + random.gauss(0, 0.07 * r), 0.55, 1.6),
        }

    def mutate_parasite(self, g):
        r = self.mutation
        return {
            "virulence": clamp(g["virulence"] + random.gauss(0, 0.09 * r), 0.5, 2.0),
            "sense": clamp(g["sense"] + random.gauss(0, 0.09 * r), 0.5, 1.9),
        }

    # -- spawning ----------------------------------------------------------
    def spawn_plant(self, near):
        plants = self.pops["plant"]
        if len(plants) >= CAPS["plant"]:
            return
        x = y = None
        if near is not None and random.random() < 0.62:
            x = near.x + random.uniform(-45, 45)
            y = near.y + random.uniform(-45, 45)
            if not (PAD <= x <= WORLD_W - PAD and PAD <= y <= WORLD_H - PAD):
                x = None  # seed fell off the map: scatter randomly instead
        if x is None:
            x, y = self.rand_pos()
        plants.append(Plant(x, y))

    def spawn_animal(self, kind, x, y, genes=None):
        a = Animal(kind, x, y, genes or self.new_genes())
        self.pops[kind].append(a)
        return a

    def spawn_parasite(self, x, y, genes=None):
        if len(self.pops["parasite"]) >= CAPS["parasite"]:
            return
        genes = genes or {
            "virulence": clamp(1 + random.gauss(0, 0.15), 0.6, 1.7),
            "sense": clamp(1 + random.gauss(0, 0.15), 0.6, 1.7),
        }
        self.pops["parasite"].append(Parasite(x, y, genes))

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def nearest(entities, x, y, max_d2):
        best, best_d = None, max_d2
        for e in entities:
            if e.dead:
                continue
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < best_d:
                best, best_d = e, d
        return best, best_d

    def release_parasites(self, host):
        for p in host.parasites:
            if random.random() < 0.45:
                p.host = None
                p.energy *= 0.5
            else:
                p.dead = True
        host.parasites = []

    def log(self, text, is_death=False):
        self.events.append((f"tick {self.tick} - {text}", is_death))
        self.events = self.events[-40:]

    # -- animal behaviour --------------------------------------------------
    def step_animal(self, a, dt):
        spec = SPECIES[a.kind]
        penalty = 0.8 if a.parasites else 1.0
        speed = spec["speed"] * a.g["speed"] * penalty
        sense = spec["sense"] * a.g["sense"] * penalty
        sense2 = sense * sense

        # flee?
        threat, threat_d = None, float("inf")
        for ft in spec["fears"]:
            cand, d = self.nearest(self.pops[ft], a.x, a.y, sense2)
            if cand is not None and d < threat_d:
                threat, threat_d = cand, d

        # hunt?
        target, target_kind = None, None
        if threat is None:
            best_d = float("inf")
            for ft in spec["eats"]:  # go for whichever prey is closest
                cand, d = self.nearest(self.pops[ft], a.x, a.y, sense2)
                if cand is not None and d < best_d:
                    target, target_kind, best_d = cand, ft, d

        if threat is not None:
            dx, dy = a.x - threat.x, a.y - threat.y
            length = math.hypot(dx, dy) or 1.0
            a.vx, a.vy = dx / length * speed, dy / length * speed
        elif target is not None:
            dx, dy = target.x - a.x, target.y - a.y
            length = math.hypot(dx, dy) or 1.0
            a.vx, a.vy = dx / length * speed, dy / length * speed
            if length < spec["radius"] + 4:
                if target_kind != "plant":
                    self.release_parasites(target)
                target.dead = True
                a.energy = min(spec["max_e"], a.energy + spec["gain"])
        else:
            a.wander += random.gauss(0, 0.9) * dt
            a.vx = math.cos(a.wander) * speed * 0.42
            a.vy = math.sin(a.wander) * speed * 0.42

        a.x += a.vx * dt
        a.y += a.vy * dt
        if a.x < PAD:
            a.x, a.wander = PAD, math.pi - a.wander
        elif a.x > WORLD_W - PAD:
            a.x, a.wander = WORLD_W - PAD, math.pi - a.wander
        if a.y < PAD:
            a.y, a.wander = PAD, -a.wander
        elif a.y > WORLD_H - PAD:
            a.y, a.wander = WORLD_H - PAD, -a.wander

        move_factor = 0.35 + (math.hypot(a.vx, a.vy) / speed) * 0.65
        size_cost = 0.65 + 0.35 * a.g["size"]
        a.energy -= spec["metab"] * a.g["metab"] * move_factor * size_cost * dt * 3.1
        a.age += dt

        # reproduction (asexual, with mutation)
        pop = self.pops[a.kind]
        if (a.energy > spec["max_e"] * spec["repro"] * a.g["repro"]
                and a.age - a.last_repro > 3.5 and len(pop) < CAPS[a.kind]):
            cost = spec["max_e"] * spec["repro_cost"]
            a.energy -= cost
            a.last_repro = a.age
            child = self.spawn_animal(
                a.kind,
                clamp(a.x + random.uniform(-14, 14), PAD, WORLD_W - PAD),
                clamp(a.y + random.uniform(-14, 14), PAD, WORLD_H - PAD),
                self.mutate(a.g),
            )
            child.energy = clamp(cost * 0.65, 10, spec["max_e"])
            self.births += 1

        # death
        if a.energy <= 0 or a.age > spec["max_age"] * random.uniform(0.85, 1.15):
            self.release_parasites(a)
            a.dead = True

    # -- parasite behaviour ------------------------------------------------
    def detach(self, p):
        if p.host is not None and p in p.host.parasites:
            p.host.parasites.remove(p)
        p.host = None

    def step_parasite(self, p, dt):
        if p.host is not None:
            h = p.host
            if h.dead:
                p.host = None
            else:
                p.x = h.x + math.cos(p.wander) * 7
                p.y = h.y + math.sin(p.wander) * 7
                p.wander += dt * 1.4
                drain = 3.2 * p.g["virulence"] * dt
                h.energy -= drain
                p.energy += drain * 0.55
                p.age += dt
                if random.random() < 0.0025:
                    self.detach(p)

        if p.host is None:
            sense = 90 * p.g["sense"]
            best, best_d = None, sense * sense
            for kind in ANIMALS:
                for h in self.pops[kind]:
                    if h.dead:
                        continue
                    d = (h.x - p.x) ** 2 + (h.y - p.y) ** 2
                    if d < best_d:
                        best, best_d = h, d
            if best is not None and best_d < 100:
                p.host = best
                best.parasites.append(p)
            elif best is not None:
                dx, dy = best.x - p.x, best.y - p.y
                length = math.hypot(dx, dy) or 1.0
                p.x += dx / length * 36 * dt
                p.y += dy / length * 36 * dt
            else:
                p.wander += random.gauss(0, 0.7) * dt
                p.x += math.cos(p.wander) * 18 * dt
                p.y += math.sin(p.wander) * 18 * dt
            p.x = clamp(p.x, PAD, WORLD_W - PAD)
            p.y = clamp(p.y, PAD, WORLD_H - PAD)
            p.energy -= 0.55 * dt
            p.age += dt

        if p.energy > 34 and len(self.pops["parasite"]) < CAPS["parasite"]:
            p.energy *= 0.5
            self.spawn_parasite(p.x + random.uniform(-10, 10),
                                p.y + random.uniform(-10, 10),
                                self.mutate_parasite(p.g))
            self.births += 1

        if p.energy <= 0 or p.age > 90:
            self.detach(p)
            p.dead = True

    # -- main step ---------------------------------------------------------
    def step(self, dt):
        self.tick += 1
        plants = self.pops["plant"]
        if len(plants) < CAPS["plant"] and random.random() < 0.5:
            self.spawn_plant(random.choice(plants) if plants else None)

        for kind in ANIMALS:
            for a in list(self.pops[kind]):
                if not a.dead:
                    self.step_animal(a, dt)
        for p in list(self.pops["parasite"]):
            if not p.dead:
                self.step_parasite(p, dt)

        # sweep the dead
        for kind, lst in self.pops.items():
            alive = [e for e in lst if not e.dead]
            if kind != "plant":
                self.deaths += len(lst) - len(alive)
            self.pops[kind] = alive
        if self.selected is not None and self.selected.dead:
            self.selected = None

        for kind in COLORS:
            self.check_population(kind, len(self.pops[kind]))
        self.migrate()

        if self.tick - self.last_sample >= 18:
            self.last_sample = self.tick
            self.history.append({k: len(v) for k, v in self.pops.items()})
            self.history = self.history[-120:]

    def check_population(self, kind, count):
        if count == 0 and self.ever_seen[kind] and not self.extinct[kind]:
            self.extinct[kind] = True
            self.log(f"{NAMES[kind]} went extinct.", True)
        elif count > 0:
            if self.extinct[kind]:
                self.log(f"{NAMES[kind]} returned.")
            self.extinct[kind] = False
            self.ever_seen[kind] = True

    # -- migration ---------------------------------------------------------
    MIGRATION_DELAY = 480  # ticks a species stays extinct before migrants arrive

    def migrate(self):
        """A species that has been extinct for a while is re-seeded by a few
        migrants from outside the map, as happens between real ecosystems."""
        for kind in ("herbivore", "carnivore", "predator", "parasite"):
            if self.pops[kind]:
                self.extinct_since.pop(kind, None)
                continue
            start = self.extinct_since.setdefault(kind, self.tick)
            if self.tick - start < self.MIGRATION_DELAY:
                continue
            # only bring in predators if there is something for them to eat
            if kind == "carnivore" and not self.pops["herbivore"]:
                continue
            if kind == "predator" and not (self.pops["herbivore"] or self.pops["carnivore"]):
                continue
            if kind == "parasite" and not any(self.pops[k] for k in ANIMALS):
                continue
            n = 4 if kind in ("herbivore", "parasite") else 3
            for _ in range(n):
                # arrive at a random edge of the map
                side = random.choice("NSEW")
                x = {"W": PAD, "E": WORLD_W - PAD}.get(side, random.uniform(PAD, WORLD_W - PAD))
                y = {"N": PAD, "S": WORLD_H - PAD}.get(side, random.uniform(PAD, WORLD_H - PAD))
                if kind == "parasite":
                    self.spawn_parasite(x, y)
                else:
                    self.spawn_animal(kind, x, y)
            self.extinct_since.pop(kind, None)
            self.log(f"{NAMES[kind]}: migrants arrived.")

    # -- picking -----------------------------------------------------------
    def pick(self, x, y):
        best, best_d = None, 26 * 26
        for kind in ANIMALS:
            for a in self.pops[kind]:
                d = (a.x - x) ** 2 + (a.y - y) ** 2
                if d < best_d:
                    best, best_d = a, d
        return best


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.glow = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        self.f_title = pygame.font.SysFont("segoeui,helvetica,arial", 26, bold=True)
        self.f_hero = pygame.font.SysFont("segoeui,helvetica,arial", 52, bold=True)
        self.f_body = pygame.font.SysFont("segoeui,helvetica,arial", 15)
        self.f_small = pygame.font.SysFont("segoeui,helvetica,arial", 13)
        self.f_head = pygame.font.SysFont("segoeui,helvetica,arial", 12, bold=True)

    def text(self, s, font, color, pos, anchor="topleft"):
        img = font.render(s, True, color)
        rect = img.get_rect(**{anchor: pos})
        self.screen.blit(img, rect)
        return rect

    # -- shapes ------------------------------------------------------------
    def shape(self, kind, x, y, r, color, heading):
        s = self.screen
        if kind == "herbivore":
            pygame.draw.circle(s, color, (int(x), int(y)), max(2, int(r)))
        elif kind == "carnivore":
            c, sn = math.cos(heading), math.sin(heading)
            pts = [(r, 0), (-r * 0.7, r * 0.7), (-r * 0.7, -r * 0.7)]
            pygame.draw.polygon(s, color, [(x + px * c - py * sn, y + px * sn + py * c)
                                           for px, py in pts])
        else:  # predator
            pygame.draw.polygon(s, color, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)])

    def draw_world(self, sim):
        s = self.screen
        pygame.draw.rect(s, BG, (0, 0, WORLD_W, WORLD_H))
        self.glow.fill((0, 0, 0, 0))

        for p in sim.pops["plant"]:
            pygame.draw.circle(s, shade(COLORS["plant"], 0.85), (int(p.x), int(p.y)), 2)

        for p in sim.pops["parasite"]:
            if p.host is not None:
                pygame.draw.line(s, shade(COLORS["parasite"], 0.4),
                                 (p.x, p.y), (p.host.x, p.host.y), 1)
            pygame.draw.circle(s, COLORS["parasite"], (int(p.x), int(p.y)), 3)

        for kind in ANIMALS:
            spec = SPECIES[kind]
            for a in sim.pops[kind]:
                r = spec["radius"] * math.sqrt(a.g["size"])
                f = 0.45 + 0.55 * (a.energy / spec["max_e"])
                col = shade(COLORS[kind], f)
                pygame.draw.circle(self.glow, (*COLORS[kind], 38),
                                   (int(a.x), int(a.y)), int(r * 2.1))
                self.shape(kind, a.x, a.y, r, col, math.atan2(a.vy, a.vx))

        s.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        sel = sim.selected
        if sel is not None:
            pygame.draw.circle(s, TEXT, (int(sel.x), int(sel.y)), 14, 1)
            self.draw_inspector(sel)
        else:
            self.text("click a creature to inspect its genes", self.f_small,
                      TEXT_FAINT, (16, WORLD_H - 14), "bottomleft")

    def draw_inspector(self, a):
        spec = SPECIES[a.kind]
        box = pygame.Rect(14, 14, 230, 156)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((*PANEL_ALT, 235))
        self.screen.blit(panel, box.topleft)
        pygame.draw.rect(self.screen, BORDER, box, 1)

        x, y = box.x + 12, box.y + 10
        self.text(NAMES[a.kind][:-1] if NAMES[a.kind].endswith("s") else NAMES[a.kind],
                  self.f_body, TEXT, (x, y))
        y += 26
        self.text("energy", self.f_small, TEXT_DIM, (x, y))
        bar = pygame.Rect(x + 62, y + 5, box.w - 86, 4)
        pygame.draw.rect(self.screen, BG, bar)
        pygame.draw.rect(self.screen, ACCENT,
                         (bar.x, bar.y, int(bar.w * clamp(a.energy / spec["max_e"], 0, 1)), bar.h))
        rows = [("speed gene", f"{a.g['speed']:.2f}"), ("size gene", f"{a.g['size']:.2f}"),
                ("sense gene", f"{a.g['sense']:.2f}"), ("age", f"{a.age:.0f}s"),
                ("parasites", str(len(a.parasites)))]
        y += 22
        for label, val in rows:
            self.text(label, self.f_small, TEXT_DIM, (x, y))
            self.text(val, self.f_small, TEXT, (box.right - 12, y), "topright")
            y += 20

    # -- sidebar -----------------------------------------------------------
    def draw_legend_icon(self, kind, cx, cy):
        s, col = self.screen, COLORS[kind]
        if kind in ("plant", "herbivore", "parasite"):
            pygame.draw.circle(s, col, (cx, cy), 6)
        elif kind == "carnivore":
            pygame.draw.polygon(s, col, [(cx, cy - 7), (cx - 7, cy + 6), (cx + 7, cy + 6)])
        else:
            pygame.draw.polygon(s, col, [(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)])

    def draw_sidebar(self, sim, playing, speed):
        s = self.screen
        pygame.draw.rect(s, PANEL, (WORLD_W, 0, SIDE_W, WIN_H))
        pygame.draw.line(s, BORDER, (WORLD_W, 0), (WORLD_W, WIN_H))
        x0 = WORLD_W + 18
        w = SIDE_W - 36
        y = 16

        self.text("Trophic", self.f_title, TEXT, (x0, y))
        status = ("running" if playing else "paused") + f" - {speed}x"
        self.text(status, self.f_small, COLORS["herbivore"] if playing else COLORS["carnivore"],
                  (x0 + w, y + 10), "topright")
        y += 40

        total = sum(len(sim.pops[k]) for k in ("herbivore", "carnivore", "predator", "parasite"))
        r = self.text(str(total), self.f_hero, TEXT, (x0, y))
        self.text("organisms alive", self.f_small, TEXT_DIM, (r.right + 10, r.bottom - 12), "bottomleft")
        y = r.bottom + 2
        self.text(f"tick {sim.tick}  |  {sim.births} births  |  {sim.deaths} deaths",
                  self.f_small, TEXT_FAINT, (x0, y))
        y += 28

        self.text("SPECIES", self.f_head, TEXT_FAINT, (x0, y))
        y += 20
        for kind in COLORS:
            self.draw_legend_icon(kind, x0 + 7, y + 13)
            self.text(NAMES[kind], self.f_body, TEXT, (x0 + 24, y))
            self.text(DESCS[kind], self.f_small, TEXT_FAINT, (x0 + 24, y + 18))
            self.text(str(len(sim.pops[kind])), self.f_body, TEXT, (x0 + w, y + 6), "topright")
            y += 42

        y += 4
        self.text("POPULATION OVER TIME", self.f_head, TEXT_FAINT, (x0, y))
        y += 20
        self.draw_chart(sim, pygame.Rect(x0, y, w, 96))
        y += 96 + 16

        self.text("EVENTS", self.f_head, TEXT_FAINT, (x0, y))
        y += 20
        if not sim.events:
            self.text("watching for extinctions...", self.f_small, TEXT_FAINT, (x0, y))
        for text, is_death in reversed(sim.events[-4:]):
            pygame.draw.line(s, COLORS["carnivore"] if is_death else BORDER,
                             (x0, y + 2), (x0, y + 14), 2)
            self.text(text, self.f_small, TEXT_DIM, (x0 + 8, y))
            y += 20

        y = WIN_H - 66
        self.text("SPACE pause   1/2/3 speed   R reseed", self.f_small, TEXT_FAINT, (x0, y))
        self.text(f"UP/DOWN mutation rate: {sim.mutation:.1f}x", self.f_small, ACCENT, (x0, y + 22))

    def draw_chart(self, sim, rect):
        pygame.draw.rect(self.screen, PANEL_ALT, rect, border_radius=3)
        h = sim.history
        if len(h) < 2:
            return
        peak = max(1, max(max(row.values()) for row in h))
        pad = 6
        for kind in COLORS:
            pts = []
            for i, row in enumerate(h):
                px = rect.x + pad + i / (len(h) - 1) * (rect.w - pad * 2)
                py = rect.bottom - pad - row[kind] / peak * (rect.h - pad * 2)
                pts.append((px, py))
            col = shade(COLORS[kind], 0.55 if kind == "plant" else 1.0)
            pygame.draw.lines(self.screen, col, False, pts, 1 if kind == "plant" else 2)


# --------------------------------------------------------------------------
# main loop
# --------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Trophic - a living ecosystem")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()

    sim = Sim()
    renderer = Renderer(screen)
    playing = True
    speed = 1
    dt = 1.0 / FPS

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_1:
                    speed = 1
                elif event.key == pygame.K_2:
                    speed = 2
                elif event.key == pygame.K_3:
                    speed = 4
                elif event.key == pygame.K_r:
                    sim.reset()
                elif event.key == pygame.K_UP:
                    sim.mutation = min(3.0, round(sim.mutation + 0.1, 1))
                elif event.key == pygame.K_DOWN:
                    sim.mutation = max(0.0, round(sim.mutation - 0.1, 1))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                sim.selected = sim.pick(mx, my) if mx < WORLD_W else None

        if playing:
            for _ in range(speed):
                sim.step(dt)

        renderer.draw_world(sim)
        renderer.draw_sidebar(sim, playing, speed)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
