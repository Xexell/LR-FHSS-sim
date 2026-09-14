import numpy as np
import warnings
from lrfhss.traffic import *
import inspect


class Settings():
    """Network configuration for a simulation run.

    This is the "config file" of the simulator: every network parameter has a
    sensible default, so a run is ``Settings()`` plus whatever you want to
    override. Physical/traffic parameters (payload, headers, obw, traffic...)
    and network-layout parameters (``base``, gateways, antennas, radii) all
    live here; ``run.py`` only wires the chosen scenario to the core classes.

    Feel free to add your own parameters, which is specially useful when you
    want to change them over iterations outside the simulator. The simulator
    will ignore any extra parameters, but you can use them in your own scenario code.
    """

    def __init__(self, number_nodes=80000//8, simulation_time=60*60, payload_size = 10, headers = 3, header_duration = 0.233472, payloads = None, threshold = None, payload_duration = 0.1024,
                 code = '1/3', traffic_class = Exponential_Traffic, traffic_param = {'average_interval': 900}, transceiver_wait = 0.006472, obw = 35,
                 base='core', window_size = 2, window_step = 0.5, gateway_antenna_gain = 0,
                 node_antenna_gain = 0, number_gateways = 0, node_radius = 80_000,
                 coverage_radius = 25_000, haps_altitude = 30_000, terrestrial_gate_gain = 6):

        self.number_nodes = number_nodes
        self.simulation_time = simulation_time
        self.payload_size = payload_size
        self.headers = headers
        self.header_duration = header_duration
        self.payload_duration = payload_duration
        self.transceiver_wait = transceiver_wait
        self.obw = obw
        self.base = base
        self.window_size = window_size
        self.window_step = window_step
        self.gateway_antenna_gain = gateway_antenna_gain

        # --- network layout (all optional, defaulted) ---
        self.node_antenna_gain = node_antenna_gain    # dBi, gain of each device antenna
        self.number_gateways = number_gateways        # fixed terrestrial LoRa gates added to the scenario (0 = none)
        self.node_radius = node_radius                # m, radius of the devices' uniform circular distribution
        self.coverage_radius = coverage_radius        # m, node only reaches gates within this range
        self.haps_altitude = haps_altitude            # m, HAPS altitude for the 'haps' scenario
        self.terrestrial_gate_gain = terrestrial_gate_gain  # dBi, gain of the fixed terrestrial LoRa gates

        
        if payloads:
            self.payloads = payloads
        if threshold:
            self.threshold = threshold
        if not (payloads and threshold):
            match code:
                case '1/3':
                    if not payloads:
                        self.payloads = np.ceil((payload_size+3)/2).astype('int')
                    if not threshold:
                        self.threshold = np.ceil(self.payloads/3).astype('int')
                case '2/3':
                    if not payloads:
                        self.payloads = np.ceil((payload_size+3)/4).astype('int')
                    if not threshold:
                        self.threshold = np.ceil((2*self.payloads)/3).astype('int')
                case '5/6':
                    if not payloads:
                        self.payloads = np.ceil((payload_size+3)/5).astype('int')
                    if not threshold:
                        self.threshold = np.ceil((5*self.payloads)/6).astype('int')
                case '1/2':
                    if not payloads:
                        self.payloads = np.ceil((payload_size+3)/3).astype('int')
                    if not threshold:
                        self.threshold = np.ceil((self.payloads)/2).astype('int')
                case _:
                    warnings.warn(f'code = {code} is not a valid input. Using 1/3 instead.')
                    if not payloads:
                        self.payloads = np.ceil((payload_size+3)/2).astype('int')
                    if not threshold:
                        self.threshold = np.ceil(self.payloads/3).astype('int')
        
        self.time_on_air = self.header_duration*self.headers + self.payload_duration*self.payloads + self.transceiver_wait

        if not issubclass(traffic_class, Traffic):
            warnings.warn(f'Using an invalid traffic class.')
            exit(1)

        self.traffic_generator = traffic_class(traffic_param);
