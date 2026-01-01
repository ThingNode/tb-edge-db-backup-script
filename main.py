#!/usr/bin/env python3

import subprocess
import os
import json
import shutil

metadata = {}
with open("data.json", "r") as f:
    content = json.load(f)
    metadata = content


# ===================== CONFIG =====================
CONTAINER_NAME = "tb-edge-db"   # Docker container running Postgres
DB_NAME = "tb-edge"
DB_USER = "postgres" 

S3_FOLDER = metadata.get("backup_folder")
print(f"S3 Backup Folder from metadata: {S3_FOLDER}")
# ==================================================

# Backup in the same folder as script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
backup_dir = os.path.join(SCRIPT_DIR, "tb_edge_backup_tmp")
archive_file = os.path.join(SCRIPT_DIR, "tb_edge_backup.tar.gz")

def run(cmd):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("ERROR: command failed")
        exit(1)

def remove_old_archives():
    """Remove any previous archive and temp folder"""
    if os.path.exists(archive_file):
        print(f"Removing old archive: {archive_file}")
        os.remove(archive_file)
    if os.path.exists(backup_dir):
        print(f"Removing old temporary backup folder: {backup_dir}")
        shutil.rmtree(backup_dir)

def main():
    # 1. Cleanup old files first
    remove_old_archives()

    # 2. Create temporary backup folder
    os.makedirs(backup_dir, exist_ok=True)
    dump_file = os.path.join(backup_dir, f"{DB_NAME}.dump")

    # 3. Dump full database from Docker
    run(f"docker exec -t {CONTAINER_NAME} pg_dump -U {DB_USER} -F c {DB_NAME} > {dump_file}")

    # 4. Archive the backup folder into single .tar.gz
    run(f"tar -czf {archive_file} -C {SCRIPT_DIR} {os.path.basename(backup_dir)}")

    # 5. Remove temporary folder
    shutil.rmtree(backup_dir)

    print("Backup completed successfully!")
    print(f"Archive file: {archive_file}")

if __name__ == "__main__":
    main()
