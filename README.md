# LR-FHSS-sim
LR-FHSS event-driven simulator built in python.

## Instalation Guide
* pip:
  
Download the source code and extract it to a folder.

Open a terminal in the folder and execute the following to install the prerequisites libraries.
  ```sh
  pip install -r requirements.txt
  ```

Run the following to install the library.
  ```sh
  pip install .
  ```

If you wish to make changes to the library, you can install it with the editable flag, so any changes to the source code will apply to the version installed.
  ```sh
  pip install -e .
  ```

## Usage

The project contains three main files. lrfhss_core.py contains the the main classes and features needed to run the simulation. This classes don't have any main procedures. In order to run the simulation, you have to built the simulation setup with the classes present in that file. The second file, settings.py, contains several adjustable simulation parameters and is used to configure the simulator behavior. The file run.py is an example of a simulation scenario setup. It simply builds a network with a certain amount of devices with certain input parameters, run it for a certain amount of time and returns the amount of successfully received packets divided by the amount of packets transmitted. For an example of how to use the run.py file, refer to the file examples/examples.ipynb.

Two other files provide simulator extensions. The file traffic.py implements different types of traffic generators to be used by Node objects. Finally, acrda.py implements a new version of the Base (base station) class to implement the ACRDA receiver/decoder.

Plots were made with the [SciencePlots](https://github.com/garrettj403/SciencePlots) library.
