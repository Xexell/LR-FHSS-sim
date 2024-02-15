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
    

def two_state_markovian_traffic(self):
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