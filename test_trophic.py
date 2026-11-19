#!/usr/bin/env python3
"""
Unit tests for trophic.py (Chapter 9 of the report).

Run from the folder that holds trophic.py:
    python -m unittest test_trophic -v
No window is opened; the tests exercise the simulation logic only.
"""

import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import trophic as t  # noqa: E402

ONES = {"speed": 1.0, "size": 1.0, "sense": 1.0, "metab": 1.0, "repro": 1.0}


def empty_sim(seed=0):
    """A simulation with every population removed, for hand-built scenes."""
    random.seed(seed)
    sim = t.Sim()
    for kind in sim.pops:
        sim.pops[kind] = []
    sim.extinct_since = {k: float("inf") for k in sim.pops}  # no migration
    return sim


class HelperTests(unittest.TestCase):
    def test_clamp_limits_value(self):
        self.assertEqual(t.clamp(5, 0, 3), 3)
        self.assertEqual(t.clamp(-2, 0, 3), 0)
        self.assertEqual(t.clamp(2, 0, 3), 2)

    def test_shade_blends_toward_background(self):
        col = t.COLORS["carnivore"]
        self.assertEqual(t.shade(col, 1.0), col)
        self.assertEqual(t.shade(col, 0.0), t.BG)
        mid = t.shade(col, 0.5)
        for c, b, m in zip(col, t.BG, mid):
            self.assertTrue(min(c, b) <= m <= max(c, b))


class GeneticsTests(unittest.TestCase):
    def test_new_genes_within_bounds(self):
        random.seed(1)
        for _ in range(500):
            g = t.Sim.new_genes()
            for v in g.values():
                self.assertTrue(0.55 <= v <= 1.75)

    def test_mutation_keeps_genes_in_bounds(self):
        sim = empty_sim()
        sim.mutation = 3.0
        g = dict(ONES)
        for _ in range(2000):
            g = sim.mutate(g)
            for v in g.values():
                self.assertTrue(0.5 <= v <= 1.9)

    def test_zero_mutation_copies_genes_exactly(self):
        sim = empty_sim()
        sim.mutation = 0.0
        g = {"speed": 1.2, "size": 0.8, "sense": 1.1, "metab": 0.9, "repro": 1.05}
        self.assertEqual(sim.mutate(g), g)


class BehaviourTests(unittest.TestCase):
    def test_herbivore_flees_from_carnivore(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        sim.spawn_animal("carnivore", 560, 300, dict(ONES))   # inside herbivore sense range
        sim.step(0.1)
        self.assertLess(h.vx, 0)                              # running away (to the left)

    def test_herbivore_eats_plant_and_gains_energy(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        h.energy = 40.0
        sim.pops["plant"].append(t.Plant(503, 300))
        sim.step(0.05)
        self.assertEqual(len(sim.pops["plant"]), 0)
        self.assertGreater(h.energy, 40.0)

    def test_energy_never_exceeds_species_maximum(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        h.energy = t.SPECIES["herbivore"]["max_e"] - 1
        sim.pops["plant"].append(t.Plant(501, 300))
        sim.step(0.05)
        self.assertLessEqual(h.energy, t.SPECIES["herbivore"]["max_e"])

    def test_animal_starves_when_energy_reaches_zero(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        h.energy = 0.001
        sim.step(0.1)
        self.assertEqual(len(sim.pops["herbivore"]), 0)

    def test_animals_stay_inside_the_world(self):
        random.seed(5)
        sim = t.Sim()
        for _ in range(1500):
            sim.step(1 / 60)
        for kind in t.ANIMALS:
            for a in sim.pops[kind]:
                self.assertTrue(t.PAD - 1e-6 <= a.x <= t.WORLD_W - t.PAD + 1e-6)
                self.assertTrue(t.PAD - 1e-6 <= a.y <= t.WORLD_H - t.PAD + 1e-6)


class ReproductionTests(unittest.TestCase):
    def test_reproduction_costs_energy_and_adds_a_child(self):
        sim = empty_sim()
        sim.mutation = 0.0
        a = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        a.energy = t.SPECIES["herbivore"]["max_e"]
        a.age = 10.0
        sim.step(0.01)
        self.assertEqual(len(sim.pops["herbivore"]), 2)
        self.assertLess(a.energy, t.SPECIES["herbivore"]["max_e"])
        self.assertEqual(sim.births, 1)

    def test_population_caps_are_respected(self):
        random.seed(2)
        sim = t.Sim()
        for _ in range(6000):
            sim.step(1 / 60)
            for kind, cap in t.CAPS.items():
                self.assertLessEqual(len(sim.pops[kind]), cap + 4)  # +4: migrants are not capped


class ParasiteTests(unittest.TestCase):
    def test_parasite_attaches_and_drains_host(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        h.energy = 50.0
        sim.spawn_parasite(502, 300)
        sim.step(0.1)
        self.assertEqual(len(h.parasites), 1)
        sim.step(0.5)
        self.assertLess(h.energy, 50.0)

    def test_parasites_are_released_when_host_dies(self):
        sim = empty_sim()
        h = sim.spawn_animal("herbivore", 500, 300, dict(ONES))
        h.energy = 0.001
        sim.spawn_parasite(502, 300)
        sim.step(0.1)
        self.assertEqual(len(sim.pops["herbivore"]), 0)
        for p in sim.pops["parasite"]:
            self.assertIsNone(p.host)


class EcosystemTests(unittest.TestCase):
    def test_extinct_species_is_logged_then_restored_by_migration(self):
        random.seed(3)
        sim = t.Sim()
        sim.pops["predator"] = []
        sim.extinct_since.pop("predator", None)
        for _ in range(sim.MIGRATION_DELAY + 5):
            sim.step(1 / 60)
        self.assertTrue(any("migrants" in text for text, _ in sim.events))
        self.assertGreater(len(sim.pops["predator"]), 0)

    def test_same_seed_gives_identical_run(self):
        def run():
            random.seed(42)
            sim = t.Sim()
            for _ in range(1200):
                sim.step(1 / 60)
            return {k: len(v) for k, v in sim.pops.items()}, sim.births, sim.deaths
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
