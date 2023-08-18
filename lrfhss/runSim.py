from lrfhss.LRFHSS_ALOHA import *
import simpy
import warnings

class Settings():
    def __init__(self, number_nodes=80000//8, simulation_time=60*60, payload_size = 10, headers = 3, header_duration = 0.233472, payloads = None, threshold = None, payload_duration = 0.1024,
                 code = '1/3', average_interval = 900, transceiver_wait = 0.006472, obw = 35, sic=False, window_size = 2, window_step = 0.5):
        
        self.number_nodes = number_nodes
        self.simulation_time = simulation_time
        self.payload_size = payload_size
        self.headers = headers
        self.header_duration = header_duration
        self.payload_duration = payload_duration
        self.transceiver_wait = transceiver_wait
        self.average_interval = average_interval
        self.obw = obw
        self.sic = sic
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