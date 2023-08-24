from lrfhss.lrfhss_core import Base

class BaseACRDA(Base):
    def __init__(self, obw, window_size, window_step, time_on_air, threshold):

        super().__init__(obw, threshold)
        self.memory = {}
        self.window_size = window_size*time_on_air
        self.window_step = window_step*time_on_air

    def add_packet(self, packet):
        self.memory[packet.id] = packet

    def try_decode(self,packet,now):
        for f in list(packet.fragments):
            if not self.in_window(f, now):
                packet.fragments.remove(f)
            else:
                break
        h_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='header') else 0 for f in packet.fragments)
        p_success = sum( ((len(f.collided)==0) and f.transmitted==1) if (f.type=='payload') else 0 for f in packet.fragments)
        success = 1 if ((h_success>0) and (p_success >= self.threshold)) else 0
        if success == 1:
            self.packets_received[packet.node_id] += 1
            packet.success = 1
            for f in packet.fragments:
                f.success = 1
                for c in list(f.collided):
                    f.collided.remove(c)
                    c.collided.remove(f)
            return True
        else:
            return False

    def sic_window(self, env):
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
            new_recover = True #variable to check if at least one packet was recovered the interference cancellation
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
