import random
import numpy as np

#These are the overall network parameters. In this early version, we will use the as global variables to avoid too many input parameters.
#Later we can move the most important outside the code, to facilitate changing it without opening the source code.

PAYLOAD_SIZE = 10
#Values from Regional Parameters document: https://resources.lora-alliance.org/technical-specifications/rp2-1-0-3-lorawan-regional-parameters
N_HEADERS = 3
L_HEADERS = 0.233472
N_PAYLOADS = int(np.ceil((PAYLOAD_SIZE+3)/2))
L_PAYLOADS = 0.1024
P_THRESHOLD = np.ceil(N_PAYLOADS/3)
W_TRANSCEIVER = 0.006472 #Probably mentioned in some datasheet, I'm just trusting Asad on this at the moment.
AVG_INTERVAL = 900
N_OBW = 35 #There are 280 available, but they are divided into 8x35 channels. So, each transmission has 35 channels to hop. We use 35 to improve the simulation speed.
#WINDOW_SIZE = 5 # This is commented as, in this version, this information is not necessary 
#WINDOW_STEP = 0.5 # This is commented as, in this version, this information is not necessary



class Fragment():
    def __init__(self, type, length, channel):
        self.length = length
        self.success = 1
        self.type = type
        self.channel = channel
        self.timestamp = 0

class Packet():
    def __init__(self, n_headers=N_HEADERS, l_header=L_HEADERS, n_payloads=N_PAYLOADS, l_payloads=L_PAYLOADS):
        self.index_transmission = 0
        self.success = 0
        self.new_channels()
        self.fragments = []
        for headers in range(n_headers):
            self.fragments.append(Fragment('header',l_header, random.sample(self.channels,1)))
        for payloads in range(n_payloads):
            self.fragments.append(Fragment('payload',l_payloads, random.sample(self.channels,1)))

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
    def __init__(self):
        self.transmitted = 0
        self.successes = 0
        self.avg_interval = AVG_INTERVAL
        self.packet = Packet()

# This method will be moved to Base() class in future versions
    def end_of_transmission(self):
        self.transmitted += 1
        h_success = sum(f.success if (f.type=='header') else 0 for f in self.packet.fragments)
        p_success = sum(f.success if (f.type=='payload') else 0 for f in self.packet.fragments)
        self.successes += 1 if ((h_success>0) and (p_success >= P_THRESHOLD)) else 0
        self.packet = Packet()


class Base():
    def __init__(self):
        self.transmitting = []
    #    self.success = [] # This is commented as, in this version, this information is not necessary
    #    self.collided = [] # This is commented as, in this version, this information is not necessary
    #    self.window_size = WINDOW_SIZE # This is commented as, in this version, this information is not necessary
    #    self.window_step = WINDOW_STEP # This is commented as, in this version, this information is not necessary

    def add(self, fragment):
        self.transmitting.append(fragment)

    def remove(self, fragment):
        self.transmitting.remove(fragment)

    def check_collision(self,fragment):
        for f in self.transmitting:
            if f.channel == fragment.channel:
                f.success = 0
                fragment.success = 0



def transmit(env, bs, node):
    while 1:
        #time between transmissions
        yield env.timeout(random.expovariate(1/node.avg_interval))
        next_fragment = node.packet.next()
        #next_fragment.timestamp = env.now  #This is commented as, in this version, this information is not necessary
        first_payload = 0
        while next_fragment:
            if first_payload == 0 and next_fragment.type=='payload': #account for the transceiver wait time between the last header and first payload fragment
                first_payload=1
                yield env.timeout(W_TRANSCEIVER)
            #checks if the fragment is colliding with the fragments in transmission now
            bs.check_collision(next_fragment)
            #add the fragment to the list of fragments being transmitted.
            bs.add(next_fragment)
            #wait the length (time on air) of the fragment
            yield env.timeout(next_fragment.length)
            #removes the fragment from the list.
            bs.remove(next_fragment)
            #select the next fragment
            next_fragment = node.packet.next()
        
        #end of transmission procedure
        node.end_of_transmission()