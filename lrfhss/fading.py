import copy
from abc import ABC, abstractmethod
import warnings

import numpy as np
from scipy.stats import rayleigh, rice, nakagami

from lrfhss.lrfhss_core import Node, Base, Packet

# Fading models classes
class Fading(ABC):
    @abstractmethod
    def __init__(self, fading_param):
        self.fading_param = fading_param

    @abstractmethod
    def fading_function(self, **kwargs):
        pass


## Rayleigh fading
class Rayleigh_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'scale' in self.fading_param:
            warnings.warn(f'fading_param scale key missing for Rayleigh_Fading. Using with scale=1 as default')
            self.fading_param['scale'] = 1.0

    def fading_function(self, **kwargs):
        scale = self.fading_param['scale']
        return rayleigh.rvs(scale=scale)

## Rician fading
class Rician_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'k' in self.fading_param:
            warnings.warn(f'fading_param k key missing for Rician_Fading. Using with k=3 as default')
            self.fading_param['k'] = 3

    def fading_function(self, **kwargs):
        K = self.fading_param['k']
        return rice.rvs(np.sqrt(2*K), scale= 1/np.sqrt(2*(K+1)))

## Nakagami-m fading
class Nakagami_M_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'm' in self.fading_param:
            warnings.warn(f'fading_param m key missing for Nakagami_M_Fading. Using with m=1 as default')
            self.fading_param['m'] = 1.0 # para m=1, equivale ao Rayleigh
        if not 'omega' in self.fading_param:
            warnings.warn('Fading parameter "omega" missing for Nakagami_M_Fading. Using omega=1 as default')
            self.fading_param['omega'] = 1.0  # Energia média do sinal

    def fading_function(self, **kwargs):
        m = self.fading_param['m']
        omega = self.fading_param['omega']
        return nakagami.rvs(m, scale=omega)

## No fading
class No_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)

    def fading_function(self, **kwargs):
        return 1

## Empirical/Statistical fading model from https://ieeexplore.ieee.org/document/1198102
## Approximated as a Gamma, as in https://ieeexplore.ieee.org/document/10463093
## The polynomial approximations of b0, m and omega are only valid for
## elevation angles between 20 and 90 degrees; outside that range the angle
## is clamped to the nearest bound (with a warning).
class Abdi_Gamma(Fading):
    VALID_RANGE = (20, 90)

    def __init__(self, fading_param):
        super().__init__(fading_param)

    def fading_function(self, **kwargs):
        # Get elevation angle from kwargs, defaulting to 90 degrees if not provided
        elevation_angle = self._clamp_elevation(kwargs.get('elevation_angle', 90))
        b0 = self.b0_theta(elevation_angle)
        m = self.m_theta(elevation_angle)
        Omega = self.omega_theta(elevation_angle)

        # Equation (23) from the paper
        alpha_s = m * (2 * b0 + Omega)**2 / (4 * m * b0**2 + 4 * m * b0 * Omega + Omega**2)
        beta_s = (4 * m * b0**2 + 4 * m * b0 * Omega + Omega**2) / (m * (2 * b0 + Omega))
        # numpy uses shape (alpha), and scale (beta)
        return float(np.random.gamma(shape=alpha_s, scale=beta_s))

    def _clamp_elevation(self, theta):
        lo, hi = self.VALID_RANGE
        if not (lo <= theta <= hi):
            warnings.warn(f'Abdi_Gamma: elevation angle {theta:.1f} deg outside valid range [{lo}, {hi}]; clamping to nearest bound.')
            theta = min(max(theta, lo), hi)
        return theta

    # Coefficients for the polynomial approximations of b0, m, and omega as functions of theta
    def b0_theta(self, theta):
        return -(4.7943e-8)*theta**3 +  (5.5784e-6)*theta**2 - (2.1344e-4)*theta + 3.2710e-2

    def m_theta(self, theta):
        return (6.3739e-5)*theta**3 + (5.8533e-4)*theta**2 - (1.5973e-1)*theta + 3.5156

    def omega_theta(self, theta):
        return (1.4428e-5)*theta**3 - (2.3798e-3)*theta**2 + (1.2702e-1)*theta - 1.4864

## Log-shadowing fading model for LoRa terrestrial links, with parameters from
## https://ieeexplore.ieee.org/document/7377400
## Log-distance path loss: Lpl(d) = Lpl(d0) + 10*gamma*log10(d/d0) + X_sigma
## This model only returns the log-normal shadowing term X_sigma ~ N(0, std);
## the distance-dependent path loss is applied in
## FadingBase.calculate_received_power, where the distance is known.
class LogShadow(Fading):

    def __init__(self, fading_param):

        fading_param["gamma"] = fading_param.get("gamma", 2.5)
        fading_param["d0"] = fading_param.get("d0", 1000)
        fading_param["std"] = fading_param.get("std", 7.8)
        fading_param["Lpld0"] = fading_param.get("Lpld0", 128.95)
        fading_param["GL"] = fading_param.get("GL", 0)
        super().__init__(fading_param)

    def fading_function(self, **kwargs):
        return np.random.normal(0, self.fading_param["std"])



# Node and gateway modules with fading
class FadingNode(Node):
    def __init__(self, obw, headers, payloads, header_duration, payload_duration, transceiver_wait, traffic_generator,position_generator,antenna_gain = 0,stats=None):
        super().__init__(obw, headers, payloads, header_duration, payload_duration, transceiver_wait, traffic_generator, stats)
        self.tx = 14 #transmit power in dBm
        self.G_t = antenna_gain # gain of the antenna in dBi
        self.sensitivity = -132 # dBm, can be parameterized later
        self.x, self.y, self.z = position_generator.node_distribution_function()  # Get position from the distribution function
        self.total_fragments_erased = 0
    def transmit(self, env, bs):
        if not isinstance(bs, list):
            bs_list = [bs]
        else:
            bs_list = bs
        while 1:
            #time between transmissions
            yield env.timeout(self.next_transmission())
            self.transmitted += 1
            self.stats.register_transmission(self.id) if self.stats else None

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
                    frag_copy.received_power = base.calculate_received_power(self)
                    self.stats.register_fragment_transmission(self.id) if self.stats else None
                    if frag_copy.received_power > self.sensitivity:
                        frag_copy.erased = 0
                        base.check_collision(frag_copy)
                        base.receive_packet(frag_copy)
                    else:
                        frag_copy.erased = 1
                        self.stats.register_erased(self.id) if self.stats else None


                #wait the duration (time on air) of the fragment
                yield env.timeout(orig_fragment.duration)

                for base in bs_list:
                    frag_copy = packet_copies[base].fragments[next_fragment_idx]
                    base.finish_fragment(frag_copy)
                    if packet_copies[base].success == 0:
                        base.try_decode(packet_copies[base],env.now)
                # If any fragment copy was successful, mark the original fragment as successful, mostly for statistics
                # For detailed base statistics, we should implement a check and statistics update for each base
                self.packet.fragments[next_fragment_idx].success = 1 if any(frag_copy.success == 1 for frag_copy in [packet_copies[base].fragments[next_fragment_idx] for base in bs_list]) else 0
                self.packet.fragments[next_fragment_idx].erased = 0 if any(frag_copy.erased == 0 for frag_copy in [packet_copies[base].fragments[next_fragment_idx] for base in bs_list]) else 1
                self.packet.fragments[next_fragment_idx].transmitted = 1
                next_fragment_idx += 1
            # After all fragments are processed, check if any base successfully received the packet
            self.packet.success = int(any(p_copy.success == 1 for p_copy in packet_copies.values()))
            if self.packet.success == 1:
                self.stats.register_success(self.id) if self.stats else None
            self.end_of_transmission()


    def end_of_transmission(self):

        for fragment in self.packet.fragments:
            if fragment.success == 1:
                self.total_fragments_success += 1
            if fragment.transmitted == 1:
                self.total_fragments_transmitted += 1
            if fragment.erased == 1:
                self.total_fragments_erased += 1
            if fragment.erased == 1 and fragment.success == 1:
                warnings.warn(f'Fragment {fragment.id} was erased but marked as successful. This should not happen.')
        self.packet = Packet(self.id, self.obw, self.headers, self.payloads, self.header_duration, self.payload_duration)

class FadingBase(Base):
    def __init__(self, obw, threshold, base_position, antenna_gain, stats=None, fading_model=No_Fading({})):
        super().__init__(obw, threshold, base_position, stats)
        self.fading_model = fading_model
        self.G_r = antenna_gain  # Antenna gain in dBi
        self.sensitivity = -132 # dBm, can be parameterized later

    def calculate_received_power(self, node):
        distance = self.base_position.get_distance(node.x, node.y, node.z)
        if isinstance(self.fading_model, LogShadow):
            # Log-distance model for the terrestrial LoRa link:
            # P_rx = P_tx + G_t + G_r - Lpl(d0) - 10*gamma*log10(d/d0) - GL + X_sigma
            # (fading_function returns only the log-normal shadowing X_sigma)
            fading = self.fading_model.fading_function()
            p = self.fading_model.fading_param
            return (node.tx + node.G_t + self.G_r
                    - p['Lpld0'] + fading
                    - 10 * p['gamma'] * np.log10(distance / p['d0'])
                    - p['GL'])
        # Free-space path loss plus multiplicative fading (satellite/HAPS links)
        lamb = 3e8 / (868e6)  # wavelength in meters for 868 MHz
        elevation_angle = 90  # Default elevation angle in degrees
        # If the base position has a method to get elevation, use it
        if hasattr(self.base_position, "get_elevation"):
            elevation_angle = self.base_position.get_elevation(node.x, node.y, node.z)
        fading = self.fading_model.fading_function(elevation_angle=elevation_angle)
        path_gain = 20*np.log10(lamb / (4 * np.pi * distance))  # Path loss in dB (negative)
        return node.tx + node.G_t + self.G_r + path_gain + 20*np.log10(fading)  # Received power in dBm

    def finish_fragment(self, fragment):
        if fragment in self.transmitting[fragment.channel]:
            self.transmitting[fragment.channel].remove(fragment)
        if len(fragment.collided) == 0 and fragment.erased == 0:
            fragment.success = 1
        fragment.transmitted = 1

    def try_decode(self,packet,now):
        h_success = sum( ((len(f.collided)==0) and f.transmitted==1 and f.erased == 0) if (f.type=='header') else 0 for f in packet.fragments)
        p_success = sum( ((len(f.collided)==0) and f.transmitted==1 and f.erased == 0) if (f.type=='payload') else 0 for f in packet.fragments)
        success = 1 if ((h_success>0) and (p_success >= self.threshold)) else 0
        if success == 1:
            self.packets_received[packet.node_id] += 1
            packet.success = 1
            return True
        else:
            return False
