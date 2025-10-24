#!/bin/sh
set -e

CERT_DIR="/app/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

# Создаем директорию для сертификатов
mkdir -p "$CERT_DIR"

# Проверяем наличие сертификатов
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "🔒 Generating self-signed SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -days 365 \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:192.168.0.8,IP:127.0.0.1"
    echo "✅ SSL certificate generated!"
else
    echo "✅ SSL certificate already exists"
fi

# Выполняем переданную команду
exec "$@"
