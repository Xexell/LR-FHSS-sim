import numpy as np
import warnings
from lrfhss.traffic import *
import inspect


class Settings():
    def __init__(self, number_nodes=80000//8, simulation_time=60*60, payload_size = 10, headers = 3, header_duration = 0.233472, payloads = None, threshold = None, payload_duration = 0.1024,
                 code = '1/3', traffic_class = Exponential_Traffic, traffic_param = {'average_interval': 900}, transceiver_wait = 0.006472, obw = 35, base='core', window_size = 2, window_step = 0.5):
        
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
