import random
import numpy as np

        
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
        self.channels = random.sample(range(obw), headers+payloads)
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
    def new_channels(self, obw, fragments):
        self.channels = random.sample(range(obw), fragments)


class Node():
    def __init__(self, average_interval, obw, headers, payloads, header_duration, payload_duration):
        self.id = id(self)
        self.transmitted = 0
        self.average_interval = average_interval

        # Packet info that Node has to store
        self.average_interval = average_interval
        self.obw = obw
        self.headers = headers
        self.payloads = payloads
        self.header_duration = header_duration
        self.payload_duration = payload_duration
        self.packet = Packet(self.id, self.obw, self.headers, self.payloads, self.header_duration, self.payload_duration)

    def end_of_transmission(self):
        self.packet = Packet(self.id, self.obw, self.headers, self.payloads, self.header_duration, self.payload_duration)


class Base():
    def __init__(self, obw, threshold):
        self.id = id(self)
        self.transmitting = {}
        for channel in range(obw):
            self.transmitting[channel] = []
        self.packets_received = {}
        self.header_failure = {}
        self.fragment_failure = {}
        self.threshold = threshold

    def add_packet(self, packet):
        pass

    def add_node(self, id):
        self.packets_received[id] = 0
        self.header_failure[id] = 0
        self.fragment_failure[id] = 0

    def receive_packet(self, fragment):
        self.transmitting[fragment.channel].append(fragment)

    def finish_fragment(self, fragment):
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
            self.header_failure[packet.node_id] += h_success<1
            self.fragment_failure[packet.node_id] += p_success<self.threshold
            return False



def transmit(env, bs, node, transceiver_wait):
    while 1:
        #time between transmissions
        yield env.timeout(random.expovariate(1/node.average_interval))
        node.transmitted += 1
        bs.add_packet(node.packet)
        next_fragment = node.packet.next()
        first_payload = 0
        while next_fragment:
            if first_payload == 0 and next_fragment.type=='payload': #account for the transceiver wait time between the last header and first payload fragment
                first_payload=1
                yield env.timeout(transceiver_wait)
            next_fragment.timestamp = env.now
            #checks if the fragment is colliding with the fragments in transmission now
            bs.check_collision(next_fragment)
            #add the fragment to the list of fragments being transmitted.
            bs.receive_packet(next_fragment)
            #wait the duration (time on air) of the fragment
            yield env.timeout(next_fragment.duration)
            #removes the fragment from the list.
            bs.finish_fragment(next_fragment)
            #check if base can decode the packet now.
            #tries to decode if not decoded yet.
            if node.packet.success == 0:
                bs.try_decode(node.packet,env.now)
            #select the next fragment
            next_fragment = node.packet.next()
        
        #end of transmission procedure
        node.end_of_transmission()