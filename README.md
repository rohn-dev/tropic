# Trophic — A Living Ecosystem

**An evolutionary ecosystem simulation built with Python and Pygame.**

Trophic is an interactive ecosystem simulator where flora, herbivores, carnivores, apex predators, and parasites coexist in a dynamic environment.

Every organism follows behavioural and survival rules, competes for resources, reproduces, and evolves through genetic mutations. Over time, natural selection influences population dynamics and the distribution of inherited traits.

The simulation combines artificial life, evolutionary biology, predator-prey interactions, and computational modelling into a real-time visual environment.

---

## Overview

Trophic simulates a closed food web in which organisms interact with their environment and one another.

Unlike a predefined animation, the ecosystem evolves through individual organism behaviours and interactions. Population changes, reproduction, starvation, predation, and extinction emerge from the simulation rules.

Each animal carries inherited genetic traits that influence its behaviour and survival.

### The Ecosystem

| Species | Role | Behaviour |
| --- | --- | --- |
| Flora | Primary producers | Grow and provide energy to herbivores |
| Herbivores | Primary consumers | Graze on plants and flee predators |
| Carnivores | Secondary consumers | Hunt herbivores |
| Apex Predators | Top-level consumers | Hunt herbivores and carnivores |
| Parasites | Host-dependent organisms | Attach to hosts and drain their energy |

## Key Features

- **Dynamic Food Web:** Five interacting populations with different ecological roles.
- **Evolutionary Genetics:** Organisms inherit genetic traits that mutate during reproduction.
- **Natural Selection:** Genetic variation influences movement, resource acquisition, metabolism, and reproduction.
- **Predator-Prey Behaviour:** Organisms detect threats, pursue prey, flee predators, and wander when no target is available.
- **Parasitism:** Parasites attach to hosts, drain their energy, reproduce, and detach or die when necessary.
- **Population Dynamics:** Tracks births, deaths, population changes, and extinction events.
- **Species Migration:** Extinct animal populations can be restored through migration after a specified delay.
- **Real-Time Visualization:** Displays the ecosystem, population statistics, and historical population trends.
- **Experimental Analysis:** Includes a separate experiment framework for studying different ecological scenarios and mutation rates.
- **Unit Testing:** Tests core simulation mechanics, genetics, reproduction, and ecosystem behaviour.

---

## Evolutionary Genetics

Every animal carries five inherited genetic parameters:

| Gene | Function |
| --- | --- |
| Speed | Influences movement speed |
| Size | Influences physical size and energy expenditure |
| Sense | Determines detection range |
| Metabolism | Influences energy consumption |
| Reproduction | Influences the energy threshold for reproduction |

Parasites have two genetic parameters:

- **Virulence:** Determines how aggressively they drain host energy.
- **Sense:** Influences their ability to detect potential hosts.

### Mutation

When an animal reproduces, its offspring inherit modified versions of its parent's genes.

Mutations introduce variation into the population, allowing different traits to become more or less common over successive generations.

The mutation rate can be adjusted during runtime, allowing experimentation with different evolutionary conditions.

---

## Simulation Mechanics

### 1. Movement and Behaviour

- Animals detect nearby organisms within their sensing range.
- Herbivores flee from carnivores and apex predators.
- Carnivores pursue herbivores.
- Apex predators hunt both herbivores and carnivores.
- Organisms wander when no immediate threat or food source is detected.

### 2. Energy and Survival

- Organisms consume energy through movement and metabolism.
- Successful feeding restores energy.
- Parasites drain energy from their hosts.
- Organisms die when their energy reaches zero or their maximum age is exceeded.

### 3. Reproduction

- Animals reproduce asexually when their energy exceeds a gene-dependent threshold.
- Reproduction consumes energy.
- Offspring inherit mutated genetic traits.
- Population caps prevent unrestricted population growth.

### 4. Extinction and Migration

- The simulation detects when previously established populations become extinct.
- Extinction and recovery events are recorded.
- Certain species can migrate back into the ecosystem after an extinction delay.

---

## Tech Stack

| Technology | Purpose |
| --- | --- |
| Python | Core simulation logic |
| Pygame | Real-time visualization and interaction |
| Random | Stochastic behaviour and genetic mutation |
| Math | Movement, distances, and mathematical modelling |
| JSON | Experimental results and simulation caching |
| Multiprocessing | Parallel execution of experiments |
| Unittest | Automated testing |

---

## Installation

### Prerequisites

- Python 3.10 or later
- pip

### 1. Clone the repository

```bash
git clone https://github.com/rohn-dev/tropic.git
cd tropic
```

### 2. Install dependencies

```bash
pip install pygame
```

### 3. Run the simulation

```bash
python trophic.py
```

The simulation window will open with the ecosystem running automatically.

---

## Controls

| Key / Action | Function |
| --- | --- |
| `SPACE` | Pause / Resume |
| `1` | Simulation speed: 1x |
| `2` | Simulation speed: 2x |
| `3` | Simulation speed: 4x |
| `UP` | Increase mutation rate by 0.1 |
| `DOWN` | Decrease mutation rate by 0.1 |
| `R` | Reseed the ecosystem |
| `LEFT CLICK` | Inspect an organism's genes |
| `ESC` | Exit simulation |

---

## Experimental Framework

Trophic includes a separate experimental framework (`experiments.py`) designed to investigate ecosystem behaviour under different environmental conditions.

Rather than relying solely on visual observations, experiments run multiple seeded simulations and collect numerical measurements.

### Experimental Scenarios

| Scenario | Configuration |
| --- | --- |
| A | Full ecosystem |
| B | No parasites |
| C | No apex predators |
| D | Flora and herbivores only |
| E | Full ecosystem with migration disabled |

### Mutation Rate Experiments

The framework evaluates five mutation rates:

`0.0 | 0.5 | 1.0 | 2.0 | 3.0`

This allows comparison of evolutionary outcomes under different mutation intensities.

### Measurements

The experimental framework records:

- Mean population sizes
- Population standard deviations
- Extinction frequency
- Species survival fractions
- Average extinction timing
- Birth and death counts
- Genetic trait trajectories
- Initial-to-final genetic trait shifts
- Simulation performance and execution time

### Running Experiments

For the complete experimental study:

```bash
python experiments.py
```

For a shorter experimental run:

```bash
python experiments.py --quick
```

| Configuration | Full Study | Quick Study |
| --- | ---: | ---: |
| Seeds per scenario | 30 | 6 |
| Simulation ticks | 18,000 | 6,000 |
| Simulated time | 300 seconds | 100 seconds |
| Approximate duration | 15–20 minutes | 1 minute |

Experiments run in parallel using two worker processes.

Results are saved to:

```text
results.json
```

Individual completed runs are cached in `run_cache/`, allowing interrupted experiments to resume without repeating completed simulations.

---

## Testing

The project includes automated unit tests covering the simulation's core mechanics.

Run the complete test suite:

```bash
python -m unittest test_trophic -v
```

Tests cover:

- Helper functions and colour shading
- Genetic initialization and mutation boundaries
- Herbivore predator-avoidance behaviour
- Feeding and energy restoration
- Energy limits and starvation
- World-boundary constraints
- Reproduction and population limits
- Parasite attachment and host energy drainage
- Parasite release after host death
- Extinction and migration
- Reproducibility using random seeds

The tests run without opening a graphical window.

---

## Project Structure

```text
trophic/
│
├── trophic.py
│   └── Main simulation engine and Pygame renderer
│
├── experiments.py
│   └── Experimental framework and statistical analysis
│
├── test_trophic.py
│   └── Automated unit tests
│
├── results.json
│   └── Generated experimental results
│
└── run_cache/
    └── Cached individual simulation runs
```

`results.json` and `run_cache/` are generated when experiments are executed.

---

## Project Objective

The objective of Trophic is to explore how complex ecological behaviour can emerge from relatively simple individual rules.

By combining population interactions, genetic variation, reproduction, and environmental pressures, the simulation provides a computational environment for observing evolutionary and ecological dynamics.

It also demonstrates how computational modelling can be used to investigate biological systems, collect experimental data, and evaluate the effects of changing simulation parameters.

---

## License

This project is open-source. Add a license file to specify the terms under which others can use, modify, and distribute the project.
