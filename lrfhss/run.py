"""Example scenario runner for the LR-FHSS simulator.

This module is meant to be read and copied. It shows how to build a network
(one or more gateways plus the devices), run it for a given time and read the
results. The scenario is picked by ``settings.base``; all the tunables -- how
many gateways, antenna gains, device area, HAPS altitude -- live in
``Settings`` (see :class:`lrfhss.settings.Settings`), so adding a scenario is
just a new branch here, and changing a scenario is one ``Settings(...)`` call.

Scenarios
---------
  ``'core'``      one plain base station at the origin, no fading.
  ``'acrda'``     one ACRDA (SIC) base, no fading.
  ``'satellite'`` one LEO satellite (coverage-time windows) plus, optionally,
                  ``number_gateways`` terrestrial gateways.
  ``'haps'``      one HAPS at ``haps_altitude`` plus, optionally, terrestrial
                   gateways.
  ``'rayleigh'``  a pure terrestrial multi-gateway network
                  (``number_gateways`` gateways, log-shadowing links).

``run_sim`` keeps the original return contract used by the notebooks in
``examples/``::

    results = run_sim(settings)          # one run
    np.mean(results, 0)                  # -> [success_ratio, goodput, transmitted]

``run_sim_full`` additionally exposes the ``SimulationStats`` object and the
node list, for custom post-processing (per-node CDFs, erasure maps, ...).
"""
import random

import simpy

from lrfhss.lrfhss_core import Node, Base, SimulationStats
from lrfhss.acrda import BaseACRDA
from lrfhss.settings import Settings
from lrfhss.gateway_distribution import (
    Fixed_Gateway, Satellite_Gateway, terrestrial_gate_positions,
)
from lrfhss.fading import FadingNode, FadingBase, LogShadow, Abdi_Gamma
from lrfhss.node_distribution import Uniform_Circle_Distribution


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def make_node(settings, stats, fading=True):
    """One device, dropped uniformly in the devices' circular area.

    ``fading=True`` gives a :class:`FadingNode` (sits at a position and computes
    the received power); ``fading=False`` gives a plain :class:`Node` for the
    no-fading scenarios ('core', 'acrda').
    """
    common = (settings.obw, settings.headers, settings.payloads,
              settings.header_duration, settings.payload_duration,
              settings.transceiver_wait, settings.traffic_generator)
    if not fading:
        return Node(*common, stats=stats)

    #Only distribution implemented so far
    dist = Uniform_Circle_Distribution({'radius': settings.node_radius})
    return FadingNode(*common, dist,
                      antenna_gain=settings.node_antenna_gain, stats=stats)


def terrestrial_gateways(settings, stats, seed):
    """``settings.number_gateways`` fixed gateways spread over the area.

    Each gateway is a :class:`FadingBase` with a log-shadowing terrestrial link.
    Returns ``[]`` when ``number_gateways`` is 0, so satellite/HAPS scenarios
    can attach gateways optionally.
    """
    if settings.number_gateways <= 0:
        return []
    return [
        FadingBase(settings.obw, settings.threshold,
                   Fixed_Gateway({'x': x, 'y': y, 'z': 0}),
                   settings.terrestrial_gate_gain,
                   stats=stats, fading_model=LogShadow({}))
        for x, y in terrestrial_gate_positions(
            settings.number_gateways, radius=settings.node_radius, seed=seed)
    ]


def reachable_bases(node, bases, settings):
    """Which of ``bases`` can hear ``node``.

    A LEO satellite and a HAPS are always in range (line of sight to the sky);
    a fixed ground-level gateway is only reachable within
    ``settings.coverage_radius`` of the node. This is what makes a multi-gateway
    terrestrial network behave like "each node talks to its nearest gateways".
    """
    out = []
    for b in bases:
        pos = b.base_position
        ground_gate = (isinstance(pos, Fixed_Gateway)
                       and pos.gateway_distribution_param['z'] == 0)
        if (not ground_gate) or pos.get_distance(node.x, node.y, node.z) <= settings.coverage_radius:
            out.append(b)
    return out


# ---------------------------------------------------------------------------
# Network assembly
# ---------------------------------------------------------------------------
def _build_network(settings, seed):
    """Wire up env + bases + devices for the scenario named by ``settings.base``.

    Returns ``(env, nodes, stats)``. Only the scenario *type* is hard-coded
    here; every number (gateway count, gains, radii, HAPS altitude) is read from
    the ``Settings`` object, so a scenario is configured by the caller.
    """
    env = simpy.Environment()
    stats = SimulationStats()
    nodes = []

    # --- 1. the scenario's base station(s) --------------------------------
    if settings.base == 'acrda':
        # SIC receiver, no per-gateway fading: one base plus its cancellation loop.
        bases = [BaseACRDA(settings.obw, settings.window_size, settings.window_step,
                           settings.time_on_air, settings.threshold)]
        env.process(bases[0].sic_window(env))
        fading = False
    elif settings.base == 'satellite':
        # LEO satellite (windows from the coverage-time model) + optional gateways.
        sat = FadingBase(settings.obw, settings.threshold,
                         Satellite_Gateway({'env': env, 'sim_time': settings.simulation_time}),
                         settings.gateway_antenna_gain,
                         stats=stats, fading_model=Abdi_Gamma({}))
        bases = [sat] + terrestrial_gateways(settings, stats, seed)
        fading = True
    elif settings.base == 'haps':
        # High-altitude platform at a fixed altitude + optional gateways.
        haps = FadingBase(settings.obw, settings.threshold,
                          Fixed_Gateway({'z': settings.haps_altitude}),
                          settings.gateway_antenna_gain,
                          stats=stats, fading_model=Abdi_Gamma({}))
        bases = [haps] + terrestrial_gateways(settings, stats, seed)
        fading = True
    elif settings.base == 'rayleigh':
        # Pure terrestrial multi-gateway network (log-shadowing links).
        if settings.number_gateways < 1:
            raise ValueError("Scenario 'rayleigh' needs number_gateways >= 1, "
                             "e.g. Settings(base='rayleigh', number_gateways=10).")
        bases = terrestrial_gateways(settings, stats, seed)
        fading = True
    else:
        # Default ('core' or any unknown string): one plain base, no fading.
        bases = [Base(settings.obw, settings.threshold, stats=stats)]
        fading = False

    # --- 2. the devices: place each, attach it to its reachable bases, run it.
    for i in range(settings.number_nodes):
        node = make_node(settings, stats, fading=fading)
        # Plain nodes carry no position, so they are attached to every base.
        reach = bases if not fading else reachable_bases(node, bases, settings)
        for b in reach:
            b.add_node(node.id)
        nodes.append(node)
        env.process(node.transmit(env, reach))

    return env, nodes, stats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _legacy_results(stats, settings):
    """Legacy return value: ``[[success_ratio], [goodput], [transmitted]]``.

    ``goodput`` is the number of successfully received packets times the payload
    size, matching the original ``run_sim`` used by the example notebooks.
    """
    success = stats.total_success
    transmitted = stats.total_transmissions
    if transmitted == 0:
        # No transmissions: treat as 100% success (there were no outages).
        return 1
    goodput = success * settings.payload_size
    return [[success / transmitted], [goodput], [transmitted]]


def run_sim_full(settings: Settings, seed=0):
    """Run the simulation and return ``(stats, nodes)``.

    ``stats`` is a :class:`SimulationStats` (totals + per-node counters);
    ``nodes`` is the list of device objects. Use this when you need anything
    beyond the aggregate success/goodput numbers.
    """
    random.seed(seed)
    env, nodes, stats = _build_network(settings, seed)
    env.run(until=settings.simulation_time)
    return stats, nodes


def run_sim(settings: Settings, seed=0):
    """Run the simulation and return the legacy 3-row result.

    ``np.mean(results, 0)`` yields ``[success_ratio, goodput, transmitted]``.
    If no packet is transmitted the function returns the scalar ``1`` (100%
    success by convention).
    """
    stats, nodes = run_sim_full(settings, seed)
    return _legacy_results(stats, settings)


if __name__ == "__main__":
    s = Settings()
    print(run_sim(s))
