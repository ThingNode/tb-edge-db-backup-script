#!/usr/bin/env python3

import subprocess
import os
import shutil
from datetime import datetime
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables from .env file
load_dotenv()

# ===================== CONFIG =====================
# Database Configuration from environment variables
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "tb-edge-db")
DB_NAME = os.getenv("DB_NAME", "tb-edge")
DB_USER = os.getenv("DB_USER", "postgres")

# AWS S3 Configuration from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_FOLDER = os.getenv("S3_FOLDER")

# Validate required environment variables
required_vars = {
    "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
    "S3_BUCKET_NAME": S3_BUCKET_NAME
}
missing_vars = [key for key, value in required_vars.items() if not value]

if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)

print(f"Database: {DB_NAME} (container: {CONTAINER_NAME})")
print(f"S3 Bucket: {S3_BUCKET_NAME}")
print(f"S3 Backup Folder: {S3_FOLDER}")
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

def upload_to_s3(file_path, s3_key):
    """Upload file to S3 bucket"""
    try:
        print(f"Uploading {file_path} to s3://{S3_BUCKET_NAME}/{s3_key}")
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Upload file with progress callback
        s3_client.upload_file(
            file_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ServerSideEncryption': 'AES256'}  # Optional: encrypt at rest
        )
        
        print(f"Successfully uploaded to s3://{S3_BUCKET_NAME}/{s3_key}")
        return True
    except ClientError as e:
        print(f"ERROR: Failed to upload to S3: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error during S3 upload: {e}")
        return False

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

    # 6. Upload archive to S3
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"{DB_NAME}_backup_{timestamp}.tar.gz"
    s3_key = f"{S3_FOLDER}/{archive_filename}" if S3_FOLDER else archive_filename
    
    if upload_to_s3(archive_file, s3_key):
        # Remove local archive after successful upload
        print(f"Removing local archive file: {archive_file}")
        os.remove(archive_file)
        print("Backup completed successfully!")
        print(f"Archive uploaded to: s3://{S3_BUCKET_NAME}/{s3_key}")
    else:
        print("ERROR: Failed to upload to S3. Local archive file kept for manual upload.")
        print(f"Local archive file: {archive_file}")
        exit(1)

if __name__ == "__main__":
    main()
