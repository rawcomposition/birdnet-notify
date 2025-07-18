#!/bin/bash

set -e

POST_URL="$1"

if [ -z "$POST_URL" ]; then
    echo "Usage: $0 <POST_URL>"
    echo "Example: $0 https://ntfy.sh/your-topic"
    exit 1
fi

INSTALL_DIR="/opt/birdnet-notify"
SERVICE_NAME="birdnet-notify"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Installing/Updating BirdNET notification service..."

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

mkdir -p "$INSTALL_DIR"

echo "Downloading latest script from GitHub..."
wget -O "$INSTALL_DIR/birdnet_notify.py" "https://raw.githubusercontent.com/rawcomposition/birdnet-notify/main/birdnet_notify.py"
wget -O "$INSTALL_DIR/requirements.txt" "https://raw.githubusercontent.com/rawcomposition/birdnet-notify/main/requirements.txt"
chmod +x "$INSTALL_DIR/birdnet_notify.py"

if [ ! -f "$INSTALL_DIR/config.conf" ]; then
    echo "Creating configuration..."
cat > "$INSTALL_DIR/config.conf" << EOF
database_path = ~/birdnet-go-app/data/birdnet.db
post_url = $POST_URL
max_species = 6
poll_interval = 5
cooldown_minutes = 10
log_level = INFO
log_file = /var/log/birdnet_notify.log
EOF
else
    echo "Updating POST URL in existing configuration..."
    sed -i "s|post_url = .*|post_url = $POST_URL|" "$INSTALL_DIR/config.conf"
fi

if [ ! -f "$INSTALL_DIR/ignore_species.txt" ]; then
    echo "Creating ignore file..."
    cat > "$INSTALL_DIR/ignore_species.txt" << EOF
# Add species to ignore (one per line, lowercase)
# Examples:
# house sparrow
# european starling
EOF
fi

echo "Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    echo "Checking for python3-venv..."
    if ! python3 -c "import venv" 2>/dev/null; then
        echo "Installing python3-venv..."
        apt-get update
        apt-get install -y python3-venv
    fi
    
    echo "Removing existing virtual environment if present..."
    rm -rf "$INSTALL_DIR/venv"
    
    echo "Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    
    echo "Activating virtual environment and installing dependencies..."
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/requirements.txt"
    deactivate
    
    PYTHON_PATH="$INSTALL_DIR/venv/bin/python"
    
    if [ -f "$PYTHON_PATH" ]; then
        echo "Virtual environment created successfully"
    else
        echo "Error: Virtual environment creation failed"
        exit 1
    fi
else
    echo "Error: python3 not found. Please install python3 and python3-venv:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3 python3-venv"
    exit 1
fi

echo "Creating systemd service..."
CURRENT_USER=$(logname || who am i | awk '{print $1}' || echo $SUDO_USER)
if [ -z "$CURRENT_USER" ]; then
    echo "Error: Could not determine current user"
    exit 1
fi

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=BirdNET-Go Notification Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON_PATH $INSTALL_DIR/birdnet_notify.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling and starting service..."
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "Installation/Update complete!"
echo ""
echo "Service status:"
systemctl status "$SERVICE_NAME" --no-pager -l
echo ""
echo "To view logs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
echo "To edit ignored species:"
echo "  sudo nano $INSTALL_DIR/ignore_species.txt"
echo ""
echo "To edit configuration:"
echo "  sudo nano $INSTALL_DIR/config.conf"
echo ""
echo "To restart the service:"
echo "  sudo systemctl restart $SERVICE_NAME" 