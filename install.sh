#! /usr/bin/evn bash
echo 'Enable clock output.'
gcc minimal_clk.c minimal_clk
sudo mv minimal_clk /usr/bin/minimal_clk

echo 'Install required python libs.'
sudo pip install flask_autodoc, RPi.GPIO

echo 'Install python service.'
sudo mv ad9959Http.service /etc/systemd/system/ad9959Http.service
sudo systemctl enable ad9959Http.service

echo 'Start server.'
sudo systemctl daemon-reload
sudo stemctl start ad9959Http.service

echo 'Done.'