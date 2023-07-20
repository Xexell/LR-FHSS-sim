from LRFHSS_ALOHA import *
from joblib import Parallel, delayed
import simpy
import pandas as pd
import time

#Default variables
nNodes = 500
simTime = 60*60
seed = 1

def run_sim(nNodes = nNodes, simTime = simTime, seed = seed):
    random.seed(seed)
    np.random.seed(seed)
    bs = Base()
    env = simpy.Environment()
    nodes = []

    for i in range(0,nNodes):
        node = Node()
        nodes.append(node)
        env.process(transmit(env,bs,node))

    # start simulation
    env.run(until=simTime)

    success = sum(n.successes for n in nodes)

    transmitted = sum(n.transmitted for n in nodes) 

    return success/transmitted

if __name__ == "__main__":
   run_sim()