import random
from lrfhss.lrfhss_core import Traffic
import warnings

## Exponential traffic
class Exponential_Traffic(Traffic):
    def __init__(self, traffic_param):
        super().__init__(traffic_param)
        if not 'average_interval' in self.traffic_param:
            warnings.warn(f'traffic_param average_interval key missing for exponential_traffic. Using with average_interval=900 as default')
            self.traffic_param['average_interval'] = 900

    def traffic_function(self):
        return random.expovariate(1/self.traffic_param['average_interval'])

## Uniform traffic
class Uniform_Traffic(Traffic):
    def __init__(self, traffic_param):
        super().__init__(traffic_param)
        if not 'max_interval' in self.traffic_param:
            warnings.warn(f'traffic_param max_interval key missing for uniform_traffic. Using with max_interval=1800 as default')
            self.traffic_param['max_interval'] = 1800

    def traffic_function(self):
        return random.uniform(0,self.traffic_param['max_interval'])

## Constant traffic with small gaussian deviation
class Constant_Traffic(Traffic):
    def __init__(self, traffic_param):
        super().__init__(traffic_param)
        if not 'constant_interval' in self.traffic_param:
            warnings.warn(f'traffic_param constant_interval key missing for constant_traffic. Using with constant_interval=900 as default')
            self.traffic_param['constant_interval'] = 900

        if not 'standard_deviation' in self.traffic_param:
            warnings.warn(f'traffic_param standard_deviation key missing for constant_traffic. Using with standard_deviation=900 as default')
            self.traffic_param['standard_deviation'] = 10

    def traffic_function(self):
        # First transmissions is random, devices are not initiated at the same time
        if self.transmitted == 0:
            return random.uniform(0,2*self.traffic_param['constant_interval'])
        else:
            return max(0, self.traffic_param['constant_interval'] + random.gauss(0,self.traffic_param['standard_deviation']))
    

## 2-state Markovian Traffic
class Markovian_Traffic(Traffic):
    def __init__(self, traffic_param):
        super().__init__(traffic_param)
        if not 'transition_matrix' in self.traffic_param:
            warnings.warn(f'traffic_param transition_matrix key missing for markovian_traffic. Using with standard_deviation=900 as default')
            self.traffic_param['standard_deviation'] = 10
        
        if not 'markov_time' in self.traffic_param:
            w

    def traffic_function(self):
        discrete_time = 1
        try:
            state = self.state
        except AttributeError:
            state = 0

        if random.random() >= self.traffic_param['transition_matrix'][state][0]:
            return max(0,discrete_time * self.traffic_param['markov_time'] + random.gauss(0,1))

        discrete_time+=1
        transition_probability = self.traffic_param['transition_matrix'][0][0]
        while random.random() < transition_probability:
            discrete_time+=1
        
        self.state=1
        return max(0,discrete_time * self.traffic_param['markov_time'] + random.gauss(0,1))