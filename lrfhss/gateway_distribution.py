from lrfhss.lrfhss_core import Gateway_Distribution
import warnings
import math
import random
import numpy as np

from astropy import constants as const
from scipy.stats import rv_continuous


## Fixed Gateway Distribution
# This distribution is used to place a single gateway at a fixed position in space.
class Fixed_Gateway(Gateway_Distribution):
    def __init__(self, gateway_param):
        super().__init__(gateway_param)
        if not 'x' in self.gateway_distribution_param:
            warnings.warn(f'gateway_distribution_param x key missing for Fixed_Gateway. Using x=0 as default')
            self.gateway_distribution_param['x'] = 0
        if not 'y' in self.gateway_distribution_param:
            warnings.warn(f'gateway_distribution_param y key missing for Fixed_Gateway. Using y=0 as default')
            self.gateway_distribution_param['y'] = 0
        if not 'z' in self.gateway_distribution_param:
            warnings.warn(f'gateway_distribution_param z key missing for Fixed_Gateway. Using z=0 as default')
            self.gateway_distribution_param['z'] = 0

    def gateway_distribution_function(self):
        return self.gateway_distribution_param['x'], self.gateway_distribution_param['y'], self.gateway_distribution_param['z']
    
    # This function is used to calculate the distance from the gateway to a given point in space (most likely another device in this context so far),
    # using the Euclidean distance formula.
    def get_distance(self, x, y, z):
        distance = np.sqrt((x - self.gateway_distribution_param['x'])**2 + (y - self.gateway_distribution_param['y'])**2 + (z - self.gateway_distribution_param['z'])**2)
        return distance if distance != 0 else 1e-6 # Avoid division by zero in the future
    

    def get_elevation(self, x=0, y=0, z=0):
        R_earth = const.R_earth.value    # ~6.3781e6 m
        # Convert altitudes (z) into position from Earth's center
        r_g = np.array([x, y, z + R_earth])
        r_e = np.array([self.gateway_distribution_param['x'], self.gateway_distribution_param['y'], self.gateway_distribution_param['z'] + R_earth])

        u = r_e - r_g  # vector from ground to target
        n = r_g / np.linalg.norm(r_g)  # local "up" unit vector at ground point

        dot = np.dot(u, n)
        norm_u = np.linalg.norm(u)

        angle_rad = np.arcsin(dot / norm_u)

        return np.degrees(angle_rad)



def terrestrial_gate_positions(
    n_gates,
    radius=80_000,          # m, the "evaluation circle" the devices are dropped in
    min_spacing=10_000,     # m, minimum center-to-center distance between gates
    seed=0,
):
    """Randomly place ``n_gates`` fixed LoRa gateways in the plane, keeping any
    two of them at least ``min_spacing`` apart (a "hard-core" process) so the
    gates do not stack on top of each other.

    Rejection sampling inside a slightly larger disk (radius + min_spacing):
    each gate is drawn uniformly by area until it is far enough from all the
    ones already placed. Returns a list of (x, y) pairs.
    """
    rng = random.Random(seed)
    max_radius = radius + min_spacing
    gates = []
    for _ in range(n_gates):
        for _ in range(20000):  # bounded attempts per gate
            r = max_radius * np.sqrt(rng.random())
            theta = 2 * np.pi * rng.random()
            x, y = r * np.cos(theta), r * np.sin(theta)
            if all((x - gx) ** 2 + (y - gy) ** 2 >= min_spacing ** 2 for gx, gy in gates):
                gates.append((x, y))
                break
        else:
            raise RuntimeError(
                f"Could not place {n_gates} gates within {radius} m with "
                f"min_spacing={min_spacing} m. Lower n_gates or min_spacing."
            )
    return gates



class Satellite_Gateway(Gateway_Distribution):
    """LEO satellite gateway whose visibility windows follow the analytical
    coverage-time model of Seyedi & Safavi, "On the Analysis of Random
    Coverage Time in Mobile LEO Satellite Communications", IEEE Communications
    Letters, vol. 16, no. 5, pp. 1526-1529, May 2012,
    doi:10.1109/LCOMM.2012.031912.112323 (Section II, Eqs. (1)-(5)).

    Instead of sampling the minimum angular distance gamma_m (uniform on
    [0, gamma_0), Eq. (3)) and mapping it with Eq. (1), each pass duration t_c
    is drawn directly from the equivalent coverage-time pdf, Eq. (4), and the
    resulting windows are placed back to back over the simulation horizon.
    """
    def __init__(self, gateway_param):
        super().__init__(gateway_param)
        self.sim_time = gateway_param.get('sim_time', 3600)  # Default simulation time in seconds
        self.env = gateway_param['env']  # Environment for simulation
        mu_earth = const.GM_earth.value  # ~3.986004418e14 m3 / s2
        self.Re = const.R_earth.value    # ~6.3781e6 m
        # Satellite altitude above the Earth's surface (m). Hard-coded; the
        # paper studies it as a sweep variable (its Fig. 1).
        self.h = 750000
        # Satellite radius from Earth's center (m): r = Re + h
        self.r = self.Re + self.h
        # Satellite orbital angular velocity (rad/s): omega_s = sqrt(mu/r^3)
        omega_s = np.sqrt((mu_earth)/(self.r**3))
        # Sidereal day length (s)
        T_sideral = 86164.1
        # Earth's rotation angular velocity (rad/s): omega_e = 2*pi/T_sideral
        omega_e = 2 * np.pi / T_sideral
        # Minimum elevation angle for visibility (deg) -- the paper's theta_0
        theta_0 = np.deg2rad(30)
        # Orbit inclination (deg) -- the paper's i
        i = np.deg2rad(60)
        # Constellation attribute (paper, Section II):
        #   omega = (omega_s - omega_e * cos(i)) / 2
        omega = (omega_s - omega_e*np.cos(i))/2
        self.omega = omega
        # Earth central angle for the minimum elevation (paper, Eq. (2)):
        #   gamma_0 = arccos(Re/(Re+h) * cos(theta_0)) - theta_0
        gamma_0 = np.arccos((self.Re/self.r)*np.cos(theta_0)) - theta_0
        self.gamma_0 = gamma_0
        # Maximum coverage time per pass (paper, Eq. (5)): T_m = gamma_0 / omega
        self.T_m = gamma_0/self.omega

        # pdf of the coverage time t_c (paper, Eq. (4)); support (0, T_m] with
        # T_m from Eq. (5). Drawing t_c from this pdf is equivalent to sampling
        # gamma_m ~ U[0, gamma_0) (Eq. (3)) and applying Eq. (1).
        class CoverageTimeDist(rv_continuous):
            def _pdf(self, tc):
                tc_arr = np.asarray(tc)
                arg = omega * tc_arr
                num = omega * np.cos(gamma_0) * np.tan(arg)
                den = gamma_0 * np.sqrt(np.cos(arg)**2 - np.cos(gamma_0)**2)
                pdf = num / den
                return pdf
        coverage_dist = CoverageTimeDist(a=0, b=self.T_m)
        
        # Build the visibility windows: each window's duration T_aux is drawn
        # independently from the pdf above (paper, Eq. (4)) and the windows are
        # placed back to back until the simulation horizon is reached. The
        # azimuth of each pass is not part of the paper and is drawn uniformly.
        time = np.array([])
        self.elevations = np.array([])
        window_ends = []
        azimutes = []
        while True:
            T_aux = coverage_dist.rvs()
            t, el = self.elevation_vs_time(T_aux)
            if time.size == 0:
                t_offset = t
            else:
                t_offset = t + np.max(time) + 1
            time = np.append(time, t_offset)
            self.elevations = np.append(self.elevations, el)
            window_ends.append(t_offset[-1])
            azimutes.append(np.random.uniform(0, 2*np.pi))
            if time[-1] >= self.sim_time:
                break

        self.azimutes = np.array(azimutes)
        self.window_ends = np.array(window_ends)

    def elevation_vs_time(self, T, num=500):
        """
        Calculates the elevation angle (rad) over a window of duration T,
        for altitude h, ensuring the correct peak.
        """
        # Window central half-angle
        half_ang = self.omega * int(T)
        # Minimum elevation angle at the center of the window
        phi_min = self.gamma_0 - half_ang
        
        # Generate simetric curve
        t = np.linspace(0, 2*int(T), int(T)+1)
        alpha = self.omega * t - half_ang
        phi = np.abs(alpha) + phi_min
        # elevation angle
        el = np.arctan2(self.r * np.cos(phi) - self.Re, self.r * np.sin(phi))
        return t/2, el
    
    #Auxiliary functions to get the azimuth and elevation angles at a given time
    def get_azimuth_at_time(self,t_query):
        return self.azimutes[np.argmax(self.window_ends>np.floor(t_query))]

    def get_elevation_at_time(self, t_query):
        return self.elevations[int(t_query)]
    
    
    def gateway_distribution_function(self):
        return self.gateway_distribution_param['x'], self.gateway_distribution_param['y'], self.gateway_distribution_param['z']
    
    def get_distance(self, x, y, z):
        azimuth = self.get_azimuth_at_time(self.env.now)
        elevation_center = self.get_elevation_at_time(self.env.now)
        _, distance = self.local_elev_dist(elevation_center, self.h, azimuth, x, y)
        return distance
    
    def get_elevation(self, x, y, z):
        azimuth = self.get_azimuth_at_time(self.env.now)
        elevation_center = self.get_elevation_at_time(self.env.now)
        elevation, _ = self.local_elev_dist(elevation_center, self.h, azimuth, x, y)
        return elevation
    
    
    def local_elev_dist(self,e_center, d_center, az_center, dx, dy):
        """
        Calculates the elevation angle and slant distance for a device displaced
        by (dx, dy) meters relative to the central point (0,0), given:
        - e_center: elevation angle at the center [rad]
        - d_center: slant distance at the center [m]
        - az_center: satellite azimuth at the center [rad] (0 = east, pi/2 = north)
        Returns (e_local, d_local):
        - e_local: elevation at the device [rad]
        - d_local: slant distance at the device [m]
        """
        # Satellite position vector in the ENU (East-North-Up) frame centered at (0,0)
        x_c = d_center * np.cos(e_center) * np.cos(az_center)
        y_c = d_center * np.cos(e_center) * np.sin(az_center)
        z_c = d_center * np.sin(e_center)
                
        # Satellite-to-device vector
        x_rel = x_c - dx
        y_rel = y_c - dy
        z_rel = z_c  # Assuming same level sea
        
        # Local distance
        d_local = np.sqrt(x_rel**2 + y_rel**2 + z_rel**2)
        # Local elevation angle
        e_local = np.arctan2(z_rel, np.sqrt(x_rel**2 + y_rel**2))
        
        return np.rad2deg(e_local), d_local
