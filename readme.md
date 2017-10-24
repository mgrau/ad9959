# Overview
This project is ment to run on a RaspberryPi connected to an AD9959 eval board. After installation the Raspberry Pi will provide a web interface on port 5000 (might change to port 80 in the future) to set the 4 output channels of the DDS eval board. After starting the the server the fist time you can edit the displayed names of the channels on the web page by modifying `static/webinterface_settings.json` as root.

# Usage
For setting the output frequency and amplitude of the DDS channels you can do the following:
* Use the web interface on port 5000 (might change to 80).
* Use the pyonizer client found in the pyonizer folder in `devices/AD9959/AD9959Client.py`.
* Write your own client. Check the documentation by browsing to `http://<your raspberry pi's ip>:5000/doc` for details.

# Installation
Clone this repository to your Raspberry Pi and run `./install.sh`. The bash script will install all required python libraries, set up the clock output of the Raspberry Pi and install a service that automatically starts the flask server.
Note that on the current version of the tiqi Raspberry Pi image no c compiler is installed. In case that will change in the future you will be asked whether you want to reinstall the compiler. Just answer with no and update the install script accordingly.

***
Last updated: 24.10.2017