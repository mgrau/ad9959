# Overview
This project is ment to run on a RaspberryPi connected to an AD9959 eval board. After installation the Raspberry Pi will provide a web interface on port 5000 to set the 4 output channels of the DDS eval board. After starting the the server the fist time you can edit the displayed names of the channels on the web page by modifying `static/webinterface_settings.json` as root.

# Usage
For setting the output frequency and amplitude of the DDS channels you can do the following:
* Use the web interface on port 5000.
* Use the pyonizer client (`devices/AD9959/AD9959Client.py`).
* Write your own client. Check the documentation on port 5000 /doc for details.

# Installation
Compile `minimal_clk.c` using your favorit c compiler and then copy the executable into the root directory
```c
	gcc minimal_clk.c minimal_clk
	sudo mv minimal_clk /root/minimal_clk
```
Then set up a task that starts the flask interface when the Raspberry Pi is started. For that run the following commands 
```
	sudo mv ad9959Http.service /etc/systemd/system/ad9959Http.service
	sudo systemctl enable ad9959Http.service
```
You can check whether the service is enabled by typing `systemctl list-unit-files`
