# LR-FHSS-sim
LR-FHSS event-driven simulator built in python.


## Version 0.2
* Assumes all nodes are in coverage
* Pure ALOHA with destructive collisions (no capture)
* EU DR8 datarate parameters (can be easily changed with global variables at source code)
* Outputs average network success probability
* Considers one channel grid of 35 subchannels
* Using standard transmission values from Asad's work, should be changed to specification values in future versions.
### New features
* SIC decoding on fragments
* Gateway can remove fragments from decoded packets
* Gateway keeps the received packets/fragments on memory for a predetermined time window, which advances with a predetermined step.
* Without SIC, consider a gateway with memory equals to the transmission length. With SIC and sic_window smaller than the transmission length, the gateway may erase some fragments (the first to arrive, e.g., headers) before the end of transmission.