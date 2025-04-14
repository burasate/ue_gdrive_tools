from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import io

# Set up Google Drive API credentials and service
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = None

# Authentication
def authenticate():
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    return service

# List files in Google Drive folder
def list_files_in_drive(service, folder_id):
    results = service.files().list(q=f"'{folder_id}' in parents", fields="files(id, name)").execute()
    files = results.get('files', [])
    file_list = {file['name']: file['id'] for file in files}
    return file_list

# Upload a file to Google Drive
def upload_file(service, file_path, folder_id):
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"File uploaded: {file['id']}")
    return file['id']

# Download a file from Google Drive
def download_file(service, file_id, destination_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    print(f"Downloaded {destination_path}")

# Example usage
if __name__ == '__main__':
    service = authenticate()
    folder_id = 'YOUR_FOLDER_ID'  # Replace with your folder ID

    # List files in Google Drive
    file_list = list_files_in_drive(service, folder_id)
    print(file_list)

    # Upload a file to Google Drive
    upload_file(service, 'path/to/your/file.txt', folder_id)

    # Download a file from Google Drive
    download_file(service, 'YOUR_FILE_ID', 'path/to/destination/file.txt')
