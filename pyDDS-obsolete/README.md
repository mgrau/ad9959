pyDDS ----- This library was created for the control of AOMs in laser
modulation in a lab at ETH: dkun@student.ethz.ch

pyDDS is a python interface to control a AD9959 quad channel DDS with a raspbery pi. Specifically, it can be used to program four individual sinus signals and execute amplitude and frequency ramps.
The included kicad PCB design can be used to easily connect and power up to two EVAL-AD9959 evaluation boards.


Features
--------
- reset, init functions: reset, respectively reinitialise the DDS state and the pyDDS class
- write, read functions: manually write to or read out from the DDS registers. basic building blocks for all higher level functions
- set_refclock, - set_freqmult: Sets the reference clock frequency (default 50MHz), and the refernce clock multiplier respectively (default 10), which together set the internal system clock of the DDS (default 500MHz). 
- set_channels: Activates the DDS channels which should take on the values from following commands. Can be one or several among the four DDS channels on the AD9959.
- basic set_ functions: set frequency, phase, amplitude and current of independent channels. able to set single or multiple channels as described in set_channels above.
- basic get_ functions: every set_ function has a corresponding get_ function returning the values currently set in every channel 
- sweep functions: set linear sweeps of amplitude and frequency as per accordance of the AD9959 datasheet. this means setting start and end value as well as rising and falling step sizes and step intervals.
- timed sweep functions: allow simplified use of sweep functions, substituting the need for step sizes and intervals with the ability to set a total ramp time. NOTE: amplitude step sizes however make this function impractical because the maximum sweep time allowed lies below 1ms
-also includes a dictionary of DDS registers and profile pin assignments as per the datasheet, the kicad PCB design respectively. the latter allow manual toggling of the ramps, once programmed


Anticipated Features
--------------------
- timed sweep function for amplitude with increased sweeptime
- phase linear sweep function
- web interface
