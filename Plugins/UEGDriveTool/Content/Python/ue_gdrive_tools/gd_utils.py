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
        if not self.creds:
            raise RuntimeError(f"Drive service unavailable, check {config.SA_PATH}")
        if not config.PROJECT_DIR_ID:
            raise ValueError(f"Missing project folder ID in {config.PROJECT_DIR_ID_PATH}")
        print(f'Get folder ID : {config.PROJECT_DIR_ID}')
        try:
            file_items = self.list_files_in_drive(config.PROJECT_DIR_ID)
            if not os.path.basename(config.VERSION_DIR) in list(file_items):
                self.create_folder(os.path.basename(config.VERSION_DIR), config.PROJECT_DIR_ID)
                file_items = self.list_files_in_drive(config.PROJECT_DIR_ID)
        except HttpError as e:
            if e.resp.status == 404:
                unreal = config.unreal
                unreal.EditorDialog.show_message(
                    title="Google Drive Sync Error",
                    message=f"Folder ID '{config.PROJECT_DIR_ID}' not found in Google Drive.\n\nPlease make sure the folder exists and you have shared it with the Service Account email as an 'Editor'.",
                    message_type=unreal.AppMsgType.OK,
                    default_value=unreal.AppReturnType.OK
                )
                raise RuntimeError("Drive sync aborted: Folder ID not found or missing permissions.") from e
            else:
                raise
        assert [i for i in list(file_items) if i.endswith('uproject')], '.\n--------\nProject folder should have uproject inside\n--------\n'
        self._cleanup_storage()
        print('Drive is connected.')

    def authenticate(self):
        import base64, json
        if not os.path.exists(config.SA_BIN_PATH):
            if not os.path.exists(config.SA_PATH):
                unreal = config.unreal
                unreal.EditorDialog.show_message(
                    title="No Service Account File",
                    message=f'.\n--------\nPlease create service account and place it into..\n{config.SA_PATH}\n--------\n',
                    message_type=unreal.AppMsgType.OK,
                    default_value=unreal.AppReturnType.OK
                )
                return

            with open(config.SA_PATH, 'rb') as f:
                raw_data = f.read()
                b64_data = base64.b64encode(raw_data)
            with open(config.SA_BIN_PATH, 'wb') as f:
                f.write(b64_data)

        if os.path.exists(config.SA_BIN_PATH) and os.path.exists(config.SA_PATH):
            os.remove(config.SA_PATH)
        with open(config.SA_BIN_PATH, 'rb') as f:
            b64_data = f.read()
            try:
                json_data = base64.b64decode(b64_data)
                service_account_info = json.loads(json_data)
            except Exception as exc:
                raise RuntimeError(f"Invalid service account cache at {config.SA_BIN_PATH}") from exc

        self.creds = service_account.Credentials.from_service_account_info(
            service_account_info,scopes=self.SCOPES)
        service = build('drive', 'v3', credentials=self.creds)
        return service

    def list_files_in_drive(self, folder_id):
        query = f"'{folder_id}' in parents and trashed=false"
        try:
            file_list = {}
            page_token = None
            while True:
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageToken=page_token,
                    pageSize=1000,
                ).execute()
                for file in results.get('files', []):
                    if file['name'] in file_list:
                        print(f"Duplicate file name on Drive: {file['name']}, keeping the latest id")
                    file_list[file['name']] = file['id']
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
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
        media = MediaFileUpload(file_path, mimetype='application/octet-stream', resumable=True, chunksize=256*1024*1024)
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File uploaded: {file['id']}")
        return file['id']

    def download_file(self, file_id, destination_path):
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        print(f"Downloaded {destination_path}")

    def _cleanup_storage(self, usage_limit_ratio=0.4):
        # Keep this as an explicit opt-in hook instead of automatic deletion.
        about = self.service.about().get(fields="storageQuota").execute()
        storage = about.get('storageQuota', {})
        usage = int(storage.get('usage', 0))
        limit = int(storage.get('limit', 0))

        print(f"Current usage: {usage / (1024 ** 3):.2f} GB / {limit / (1024 ** 3):.2f} GB")

        if limit == 0:
            print("No storage limit detected. Skipping management.")
            return

        if usage >= limit * usage_limit_ratio:
            print("\nStorage exceeds threshold. Automatic deletion is disabled in this build.")
            print("Please clean up Drive manually or wire this method to an explicit allowlist first.")