# -*- coding: utf-8 -*-
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os, io
from importlib import reload
from . import config
reload(config)

base_dir = config.ROOT_DIR

class drive_handler:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.token_path = config.TOKEN_PATH
        self.folder_id = config.PROJECT_DIR_ID
        self.creds_path = config.CREDS_PATH
        self.sa_path = getattr(config, 'SERV_ACC_PATH', None)
        self.creds = None
        self.service = self.authenticate()
        if self.creds:
            print(f'Get folder ID : {config.PROJECT_DIR_ID}')
            file_items = self.list_files_in_drive(config.PROJECT_DIR_ID)
            if not os.path.basename(config.VERSION_DIR) in list(file_items):
                self.create_folder(os.path.basename(config.VERSION_DIR), config.PROJECT_DIR_ID)
            assert [i for i in list(file_items) if i.endswith('uproject')], '.\n--------\nProject folder should have uproject inside\n--------\n'
            print('Drive is connected.')

    def authenticate(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                assert os.path.exists(self.creds_path), '.\n--------\nCouldn\'t be found : config.CREDS_PATH\n--------\n'
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        service = build('drive', 'v3', credentials=self.creds)
        return service

    def list_files_in_drive(self, folder_id):
        query = f"'{folder_id}' in parents and trashed=false"
        results = self.service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results.get('files', [])
        file_list = {file['name']: file['id'] for file in files}
        return file_list

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