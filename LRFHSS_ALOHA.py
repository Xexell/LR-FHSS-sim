import random
import numpy as np

#These are the overall network parameters. In this early version, we will use the as global variables to avoid too many input parameters.
#Later we can move the most important outside the code, to facilitate changing it without opening the source code.

PAYLOAD_SIZE = 10
#Values from Regional Parameters document: https://resources.lora-alliance.org/technical-specifications/rp2-1-0-3-lorawan-regional-parameters
N_HEADERS = 3
L_HEADERS = 0.233472
N_PAYLOADS = 13
#N_PAYLOADS = int(np.ceil((PAYLOAD_SIZE+3)/2))
L_PAYLOADS = 0.050
#L_PAYLOADS = 0.1024
P_THRESHOLD = np.ceil(N_PAYLOADS/3).astype('int')
W_TRANSCEIVER = 0.006472 #Probably mentioned in some datasheet, I'm just trusting Asad on this at the moment.
TX_TOA = N_HEADERS*L_HEADERS + N_PAYLOADS*L_PAYLOADS + W_TRANSCEIVER #Transmission duration/Time-on-Air
AVG_INTERVAL = 900
N_OBW = 35 #There are 280 available, but they are divided into 8x35 channels. So, each transmission has 35 channels to hop. We use 35 to improve the simulation speed.
WINDOW_SIZE = 2  #SIC window size normalized by the transmission duration.
WINDOW_STEP = 0.25 #SIC window step normalized by the transmission duration.
#SIC_ENABLED = True

FRAGMENT_ID = 0 #global that tracks unique fragment id generation. Increments every fragment creation
PACKET_ID = 0 #global that tracks unique packet id generation. Increments every packet creation

class Fragment():
    def __init__(self, type, length, channel, packet):
        global FRAGMENT_ID
        self.packet = packet
        self.length = length
        self.success = 0
        self.transmitted = 0
        self.type = type
        self.channel = channel
        self.timestamp = 0
        self.id = FRAGMENT_ID
        FRAGMENT_ID += 1
        self.collided = []

class Packet():
    def __init__(self, node_id, n_headers=N_HEADERS, l_header=L_HEADERS, n_payloads=N_PAYLOADS, l_payloads=L_PAYLOADS):
        global PACKET_ID
        self.id = PACKET_ID
        PACKET_ID += 1
        self.node_id = node_id
        self.index_transmission = 0
        self.success = 0
        self.new_channels()
        self.fragments = []
        for headers in range(n_headers):
            self.fragments.append(Fragment('header',l_header, random.sample(self.channels,1)[0], self.id))
        for payloads in range(n_payloads):
            self.fragments.append(Fragment('payload',l_payloads, random.sample(self.channels,1)[0], self.id))

    def next(self):
        self.index_transmission+=1
        try:
            return self.fragments[self.index_transmission-1]
        except:
            return False
        
#    def check_success(self):
        
# Later, we will implement the grid selection on this function. Right now, it is selecting one out of 35 channels on a grid for each fragment.
    def new_channels(self):
        self.channels = random.sample(range(N_OBW), N_OBW)


class Node():
    def __init__(self, id):
        self.id = id
        self.transmitted = 0
        self.avg_interval = AVG_INTERVAL
        self.packet = Packet(self.id)


class Base():
    def __init__(self, nNodes, sic):
        self.transmitting = {}
        for channel in range(N_OBW):
            self.transmitting[channel] = []
        self.memory = {}
        self.window_size = WINDOW_SIZE*TX_TOA
        self.window_step = WINDOW_STEP*TX_TOA
        self.packets_received = {}
        for n in range(nNodes):
            self.packets_received[n] = 0 
        self.sic = sic

    def add(self, fragment):
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

    def try_decode(self,packet):
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


# This method will be moved to Base() class in future versions
    def end_of_transmission(self, node):
        node.packet = Packet(node.id)

    def sic_window(self, env):
        if not self.sic:
            raise SyntaxError('sic_window() can not be used with SIC_ENABLED flag as False')
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
                    if self.try_decode(p):
                        new_recover = True

            yield env.timeout(self.window_step)


    def in_window(self, fragment, now):
        return True if (now - fragment.timestamp)<=self.window_size else False


def transmit(env, bs, node, sic):
    SIC_ENABLED = sic
    while 1:
        #time between transmissions
        yield env.timeout(random.expovariate(1/node.avg_interval))
        node.transmitted += 1
        if SIC_ENABLED:
            bs.memory[node.packet.id] = node.packet
        next_fragment = node.packet.next()
        first_payload = 0
        while next_fragment:
            if first_payload == 0 and next_fragment.type=='payload': #account for the transceiver wait time between the last header and first payload fragment
                first_payload=1
                yield env.timeout(W_TRANSCEIVER)
            next_fragment.timestamp = env.now
            #checks if the fragment is colliding with the fragments in transmission now
            bs.check_collision(next_fragment)
            #add the fragment to the list of fragments being transmitted.
            bs.add(next_fragment)
            #wait the length (time on air) of the fragment
            yield env.timeout(next_fragment.length)
            #removes the fragment from the list.
            bs.remove(next_fragment)
            #check if base can decode the packet now.
            #tries to decode if not decoded yet.
            if node.packet.success == 0:
                bs.try_decode(node.packet)
            #select the next fragment
            next_fragment = node.packet.next()
        
        #end of transmission procedure
        bs.end_of_transmission(node)