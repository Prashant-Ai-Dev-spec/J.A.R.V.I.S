#!/usr/bin/env bash
# Obtain LetsEncrypt cert with certbot (requires domain pointing to this host)
set -e
if [ -z "$1" ]; then
  echo "Usage: $0 yourdomain.com"
  exit 1
fi
DOMAIN=$1
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d $DOMAIN
# Copy certs to backend/certs as needed
