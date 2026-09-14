# LR-FHSS-sim

Event-driven simulator for LR-FHSS (LoRa-like frequency-hopping) random-access
networks, built in Python. Supports a plain base-station setup, the ACRDA
(SIC) receiver, and satellite / HAPS / terrestrial gateways with per-gateway
fading and erasure.

## Installation

Download the source code and extract it to a folder. Open a terminal in that
folder and install the prerequisite libraries:

```sh
pip install -r requirements.txt
```

Then install the library itself:

```sh
pip install .
```

To make changes to the library during development, install it editable so edits
to the source apply immediately:

```sh
pip install -e .
```

Python 3.10 or newer is required (the code uses `match` statements).

## Package layout

| Module | Contents |
|---|---|
| `lrfhss/lrfhss_core.py` | Core classes: `Fragment`, `Packet`, `Traffic`, `Node`, `Node_Distribution`, `Gateway_Distribution`, `Base`, `SimulationStats`. The simulation machinery lives here. |
| `lrfhss/settings.py` | `Settings` — the network "config file": physical/traffic parameters and network-layout parameters (gateways, antenna gains, radii, HAPS altitude), every one with a default. |
| `lrfhss/traffic.py` | Traffic generators: `Exponential_Traffic`, `Uniform_Traffic`, `Constant_Traffic`, `Two_State_Markovian_Traffic`. |
| `lrfhss/acrda.py` | `BaseACRDA` — base station with a sliding-window SIC decoder. |
| `lrfhss/fading.py` | Fading models (`Rayleigh_Fading`, `Rician_Fading`, `Nakagami_M_Fading`, `No_Fading`, `Abdi_Gamma`, `LogShadow`) and the fading-aware `FadingNode` / `FadingBase`. |
| `lrfhss/node_distribution.py` | `Uniform_Circle_Distribution` — places nodes uniformly in a circle. |
| `lrfhss/gateway_distribution.py` | `Fixed_Gateway` (static point in 3D), `Satellite_Gateway` (LEO orbit with coverage windows, elevation/azimuth vs. time), and `terrestrial_gate_positions` (hard-core placement of the fixed LoRa gates). |
| `lrfhss/run.py` | Example scenario runner: builds the network, runs it, and returns the results. |

## Usage

`lrfhss/run.py` is an example of a full scenario setup. It builds a network with
a given number of devices, runs it for a given time, and returns the results.
For a notebook walkthrough, see `examples/examples.ipynb` and
`examples/example_traffic.ipynb`.

The minimal usage is:

```python
from lrfhss.settings import Settings
from lrfhss.run import run_sim

s = Settings(number_nodes=1000)     # base='core' by default
results = run_sim(s)
# np.mean over repeated runs gives [success_ratio, goodput, transmitted]
```

`run_sim` keeps the historical return contract used by the example notebooks:

```python
import numpy as np
results = run_sim(s)                # [[success_ratio], [goodput], [transmitted]]
np.mean(results, 0)                 # -> [success_ratio, goodput, transmitted]
```

For anything beyond the aggregate numbers (per-node CDFs, erasure maps, ...),
use `run_sim_full`, which returns the `(stats, nodes)` pair:

```python
from lrfhss.run import run_sim_full
stats, nodes = run_sim_full(s)
stats.summary()
```

### Scenarios

The scenario type is selected by the `base` string in `Settings`:

| `base` | Gateway | Fading |
|---|---|---|
| `core` (default) | single base station at the origin | none |
| `acrda` | single ACRDA (SIC) base station | none |
| `satellite` | LEO satellite (750 km) + optional LoRa gates | Abdi-Gamma + log-shadowing |
| `haps` | HAPS at `haps_altitude` + optional LoRa gates | Abdi-Gamma + log-shadowing |
| `rayleigh` | `number_gateways` terrestrial LoRa gates | log-shadowing |

Everything else is a knob in `Settings` (all optional, defaulted), not a
separate scenario:

| `Settings` parameter | Meaning | Default |
|---|---|---|
| `gateway_antenna_gain` | dBi, gain of the satellite/HAPS gateway antenna | `0` |
| `node_antenna_gain` | dBi, gain of each device antenna | `0` |
| `number_gateways` | fixed terrestrial LoRa gates added to the scenario | `0` |
| `terrestrial_gate_gain` | dBi, gain of those fixed LoRa gates | `6` |
| `node_radius` | m, radius of the devices' circular area | `80000` |
| `coverage_radius` | m, a ground LoRa gate is only reachable within this range | `25000` |
| `haps_altitude` | m, HAPS altitude for the `haps` scenario | `30000` |

For example, a LEO satellite with a 13.5 dBi dish plus 10 nearby LoRa gates is
just `Settings(base='satellite', gateway_antenna_gain=13.5, number_gateways=10)`
— no new branch needed.

### Adding a new scenario

A scenario is just a branch in `_build_network` in `lrfhss/run.py`. To add one:

1. Pick a gateway from `gateway_distribution.py` (or write a new one that
   subclasses `Gateway_Distribution`).
2. Pick a fading model from `fading.py`.
3. Add an `elif settings.base == 'your_scenario':` branch that wires up the
   bases and nodes, mirroring the existing ones.

Nothing in the core package needs to change.

Plots in the example notebooks are made with the
[SciencePlots](https://github.com/garrettj403/SciencePlots) library.

## License

GPL-3.0 — see [LICENSE](LICENSE).
