import random
import numpy as np

PAYLOAD_SIZE = 10
#Values from Regional Parameters document: https://resources.lora-alliance.org/technical-specifications/rp2-1-0-3-lorawan-regional-parameters
N_HEADERS = 3
L_HEADERS = 0.233472
N_PAYLOADS = int(np.ceil((PAYLOAD_SIZE+3)/2))
L_PAYLOADS = 0.1024
P_THRESHOLD = np.ceil(N_PAYLOADS/3).astype('int')
W_TRANSCEIVER = 0.006472 #Probably mentioned in some datasheet, I'm just trusting Asad on this at the moment.
TX_TOA = N_HEADERS*L_HEADERS + N_PAYLOADS*L_PAYLOADS + W_TRANSCEIVER #Transmission duration/Time-on-Air
AVG_INTERVAL = 900
N_OBW = 35 #There are 280 available, but they are divided into 8x35 channels. So, each transmission has 35 channels to hop. We use 35 to improve the simulation speed.


        
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
        self.new_channels(obw, headers+payloads)
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
        
#    def check_success(self):
        
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
    def __init__(self, number_nodes, sic, window_size, window_step, time_on_air):
        self.id = id(self)
        self.transmitting = {}
        for channel in range(N_OBW):
            self.transmitting[channel] = []
        self.memory = {}
        self.window_size = window_size*time_on_air
        self.window_step = window_step*time_on_air
        self.packets_received = {}
        self.sic = sic

    def add_node(self, id):
        self.packets_received[id] = 0

    def add_fragment(self, fragment):
        self.transmitting[fragment.channel].append(fragment)

    def remove(self, fragment):
        self.transmitting[fragment.channel].remove(fragment)
        if len(fragment.collided) == 0:
            fragment.success = 1
        fragment.transmitted = 1

    def check_collision(self,fragment):
        for f in self.transmitting[fragment.channel]:
            f.collided.append(fragment)
            fragment.collided.append(f)

    def try_decode(self,packet,now):
        for f in list(packet.fragments):
            if not self.in_window(f, now):
                packet.fragments.remove(f)
            else:
                break
        h_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='header') else 0 for f in packet.fragments)
        p_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='payload') else 0 for f in packet.fragments)
        success = 1 if ((h_success>0) and (p_success >= P_THRESHOLD)) else 0
        if success == 1:
            self.packets_received[packet.node_id] += 1
            packet.success = 1
            if self.sic:
                for f in packet.fragments:
                    f.success = 1
                    for c in list(f.collided):
                        f.collided.remove(c)
                        c.collided.remove(f)
            return True
        else:
            return False

    def sic_window(self, env):
        if not self.sic:
            raise SyntaxError('sic_window() can not be used with sic flag as False')
        yield env.timeout(self.window_size)
        while(1):
            #FIRST: Remove fragments from memory that are outside the window.
            for p in list(self.memory):
                for f in list(self.memory[p].fragments):
                    if not self.in_window(f, env.now):
                        self.memory[p].fragments.remove(f)
                    else:
                        break
                if len(self.memory[p].fragments) == 0:
                    del(self.memory[p])
            
            #SECOND: Apply interference cancellation
            new_recover = True #variable to check if at least on packet was recovered due SIC
                       #if it did, we need to do the same procedure again until no new packet is recovered
            while(new_recover):
                failed_packets = (p for p in self.memory.values() if p.success == 0)
                new_recover = False
                for p in failed_packets:
                    if self.try_decode(p,env.now):
                        new_recover = True

            yield env.timeout(self.window_step)


    def in_window(self, fragment, now):
        return True if (now - fragment.timestamp)<=self.window_size else False


def transmit(env, bs, node, sic, transceiver_wait):
    while 1:
        #time between transmissions
        yield env.timeout(random.expovariate(1/node.average_interval))
        node.transmitted += 1
        if sic:
            bs.memory[node.packet.id] = node.packet
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
            bs.add_fragment(next_fragment)
            #wait the duration (time on air) of the fragment
            yield env.timeout(next_fragment.duration)
            #removes the fragment from the list.
            bs.remove(next_fragment)
            #check if base can decode the packet now.
            #tries to decode if not decoded yet.
            if node.packet.success == 0:
                bs.try_decode(node.packet,env.now)
            #select the next fragment
            next_fragment = node.packet.next()
        
        #end of transmission procedure
        node.end_of_transmission()