# BirdNET-Go Notification Service

Polls the BirdNET-Go SQLite database for new species detections and sends notifications to a specified endpoint.

## Install/Update

```bash
curl -sSL https://raw.githubusercontent.com/rawcomposition/birdnet-notify/main/install.sh | sudo bash -s https://ntfy.sh/your-topic
```

## Configuration

#### `config.conf`

`sudo nano /opt/birdnet-notify/config.conf`

```ini
database_path = ~/birdnet-go-app/data/birdnet.db
post_url = https://ntfy.sh/your-topic
max_species = 6
poll_interval = 5
cooldown_minutes = 10
log_level = INFO
log_file = /var/log/birdnet_notify.log
```

#### `ignore_species.txt`

`sudo nano /opt/birdnet-notify/ignore_species.txt`

Add species to ignore (one per line, case-insensitive):

```
House Sparrow
European Starling
American Robin
...
```

### Service Commands

```bash
sudo systemctl status birdnet-notify
sudo systemctl restart birdnet-notify
sudo systemctl stop birdnet-notify
sudo systemctl start birdnet-notify
```

### Uninstall

```bash
sudo /opt/birdnet-notify/uninstall.sh
```

## Troubleshooting

### View Logs

```bash
sudo journalctl -u birdnet-notify -n 50
```

### Test Database Connection

```bash
python3 test_db.py /path/to/birdnet.db
```

### Test Configuration

```bash
python3 test_config.py
```

### No Notifications

1. Check POST URL is correct
2. Verify species aren't in ignore list
3. Ensure database has new detections
4. Check network connectivity

### Too Many Notifications

1. Add common species to `ignore_species.txt`
2. Increase `cooldown_minutes` in config
3. Reduce `poll_interval` if needed
