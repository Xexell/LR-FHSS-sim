from LRFHSS_ALOHA import *
import simpy

#Default variables
nNodes = 1000
simTime = 60*60
seed = 1
sic = False

def run_sim(nNodes = nNodes, simTime = simTime, seed = seed, sic=sic):
    random.seed(seed)
    np.random.seed(seed)
    bs = Base(nNodes,sic)
    env = simpy.Environment()
    nodes = []

    for i in range(nNodes):
        node = Node(i)
        nodes.append(node)
        env.process(transmit(env,bs,node,sic))
    if sic:
        env.process(bs.sic_window(env))
    # start simulation
    env.run(until=simTime)

    success = sum(bs.packets_received.values())

    transmitted = sum(n.transmitted for n in nodes) 

    return success/transmitted

if __name__ == "__main__":
   print(run_sim())