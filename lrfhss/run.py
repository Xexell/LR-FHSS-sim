from lrfhss.lrfhss_core import *
from lrfhss.acrda import BaseACRDA
from lrfhss.settings import Settings
import simpy

def run_sim(settings: Settings, seed=0):
    random.seed(seed)
    np.random.seed(seed)
    env = simpy.Environment()
    if settings.base=='acrda':
        bs = BaseACRDA(settings.obw, settings.window_size, settings.window_step, settings.time_on_air, settings.threshold)
        env.process(bs.sic_window(env))
    else:
        bs = Base(settings.obw, settings.threshold)
    
    nodes = []
    for i in range(settings.number_nodes):
        node = Node(settings.average_interval, settings.obw, settings.headers, settings.payloads, settings.header_duration, settings.payload_duration)
        bs.add_node(node.id)
        nodes.append(node)
        env.process(transmit(env, bs, node, settings.transceiver_wait))
    # start simulation
    env.run(until=settings.simulation_time)

    # after simulation
    success = sum(bs.packets_received.values())
    transmitted = sum(n.transmitted for n in nodes) 
    if transmitted == 0: #If no transmissions are made, we consider 100% success as there were no outages
        return 1
    else:
        return [[success/transmitted], [success*settings.payload_size]]

if __name__ == "__main__":
   s = Settings()
   print(run_sim(s))