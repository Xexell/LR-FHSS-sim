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

The project contains two files. core.py contains the the main classes and features needed to run the simulation. This classe doesn't have any main procedure. In order to run the simulation, you have to built the simulation setup with the classes present in that file. The second file, run.py, is an example of a simulation setup. It simply builds a network with a certain amount of devices with certain input parameters, run it for a certain amount of time and returns the amount of successfully received packets divided by the amount of packets transmitted. For an example of how to use the run.py file, refer to the file examples/examples.ipynb.


