#! /usr/bin/env bash
echo '>Install c compiler...'
sudo pacman -Syu glibc
sudo pacman -Scc

echo '>Enable clock output...'
gcc minimal_clk.c -o minimal_clk
sudo mv minimal_clk /usr/bin/minimal_clk

echo '>Install required python libs...'
sudo pip install flask_autodoc
sudo pip install RPi.GPIO

echo '>Install python service...'
sudo cp ad9959Http.service /etc/systemd/system/ad9959Http.service
sudo systemctl enable ad9959Http.service

echo '>Start server...'
sudo systemctl daemon-reload
sudo systemctl start ad9959Http.service

echo 'Finished installation.'