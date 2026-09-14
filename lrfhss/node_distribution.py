from lrfhss.lrfhss_core import Node_Distribution
import warnings
import numpy as np

## Uniform distribution in a circle
# This distribution generates nodes uniformly distributed in a circle with a given radius.
# Devices are static, so the distribution is only used to generate the initial positions.
class Uniform_Circle_Distribution(Node_Distribution):
    def __init__(self, traffic_param):
        super().__init__(traffic_param)
        if not 'radius' in self.node_distribution_param:
            warnings.warn(f'node_distribution_param radius key missing for Uniform_Circle_Distribution. Using radius=80000 as default')
            self.node_distribution_param['radius'] = 80_000

    def node_distribution_function(self):
        r, theta = self.node_distribution_param['radius'] * np.sqrt(np.random.rand()), 2 * np.pi * np.random.rand()
        return r * np.cos(theta), r * np.sin(theta), 0  # Assuming z=0 for a 2D distribution
    
