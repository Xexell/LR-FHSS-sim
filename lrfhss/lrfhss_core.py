import random
import numpy as np
import copy
from abc import ABC, abstractmethod

        
class Fragment():
    def __init__(self, type, duration, channel, packet):
        self.packet = packet
        self.duration = duration
        self.success = 0
        self.transmitted = 0
        self.type = type
        self.channel = channel
        self.timestamp = 0
        self.id = id(self)
        self.collided = []

class Packet():
    def __init__(self, node_id, obw, headers, payloads, header_duration, payload_duration):
        self.id = id(self)
        self.node_id = node_id
        self.index_transmission = 0
        self.success = 0
        self.channels = random.choices(range(obw), k=headers+payloads)
        self.fragments = []
        for h in range(headers):
            self.fragments.append(Fragment('header',header_duration, self.channels[h], self.id))
        for p in range(payloads):
            self.fragments.append(Fragment('payload',payload_duration, self.channels[p+h+1], self.id))

    def next(self):
        self.index_transmission+=1
        try:
            return self.fragments[self.index_transmission-1]
        except:
            return False
        
# Instead of grid selection, we consider one grid of obw (usually 35 for EU) channels, as it is faster to simulate and extrapolate the number.
# Later we can implement the grid selection in case of interest of studying it.
#    def new_channels(self, obw, fragments):
#        self.channels = random.sample(range(obw), fragments)


class Traffic(ABC):
    @abstractmethod
    def __init__(self, traffic_param):
        self.traffic_param = traffic_param

    @abstractmethod
    def traffic_function(self):
        pass


class Node_Distribution(ABC):
    @abstractmethod
    def __init__(self, node_distribution_param):
        self.node_distribution_param = node_distribution_param

    @abstractmethod
    def node_distribution_function(self):
        pass

class Gateway_Distribution(ABC):
    @abstractmethod
    def __init__(self, gateway_distribution_param):
        self.gateway_distribution_param = gateway_distribution_param

    @abstractmethod
    def gateway_distribution_function(self):
        pass

    @abstractmethod
    def get_distance(self):
        pass

class Node():
    def __init__(self, obw, headers, payloads, header_duration, payload_duration, transceiver_wait, traffic_generator):
        self.id = id(self)
        self.transmitted = 0
        self.traffic_generator = traffic_generator
        self.transceiver_wait = transceiver_wait
        # Packet info that Node has to store
        self.obw = obw
        self.headers = headers
        self.payloads = payloads
        self.header_duration = header_duration
        self.payload_duration = payload_duration
        self.total_fragments_transmitted = 0
        self.total_fragments_success = 0
        self.packet = Packet(self.id, self.obw, self.headers, self.payloads, self.header_duration, self.payload_duration)

    def next_transmission(self):
        return self.traffic_generator.traffic_function()

    def end_of_transmission(self):
        for fragment in self.packet.fragments:
            if fragment.success == 1:
                self.total_fragments_success += 1
            if fragment.transmitted == 1:
                self.total_fragments_transmitted += 1
        self.packet = Packet(self.id, self.obw, self.headers, self.payloads, self.header_duration, self.payload_duration)

    def transmit(self, env, bs):
        if not isinstance(bs, list):
            bs_list = [bs]
        else:
            bs_list = bs
        while 1:
            #time between transmissions
            yield env.timeout(self.next_transmission())
            self.transmitted += 1
            packet_copies = {base: copy.deepcopy(self.packet) for base in bs_list}
            for base in bs_list:
                base.add_packet(packet_copies[base])

        next_fragment_idx = 0
        first_payload = 0
        while True:
            # Get the next fragment index (same for all bases)
            try:
                orig_fragment = self.packet.fragments[next_fragment_idx]
            except IndexError:
                break

            if first_payload == 0 and orig_fragment.type == 'payload':
                first_payload = 1
                yield env.timeout(self.transceiver_wait)

            # For each base, process its own fragment copy
            for base in bs_list:
                frag_copy = packet_copies[base].fragments[next_fragment_idx]
                frag_copy.timestamp = env.now
                base.check_collision(frag_copy)
                base.receive_packet(frag_copy)

            yield env.timeout(orig_fragment.duration)

            for base in bs_list:
                frag_copy = packet_copies[base].fragments[next_fragment_idx]
                base.finish_fragment(frag_copy)
                if packet_copies[base].success == 0:
                    base.try_decode(packet_copies[base], env.now)

            next_fragment_idx += 1
        packet_success = any(p_copy.success == 1 for p_copy in packet_copies.values())
        self.packet.success = 1 if packet_success else 0

        self.end_of_transmission()
class Base():
    def __init__(self, obw, threshold, base_position=None):
        self.id = id(self)
        self.transmitting = {}
        for channel in range(obw):
            self.transmitting[channel] = []
        self.packets_received = {}
        self.threshold = threshold
        self.base_position = base_position

    def add_packet(self, packet):
        pass

    def add_node(self, id):
        self.packets_received[id] = 0

    def receive_packet(self, fragment):
        self.transmitting[fragment.channel].append(fragment)

    def finish_fragment(self, fragment):
        if fragment in self.transmitting[fragment.channel]:
            self.transmitting[fragment.channel].remove(fragment)
        if len(fragment.collided) == 0:
            fragment.success = 1
        fragment.transmitted = 1

    def check_collision(self,fragment):
        for f in self.transmitting[fragment.channel]:
            f.collided.append(fragment)
            fragment.collided.append(f)

    def try_decode(self,packet,now):
        h_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='header') else 0 for f in packet.fragments)
        p_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='payload') else 0 for f in packet.fragments)
        success = 1 if ((h_success>0) and (p_success >= self.threshold)) else 0
        if success == 1:
            self.packets_received[packet.node_id] += 1
            packet.success = 1
            return True
        else:
            return False
