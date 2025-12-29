#!/bin/bash
# Generate self-signed certificate for local HTTPS
mkdir -p /tmp/certs

if [ ! -f /tmp/certs/localhost.crt ]; then
  openssl req -x509 -newkey rsa:2048 -keyout /tmp/certs/localhost.key \
    -out /tmp/certs/localhost.crt -days 365 -nodes \
    -subj "/C=US/ST=Local/L=Local/O=Local/CN=localhost"
fi

echo "Certificate generated at /tmp/certs/"
