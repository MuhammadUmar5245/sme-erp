#!/bin/sh
# Generate a self-signed TLS certificate for nginx (HTTPS) and PostgreSQL (SSL for Power BI).
# Usage: scripts/gen_cert.sh [cert_dir]   (default: ./certs). Skips if a certificate already exists.
set -e
CERT_DIR="${1:-./certs}"
mkdir -p "$CERT_DIR"
if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "Certificate already exists in $CERT_DIR (set FORCE=1 to regenerate)."
    exit 0
fi
openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
    -subj "/C=OM/ST=Muscat/L=Muscat/O=Al Wadi Trading and Distribution LLC/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:db,IP:127.0.0.1"
chmod 644 "$CERT_DIR/server.crt"
chmod 640 "$CERT_DIR/server.key"
echo "Self-signed certificate written to $CERT_DIR (valid 825 days)."
