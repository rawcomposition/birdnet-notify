#!/usr/bin/env python3
"""
Test script to verify BirdNET-Go database connectivity and schema.
"""

import sqlite3
import sys
from pathlib import Path


def test_database(db_path):
    print(f"Testing database: {db_path}")

    if not Path(db_path).exists():
        print(f"ERROR: Database file not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("✓ Database connection successful")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if cursor.fetchone():
            print("✓ 'notes' table found")
        else:
            print("✗ 'notes' table not found")
            return False

        cursor.execute("PRAGMA table_info(notes)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        required_columns = ['id', 'scientific_name', 'common_name', 'confidence', 'date', 'time']
        missing_columns = [col for col in required_columns if col not in column_names]

        if missing_columns:
            print(f"✗ Missing required columns: {missing_columns}")
            return False
        else:
            print("✓ All required columns found")

        cursor.execute("SELECT COUNT(*) FROM notes")
        count = cursor.fetchone()[0]
        print(f"✓ Found {count} records in notes table")

        if count > 0:
            cursor.execute("SELECT id, scientific_name, common_name, confidence, date, time FROM notes ORDER BY id DESC LIMIT 5")
            recent = cursor.fetchall()
            print("\nRecent detections:")
            for row in recent:
                print(f"  ID: {row[0]}, Species: {row[2]} ({row[1]}), Confidence: {row[3]:.2f}, Date: {row[4]} {row[5]}")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "birdnet.db"

    success = test_database(db_path)

    if success:
        print("\n✓ Database test passed!")
        sys.exit(0)
    else:
        print("\n✗ Database test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
