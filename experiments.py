

import json
import math
import os
import random
import sys
import time
from collections.abc import Iterable
from multiprocessing import Pool
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import trophic as t  # noqa: E402

KINDS = list(t.COLORS)                    # plant herbivore carnivore predator parasite
ANIMALS = list(t.ANIMALS)
GENES = ("speed", "size", "sense", "metab", "repro")
DT = 1.0 / 60.0                           # simulated seconds per tick
SAMPLE = 150                              # record a sample every 150 ticks (2.5 s)

QUICK = "--quick" in sys.argv
TICKS = 6000 if QUICK else 18000          # 18000 ticks = 300 simulated seconds
SEEDS = 6 if QUICK else 30


def mean(xs: Iterable[float | int | None]) -> float | None:
    values = [value for value in xs if value is not None]
    return sum(values) / len(values) if values else None


def make_sim(seed, mutation=1.0, remove=(), migration=True):
    """Create a seeded simulation. `remove` deletes species from the start and
    stops them from ever migrating back in."""
    random.seed(seed)
    sim = t.Sim()
    sim.mutation = mutation
    for kind in remove:
        sim.pops[kind] = []
        sim.extinct_since[kind] = float("inf")   # migrate() never reaches the delay
    if not migration:
        sim.migrate = lambda: None
    return sim


def gene_means(sim):
    out: dict[str, dict[str, float | None]] = {}
    for kind in ANIMALS:
        pop = sim.pops[kind]
        out[kind] = {g: (sum(a.g[g] for a in pop) / len(pop) if pop else None) for g in GENES}
    par = sim.pops["parasite"]
    out["parasite"] = {
        "virulence": sum(p.g["virulence"] for p in par) / len(par) if par else None,
        "sense": sum(p.g["sense"] for p in par) / len(par) if par else None,
    }
    return out


CACHE = "run_cache"   # every finished run is saved here, so an interrupted study can resume


def run_one(args):
    """Run one seeded simulation (or load it from the cache if it already ran)."""
    seed, mutation, remove, migration, ticks = args
    path = os.path.join(CACHE, "s%d_m%s_r%s_g%d_t%d.json" % (
        seed, mutation, "-".join(remove) or "none", migration, ticks))
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    result = _simulate(seed, mutation, remove, migration, ticks)
    os.makedirs(CACHE, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(result, f)
    os.replace(path + ".tmp", path)
    return result


def _simulate(seed, mutation, remove, migration, ticks):
    sim = make_sim(seed, mutation, remove, migration)
    prev = {k: len(sim.pops[k]) for k in KINDS}
    ext = {k: 0 for k in KINDS}
    first_ext: dict[str, int | None] = {k: None for k in KINDS}
    series = {"tick": [], **{k: [] for k in KINDS}}
    genes = []
    for i in range(ticks + 1):
        if i % SAMPLE == 0:
            series["tick"].append(i)
            for k in KINDS:
                series[k].append(len(sim.pops[k]))
            genes.append(gene_means(sim))
        if i == ticks:
            break
        sim.step(DT)
        for k in KINDS:
            n = len(sim.pops[k])
            if prev[k] > 0 and n == 0:
                ext[k] += 1
                if first_ext[k] is None:
                    first_ext[k] = i
            prev[k] = n
    return dict(seed=seed, series=series, genes=genes, extinctions=ext,
                first_ext=first_ext, alive_at_end={k: len(sim.pops[k]) > 0 for k in KINDS},
                births=sim.births, deaths=sim.deaths)


def summarise(runs):
    """Aggregate a list of runs into the numbers used in the report."""
    n = len(runs)
    out: dict[str, Any] = {"n_runs": n}
    out["mean_pop"] = {k: mean([mean(r["series"][k]) for r in runs]) for k in KINDS}
    out["sd_pop"] = {}
    for k in KINDS:
        vals = [v for v in (mean(r["series"][k]) for r in runs) if v is not None]
        m = mean(vals)
        if m is None:
            out["sd_pop"][k] = 0.0
        else:
            out["sd_pop"][k] = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1)) if n > 1 else 0.0
    out["extinctions_per_run"] = {k: mean([r["extinctions"][k] for r in runs]) for k in KINDS}
    out["alive_at_end_frac"] = {k: sum(r["alive_at_end"][k] for r in runs) / n for k in KINDS}
    out["runs_with_any_extinction_frac"] = {
        k: sum(r["extinctions"][k] > 0 for r in runs) / n for k in KINDS}
    fe = [r["first_ext"][k] for r in runs for k in ANIMALS + ["parasite"]
          if r["first_ext"][k] is not None]
    out["mean_first_extinction_tick"] = mean(fe)
    out["births_per_run"] = mean([r["births"] for r in runs])
    out["deaths_per_run"] = mean([r["deaths"] for r in runs])
    # trait trajectories (mean over runs at each sample, ignoring runs where the species is absent)
    steps = len(runs[0]["genes"])
    traj = {}
    for kind in ANIMALS:
        traj[kind] = {}
        for g in GENES:
            traj[kind][g] = []
            for s in range(steps):
                vals = [v for v in (r["genes"][s][kind][g] for r in runs) if v is not None]
                m = mean(vals)
                if m is None:
                    traj[kind][g].append({"mean": None, "sd": 0.0, "n": 0})
                    continue
                sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
                traj[kind][g].append({"mean": m, "sd": sd, "n": len(vals)})
    traj["parasite"] = {}
    for g in ("virulence", "sense"):
        traj["parasite"][g] = []
        for s in range(steps):
            vals = [v for v in (r["genes"][s]["parasite"][g] for r in runs) if v is not None]
            m = mean(vals)
            if m is None:
                traj["parasite"][g].append({"mean": None, "sd": 0.0, "n": 0})
                continue
            sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
            traj["parasite"][g].append({"mean": m, "sd": sd, "n": len(vals)})
    out["traj"] = traj
    out["ticks"] = runs[0]["series"]["tick"]
    # per-run initial vs final-window gene means, for significance tests
    shift = {}
    last = max(1, steps // 10)  # last 10 % of the run
    for kind in ANIMALS + ["parasite"]:
        shift[kind] = {}
        names = GENES if kind != "parasite" else ("virulence", "sense")
        for g in names:
            deltas = []
            for r in runs:
                start = r["genes"][0][kind][g]
                end_vals = [r["genes"][s][kind][g] for s in range(steps - last, steps)
                            if r["genes"][s][kind][g] is not None]
                if start is None or not end_vals:
                    continue
                end_mean = mean(end_vals)
                if end_mean is not None:
                    deltas.append(end_mean - start)
            shift[kind][g] = deltas
    out["gene_shift"] = shift
    # one example run for the population time-series figure
    out["example_series"] = runs[0]["series"]
    return out


def timing(scale):
    """Mean cost of one simulation tick when the world is `scale` times larger
    (initial counts and population caps scaled together). Rendering is excluded."""
    base_caps = dict(t.CAPS)
    for k in t.CAPS:
        t.CAPS[k] = int(base_caps[k] * scale)
    try:
        random.seed(123)
        sim = t.Sim()
        extra = {"plant": 70, "herbivore": 26, "carnivore": 10, "predator": 3, "parasite": 7}
        for _ in range(int(70 * (scale - 1))):
            sim.spawn_plant(None)
        for kind in ANIMALS:
            for _ in range(int(extra[kind] * (scale - 1))):
                sim.spawn_animal(kind, *sim.rand_pos())
        for _ in range(int(7 * (scale - 1))):
            sim.spawn_parasite(*sim.rand_pos())
        for _ in range(600):                       # warm-up
            sim.step(DT)
        counts, t0 = [], time.perf_counter()
        n = 900
        for _ in range(n):
            sim.step(DT)
            counts.append(sum(len(v) for v in sim.pops.values()))
        el = time.perf_counter() - t0
        return {"scale": scale, "organisms": sum(counts) / len(counts),
                "ms_per_tick": 1000 * el / n, "ticks_per_s": n / el}
    finally:
        t.CAPS.update(base_caps)


def main():
    t0 = time.time()
    results: dict[str, Any] = {"config": {"ticks": TICKS, "seeds": SEEDS, "dt": DT, "sample_every": SAMPLE,
                                          "quick": QUICK, "python": sys.version.split()[0]}}
    scenarios = {
        "A": dict(desc="Full ecosystem", remove=(), mutation=1.0, migration=True),
        "B": dict(desc="No parasites", remove=("parasite",), mutation=1.0, migration=True),
        "C": dict(desc="No apex predators", remove=("predator",), mutation=1.0, migration=True),
        "D": dict(desc="Flora and herbivores only",
                  remove=("carnivore", "predator", "parasite"), mutation=1.0, migration=True),
        "E": dict(desc="Full ecosystem, migration off", remove=(), mutation=1.0, migration=False),
    }
    sweep = [0.0, 0.5, 2.0, 3.0]  # mutation-rate sweep on scenario A (1.0 is scenario A itself)

    jobs, keys = [], []
    for name, sc in scenarios.items():
        for s in range(SEEDS):
            jobs.append((s, sc["mutation"], sc["remove"], sc["migration"], TICKS))
            keys.append(("scenario", name))
    for m in sweep:
        for s in range(SEEDS):
            jobs.append((s, m, (), True, TICKS))
            keys.append(("mut", str(m)))

    print(f"{len(jobs)} runs of {TICKS} ticks each ...", flush=True)
    with Pool(2) as pool:
        outs = []
        for i, r in enumerate(pool.imap(run_one, jobs, chunksize=1), 1):
            outs.append(r)
            if i % 10 == 0:
                print(f"  {i}/{len(jobs)} done, {time.time() - t0:.0f}s", flush=True)

    groups = {}
    for key, r in zip(keys, outs):
        groups.setdefault(key, []).append(r)

    results["scenarios"] = {}
    for name, sc in scenarios.items():
        results["scenarios"][name] = {"desc": sc["desc"], **summarise(groups[("scenario", name)])}
    results["mutation_sweep"] = {}
    for m in [0.0, 0.5, 1.0, 2.0, 3.0]:
        runs = groups[("scenario", "A")] if m == 1.0 else groups[("mut", str(m))]
        results["mutation_sweep"][str(m)] = summarise(runs)

    print("timing ...", flush=True)
    results["timing"] = [timing(s) for s in (0.5, 1, 2, 4, 8)]

    results["elapsed_s"] = time.time() - t0
    # the big per-run lists are not needed downstream; keep the file small enough to open
    with open("results.json", "w") as f:
        json.dump(results, f)
    print(f"wrote results.json in {results['elapsed_s']:.0f}s")


if __name__ == "__main__":
    main()
