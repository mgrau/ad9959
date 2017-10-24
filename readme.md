# Overview
This project is ment to run on a Raspberry Pi connected to an AD9959 eval board. After installation the Raspberry Pi will provide a web interface on port 5000 (might change to port 80 in the future) to set the 4 output channels of the DDS eval board. After starting the the server the fist time you can edit the displayed names of the channels on the web page by modifying `static/webinterface_settings.json` as root.

# AD9959
The AD9959 is a four channel DDS that (on the eval board) can output frequencies up to around 200 MHz (there is a 200 MHz low pass filter for filtering out the clock). If you need to output higher frequencies you can bypass that filter by moving a 0 Ohm resistor (R22-R29). 
With the filter, the DDS will output the following power

| Frequency (Mhz) | Power (dBm)|
| --------------- | ---------- |
| 40              | -7.1       |
| 80              | -7.4       |
| 110             | -7.7       |
| 150             | -8.9       |

# Usage
For setting the output frequency and amplitude of the DDS channels you can do the following:
* Use the web interface on port 5000 (might change to 80).
* Use the pyonizer client found in the pyonizer folder in `devices/AD9959/AD9959Client.py`.
* Write your own client. Check the documentation by browsing to `http://<your raspberry pi's ip>:5000/doc` for details.

# Installation
Clone this repository to your Raspberry Pi and run `./install.sh`. The bash script will install all required python libraries, set up the clock output of the Raspberry Pi and install a service that automatically starts the flask server. Additionally it will patch the flask-autodoc library such that the documentation is rendered correctly.
Note that on the current version of the tiqi Raspberry Pi image no c compiler is installed. In case that will change in the future you will be asked whether you want to reinstall the compiler. Just answer with no and update the install script accordingly.

# Documentation
You can find the documentation for all externally available functions by browsing to `http://<your raspberry pi's ip>:5000/doc` from any computer on the same network as your Raspberry Pi. Additionally, you can generate the full documentation for this project using [doxygen][1]. Install doxygen (i.e. `pacman -Syu doxygen` on the Raspberry Pi or an installer [from here][2] for Windows) and run `doxygen doxygen_config`. The documentation can then be found in `html/index.html`.

[1]: http://www.stack.nl/~dimitri/doxygen/
[2]: http://www.stack.nl/~dimitri/doxygen/download.html

***
Last updated: 24.10.2017