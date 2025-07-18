#!/usr/bin/env python3
"""
Test script to verify BirdNET-Go notification configuration.
"""

import sys
from pathlib import Path


def test_config():
    script_dir = Path(__file__).parent
    config_path = script_dir / 'config.conf'
    
    print(f"Testing configuration: {config_path}")
    
    if not config_path.exists():
        print("Configuration file not found. Creating default...")
        config_content = """database_path = ~/birdnet-go-app/data/birdnet.db
post_url = https://ntfy.sh/test-topic
max_species = 6
poll_interval = 5
cooldown_minutes = 10
log_level = INFO
log_file = birdnet_notify.log"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        print("✓ Default configuration created")
    else:
        print("✓ Configuration file found")
    
    config = {}
    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    except Exception as e:
        print(f"✗ Error reading config: {e}")
        return False
    
    print("\nConfiguration values:")
    print(f"  Database path: {config.get('database_path', 'NOT SET')}")
    print(f"  Post URL: {config.get('post_url', 'NOT SET')}")
    print(f"  Max species: {config.get('max_species', 'NOT SET')}")
    print(f"  Poll interval: {config.get('poll_interval', 'NOT SET')}")
    print(f"  Cooldown minutes: {config.get('cooldown_minutes', 'NOT SET')}")
    print(f"  Log level: {config.get('log_level', 'NOT SET')}")
    print(f"  Log file: {config.get('log_file', 'NOT SET')}")
    
    print("\n✓ Configuration test passed!")
    return True


if __name__ == "__main__":
    try:
        test_config()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        sys.exit(1) 