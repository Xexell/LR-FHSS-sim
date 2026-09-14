from setuptools import setup, find_packages

setup(
    name="lrfhss",
    version="0.0.1",
    description="Event-driven LR-FHSS (LoRa-like frequency-hopping) network simulator",
    long_description="Event-driven LR-FHSS network simulator in Python, with "
                     "terrestrial, HAPS and satellite gateways and per-gateway fading.",
    license="GPL-3.0",
    python_requires=">=3.10",
    packages=find_packages(include=["lrfhss"]),
    install_requires=[
        "numpy",
        "scipy",
        "simpy",
        "astropy",
    ],
)
