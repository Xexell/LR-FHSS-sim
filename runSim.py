from LRFHSS_ALOHA import *
import simpy

#Default variables
nNodes = 100000//8
simTime = 60*60
seed = 1

def run_sim(nNodes = nNodes, simTime = simTime, seed = seed):
    random.seed(seed)
    np.random.seed(seed)
    bs = Base(nNodes)
    env = simpy.Environment()
    nodes = []

    for i in range(nNodes):
        node = Node(i)
        nodes.append(node)
        env.process(transmit(env,bs,node))
    #env.process(bs.sic_window(env))
    # start simulation
    env.run(until=simTime)

    success = sum(bs.packets_received.values())

    transmitted = sum(n.transmitted for n in nodes) 

    return success/transmitted

if __name__ == "__main__":
   print(run_sim())