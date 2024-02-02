import random

## Exponential traffic

def exponential_traffic(self):
    return random.expovariate(1/self.traffic_param['average_interval'])

## Uniform traffic

def uniform_traffic(self):
    return random.uniform(0,self.traffic_param['max_interval'])

## Constant traffic with small gaussian deviation

def constant_traffic(self):
    # First transmissions is random, devices are not initiated at the same time
    if self.transmitted == 0:
        return random.uniform(0,2*self.traffic_param['constant_interval'])
    else:
        return max(0, self.traffic_param['constant_interval'] + random.gauss(0,self.traffic_param['standard_deviation']))