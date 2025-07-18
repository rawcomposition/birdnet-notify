#!/usr/bin/env python3

import sqlite3
import requests
import time
import os
import sys
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set


class BirdNETNotifier:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self.load_config()

        self.db_path = os.path.expanduser(self.config.get('database_path', '~/birdnet-go-app/data/birdnet.db'))
        self.post_url = self.config.get('post_url', '')
        self.poll_interval = int(self.config.get('poll_interval', '5'))
        self.cooldown_minutes = int(self.config.get('cooldown_minutes', '10'))
        self.max_species_per_notification = int(self.config.get('max_species', '6'))

        self.ignore_file = self.config_path.parent / 'ignore_species.txt'
        self.ignored_species = self.load_ignored_species()

        self.last_notified = {}  # species -> timestamp
        self.running = False

        self.setup_logging()
        self.last_processed_id = self.get_current_max_id()

    def normalize_species_name(self, species_name: str) -> str:
        if not species_name:
            return ""
        normalized = species_name.strip().lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', '_', normalized)
        return normalized

    def setup_logging(self):
        log_level = self.config.get('log_level', 'INFO').upper()
        log_file = self.config_path.parent / 'birdnet_notify.log'

        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self) -> Dict[str, str]:
        config = {}

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                print(f"Error reading config file: {e}")
                config = self.create_default_config()
        else:
            config = self.create_default_config()

        return config

    def create_default_config(self) -> Dict[str, str]:
        config = {
            'database_path': '~/birdnet-go-app/data/birdnet.db',
            'post_url': '',
            'max_species': '6',
            'poll_interval': '5',
            'cooldown_minutes': '10',
            'log_level': 'INFO'
        }

        try:
            with open(self.config_path, 'w') as f:
                for key, value in config.items():
                    f.write(f"{key} = {value}\n")
            print(f"Created default config at {self.config_path}")
        except Exception as e:
            print(f"Error creating config file: {e}")

        return config

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                for key, value in self.config.items():
                    f.write(f"{key} = {value}\n")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def load_ignored_species(self) -> Set[str]:
        ignored = set()

        if self.ignore_file.exists():
            try:
                with open(self.ignore_file, 'r') as f:
                    for line in f:
                        species = line.strip()
                        if species and not species.startswith('#'):
                            normalized = self.normalize_species_name(species)
                            if normalized:
                                ignored.add(normalized)
                print(f"Loaded {len(ignored)} ignored species from {self.ignore_file}")
            except Exception as e:
                print(f"Error loading ignore file: {e}")
        else:
            print(f"Ignore file not found at {self.ignore_file}, creating empty file")
            try:
                self.ignore_file.touch()
            except Exception as e:
                print(f"Error creating ignore file: {e}")

        return ignored

    def get_current_max_id(self) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM notes")
            result = cursor.fetchone()
            max_id = result[0] if result[0] else 0
            conn.close()
            self.logger.info(f"Current max ID in database: {max_id}")
            return max_id
        except Exception as e:
            self.logger.error(f"Error getting current max ID: {e}")
            return 0

    def get_new_detections(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
                SELECT id, scientific_name, common_name, confidence, date, time
                FROM notes
                WHERE id > ?
                ORDER BY id ASC
            """

            cursor.execute(query, (self.last_processed_id,))
            rows = cursor.fetchall()

            detections = []
            for row in rows:
                detection_id, scientific_name, common_name, confidence, date, time_str = row
                detections.append({
                    'id': detection_id,
                    'scientific_name': scientific_name or '',
                    'common_name': common_name or '',
                    'confidence': confidence,
                    'date': date,
                    'time': time_str
                })

            conn.close()
            return detections

        except Exception as e:
            self.logger.error(f"Error querying database: {e}")
            return []

    def should_notify_species(self, species_name: str) -> bool:
        if not species_name:
            return False

        normalized_species = self.normalize_species_name(species_name)

        if normalized_species in self.ignored_species:
            return False

        now = datetime.now()
        last_notified_time = self.last_notified.get(normalized_species)

        if last_notified_time:
            time_diff = now - last_notified_time
            if time_diff < timedelta(minutes=self.cooldown_minutes):
                return False

        return True

    def send_notification(self, species_list: List[str]):
        if not species_list:
            return

        if len(species_list) > self.max_species_per_notification:
            truncated_list = species_list[:self.max_species_per_notification]
            remaining = len(species_list) - self.max_species_per_notification
            message = f"{', '.join(truncated_list)} + {remaining} more"
        else:
            message = ', '.join(species_list)

        try:
            response = requests.post(
                self.post_url,
                data=message,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info(f"Notification sent successfully: {message}")
            else:
                self.logger.error(f"Failed to send notification. Status: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")

    def process_detections(self, detections: List[Dict]):
        if not detections:
            return

        species_to_notify = []
        now = datetime.now()

        for detection in detections:
            detection_id = detection['id']
            scientific_name = detection['scientific_name']
            common_name = detection['common_name']

            self.last_processed_id = max(self.last_processed_id, detection_id)

            species_name = common_name if common_name else scientific_name
            if self.should_notify_species(species_name):
                species_to_notify.append(species_name)
                self.last_notified[self.normalize_species_name(species_name)] = now

        if species_to_notify:
            self.send_notification(species_to_notify)

    def run(self):
        if not self.post_url:
            self.logger.error("No POST_URL configured. Please set it in the config file.")
            return

        if not os.path.exists(self.db_path):
            self.logger.error(f"Database not found at {self.db_path}")
            return

        self.logger.info("Starting BirdNET notification service")
        self.logger.info(f"Database: {self.db_path}")
        self.logger.info(f"Post URL: {self.post_url}")
        self.logger.info(f"Poll interval: {self.poll_interval} seconds")
        self.logger.info(f"Cooldown: {self.cooldown_minutes} minutes")

        self.running = True

        while self.running:
            try:
                detections = self.get_new_detections()
                if detections:
                    self.logger.info(f"Found {len(detections)} new detections")
                self.process_detections(detections)
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(self.poll_interval)

        self.logger.info("BirdNET notification service stopped")

    def stop(self):
        self.running = False


def main():
    script_dir = Path(__file__).parent
    config_path = script_dir / 'config.conf'

    notifier = BirdNETNotifier(config_path)

    if len(sys.argv) == 2:
        post_url = sys.argv[1]
        if not notifier.post_url:
            notifier.config['post_url'] = post_url
            notifier.save_config()
            notifier.post_url = post_url
            notifier.logger.info(f"Updated config with POST_URL: {post_url}")

    notifier.run()


if __name__ == "__main__":
    main()
