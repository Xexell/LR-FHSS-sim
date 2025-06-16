import random
from lrfhss.lrfhss_core import Fading
#from lrfhss_core import Fading
import warnings
import numpy as np
from scipy.stats import rayleigh, rice, nakagami

## Rayleigh fading
class Rayleigh_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'scale' in self.fading_param:
            warnings.warn(f'traffic_param scale key missing for Rayleigh_Fading. Using with scale=1 as default')
            self.fading_param['scale'] = 1.0

    def fading_function(self):
        scale = self.fading_param['scale']
        return rayleigh.rvs(scale=scale)        
    
## Rician fading
class Rician_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'k' in self.fading_param:
            warnings.warn(f'traffic_param k key missing for Rician_Fading. Using with k=3 as default')
            self.fading_param['k'] = 3
        
    def fading_function(self):
        K = self.fading_param['k']
        return rice.rvs(np.sqrt(2*K), scale= 1/np.sqrt(2*(K+1)))
        
## Nakagami-m fading
class Nakagami_M_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)
        if not 'm' in self.fading_param:
            warnings.warn(f'traffic_param m key missing for Nakagami_M_Fading. Using with m=1 as default')
            self.fading_param['m'] = 1.0 # para m=1, equivale ao Rayleigh
        if not 'omega' in self.fading_param:
            warnings.warn('Fading parameter "omega" missing for Nakagami_M_Fading. Using omega=1 as default')
            self.fading_param['omega'] = 1.0  # Energia média do sinal

    def fading_function(self):
        m = self.fading_param['m']
        omega = self.fading_param['omega']
        return nakagami.rvs(m, scale=omega)
    
## No fading
class No_Fading(Fading):
    def __init__(self, fading_param):
        super().__init__(fading_param)

    def fading_function(self):
        return 1