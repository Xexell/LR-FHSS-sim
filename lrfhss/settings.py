import numpy as np
import warnings
from lrfhss.traffic import *
import inspect


class Settings():
    def __init__(self, number_nodes=80000//8, simulation_time=60*60, payload_size = 10, headers = 3, header_duration = 0.233472, payloads = None, threshold = None, payload_duration = 0.1024,
                 code = '1/3', traffic_func = exponential_traffic, traffic_param = {'average_interval': 900}, transceiver_wait = 0.006472, obw = 35, base='core', window_size = 2, window_step = 0.5):
        
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

        if inspect.isfunction(traffic_func):
            self.traffic_func = traffic_func
            self.traffic_param = traffic_param
            match traffic_func.__name__:
                case 'exponential_traffic':
                    if not 'average_interval' in self.traffic_param:
                        warnings.warn(f'traffic_param average_interval key missing for exponential_traffic. Using average_interval=900 as default')
                        self.traffic_param['average_interval'] = 900
                case 'uniform_traffic':
                    if not 'max_interval' in self.traffic_param:
                        warnings.warn(f'traffic_param max_interval key missing for uniform_traffic. Using max_interval=1800 as default')
                        self.traffic_param['max_interval'] = 1800
                case 'constant_traffic':
                    if not 'constant_interval' in self.traffic_param:
                        warnings.warn(f'traffic_param constant_interval key missing for constant_traffic. Using constant_interval=900 as default')
                        self.traffic_param['constant_interval'] = 900

                    if not 'standard_deviation' in self.traffic_param:
                        warnings.warn(f'traffic_param standard_deviation key missing for constant_traffic. Using standard_deviation=900 as default')
                        self.traffic_param['standard_deviation'] = 10
                case 'two_state_markovian_traffic':
                    if not 'transition_matrix' in self.traffic_param:
                        warnings.warn(f'traffic_param transition_matrix key missing for two_state_markovian_traffic. Using transition_matrix=[0.5, 0.5; 0.5, 0.5] as default')
                        self.traffic_param['transition_matrix'] = [[0.5, 0.5],[0.5, 0.5]]
                    if not 'markov_time' in self.traffic_param:
                        warnings.warn(f'traffic_param markov_time key missing for two_state_markovian_traffic. Using markov_time=0.5 as default')
                        self.traffic_param['markov_time'] = 0.5
                case _:
                    warnings.warn(f'Using an unpredicted (not listed in settings.py) traffic function.')

        else:
            warnings.warn(f'traffic_func should be a function. Using exponential_traffic with average_interval=900 as default.')