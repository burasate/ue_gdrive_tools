import os
import hashlib
import zipfile
import json
from datetime import datetime

# Function to compute MD5 checksum of a file
def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Function to zip files
def zip_files(files, zip_name):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    print(f"Created zip file: {zip_name}")

# Function to log versioning info
def log_version(file_name, zip_name, metadata):
    log_data = {
        'file_name': file_name,
        'zip_name': zip_name,
        'timestamp': str(datetime.now()),
        'metadata': metadata
    }
    
    # Save log as JSON file
    log_file = f"{zip_name}_log.txt"
    if os.path.exists(log_file):
        with open(log_file, 'a') as f:
            json.dump(log_data, f, indent=4)
            f.write('\n')
    else:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=4)
            f.write('\n')
    print(f"Logged version to {log_file}")

# Function to check for updates in a directory and zip new/modified files
def update_version_and_zip(directory, zip_name):
    updated_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_md5 = get_md5(file_path)

            # Here you would compare MD5 against the saved version (for simplicity, we assume the file is always new/modified)
            updated_files.append(file_path)
    
    if updated_files:
        zip_files(updated_files, zip_name)
        log_version(directory, zip_name, {'files': updated_files})
    else:
        print("No updates found.")

# Example usage
if __name__ == '__main__':
    # Example: Update version and zip files from a directory
    update_version_and_zip('D:/UE_Project/Assets', 'assets_v1.zip')
