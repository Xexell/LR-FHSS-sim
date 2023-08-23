from lrfhss.lrfhss_core import *
import simpy

def run_sim(settings: Settings, seed=0):
    random.seed(seed)
    np.random.seed(seed)
    bs = Base(settings.obw, settings.sic, settings.window_size, settings.window_step, settings.time_on_air, settings.threshold)
    env = simpy.Environment()
    nodes = []

    for i in range(settings.number_nodes):
        node = Node(settings.average_interval, settings.obw, settings.headers, settings.payloads, settings.header_duration, settings.payload_duration)
        bs.add_node(node.id)
        nodes.append(node)
        env.process(transmit(env, bs, node, settings.sic, settings.transceiver_wait))
    if settings.sic:
        env.process(bs.sic_window(env))
    # start simulation
    env.run(until=settings.simulation_time)

    success = sum(bs.packets_received.values())

    transmitted = sum(n.transmitted for n in nodes) 

    return success/transmitted

if __name__ == "__main__":
   s = Settings()
   print(run_sim(s))