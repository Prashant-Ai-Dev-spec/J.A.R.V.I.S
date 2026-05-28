#!/usr/bin/env bash
# Provision coturn on Ubuntu (manual steps)
set -e
sudo apt-get update
sudo apt-get install -y coturn
sudo systemctl enable coturn
# edit /etc/turnserver.conf as needed (see WEBRTC_SETUP.md)
echo "coturn installed. Edit /etc/turnserver.conf and restart: sudo systemctl restart coturn" 
