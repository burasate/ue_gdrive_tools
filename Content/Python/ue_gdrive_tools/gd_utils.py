# -*- coding: utf-8 -*-
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

import os, io
from importlib import reload
from . import config
reload(config)

base_dir = config.ROOT_DIR

class drive_handler:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.creds = None
        self.service = self.authenticate()
        if self.creds:
            print(f'Get folder ID : {config.PROJECT_DIR_ID}')
            file_items = self.list_files_in_drive(config.PROJECT_DIR_ID)
            if not os.path.basename(config.VERSION_DIR) in list(file_items):
                self.create_folder(os.path.basename(config.VERSION_DIR), config.PROJECT_DIR_ID)
            assert [i for i in list(file_items) if i.endswith('uproject')], '.\n--------\nProject folder should have uproject inside\n--------\n'
            self._cleanup_storage()
            print('Drive is connected.')

    def authenticate(self):
        import base64, json
        if not os.path.exists(config.SA_BIN_PATH):
            assert os.path.exists(config.SA_PATH), f'.\n--------\nPlease create service account and place it into..\n{config.SA_PATH}\n--------\n'
            with open(config.SA_PATH, 'rb') as f:
                raw_data = f.read()
                b64_data = base64.b64encode(raw_data)
            with open(config.SA_BIN_PATH, 'wb') as f:
                f.write(b64_data)

        if os.path.exists(config.SA_BIN_PATH) and os.path.exists(config.SA_PATH):
            os.remove(config.SA_PATH)
        with open(config.SA_BIN_PATH, 'rb') as f:
            b64_data = f.read()
            json_data = base64.b64decode(b64_data)
            service_account_info = json.loads(json_data)

        self.creds = service_account.Credentials.from_service_account_info(
            service_account_info,scopes=self.SCOPES)
        service = build('drive', 'v3', credentials=self.creds)
        return service

    def list_files_in_drive(self, folder_id):
        query = f"'{folder_id}' in parents and trashed=false"
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = results.get('files', [])
            file_list = {file['name']: file['id'] for file in files}
            return file_list
        except HttpError as e:
            raise Warning(f"\nAPI returned an error:\n{e}\nPlease double check your setting")

    def create_folder(self, name, parent_id=None):
        file_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            file_metadata['parents'] = [parent_id]
        file = self.service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')

    def upload_file(self, file_path, folder_id):
        file_name = os.path.basename(file_path)
        media = MediaFileUpload(file_path, mimetype='application/octet-stream')
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File uploaded: {file['id']}")
        return file['id']

    def download_file(self, file_id, destination_path):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        print(f"Downloaded {destination_path}")

    def _cleanup_storage(self, usage_limit_ratio=0.4):
        import datetime

        #Check current storage
        about = self.service.about().get(fields="storageQuota").execute()
        storage = about.get('storageQuota', {})
        usage = int(storage.get('usage', 0))
        limit = int(storage.get('limit', 0))

        print(f"Current usage: {usage / (1024 ** 3):.2f} GB / {limit / (1024 ** 3):.2f} GB")

        if limit == 0:
            print("No storage limit detected. Skipping management.")
            return

        # Start managing if over threshold
        if usage >= limit * usage_limit_ratio:
            print("\nStorage exceeds threshold. Managing files...")

            # Empty trash
            try:
                self.service.files().emptyTrash().execute()
                print("Trash emptied successfully.")
            except Exception as e:
                print(f"Failed to empty trash: {e}")

            # Recheck storage
            about = service.about().get(fields="storageQuota").execute()
            usage = int(about.get('storageQuota', {}).get('usage', 0))

            if usage < limit * usage_limit_ratio:
                print("Storage cleared after trash empty. No need to delete files.")
                return

            # List all files
            files = []
            page_token = None

            while True:
                response = self.service.files().list(
                    fields="nextPageToken, files(id, name, createdTime, size)",
                    spaces='drive',
                    pageSize=1000,
                    pageToken=page_token
                ).execute()

                for file in response.get('files', []):
                    if 'size' in file:  # Only consider files with size (skip folders)
                        files.append({
                            'id': file['id'],
                            'name': file['name'],
                            'createdTime': file['createdTime'],
                            'size': int(file['size'])
                        })

                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break

            # Sort by createdTime
            files.sort(key=lambda x: x['createdTime'])

            # Deleting oldest files
            deleted_count = 0
            for file in files:
                try:
                    self.service.files().delete(fileId=file['id']).execute()
                    deleted_count += 1
                    print(f"Deleted {file['name']} ({file['size'] / (1024 ** 2):.2f} MB)")

                    about = self.service.about().get(fields="storageQuota").execute()
                    usage = int(about.get('storageQuota', {}).get('usage', 0))
                    if usage < limit * usage_limit_ratio:
                        print("\nStorage under control now.")
                        break
                except Exception as e:
                    print(f"Failed to delete {file['name']}: {e}")

            #if deleted_count == 0:
                #print("No files were deleted.")
        #else:
            #print("\nStorage is under the threshold. No action needed.")