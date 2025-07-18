#!/bin/bash

set -e

SERVICE_NAME="birdnet-notify"
INSTALL_DIR="/opt/birdnet-notify"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Uninstalling BirdNET notification service..."

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

echo "Stopping and disabling service..."
systemctl stop "$SERVICE_NAME" || true
systemctl disable "$SERVICE_NAME" || true

echo "Removing service file..."
rm -f "$SERVICE_FILE"

echo "Reloading systemd..."
systemctl daemon-reload

echo "Removing installation directory..."
rm -rf "$INSTALL_DIR"

echo "Uninstallation complete!" 