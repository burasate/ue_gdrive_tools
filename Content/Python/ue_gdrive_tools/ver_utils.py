# -*- coding: utf-8 -*-
import os, sys, hashlib, json, getpass, glob, time
from datetime import datetime, timezone
from importlib import reload
import zipfile36 as zipfile
from . import config
reload(config)
import numpy as np
import pandas as pd
#pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
import unreal

'''--------------------'''
# Init
'''--------------------'''
base_dir = os.path.dirname( os.path.abspath(__file__) )
project_dir = config.PROJECT_DIR
content_dir = config.CONTENT_DIR
extension_ls = ['uproject', 'umap', 'uasset']
version_dir = config.VERSION_DIR

'''--------------------'''
# Func
'''--------------------'''
def get_md5_file_path(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_md5_file_obj(file_obj):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()

def zip_files_with_hierarchy(files, zip_name):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.setpassword(config.PROJECT_DIR_ID.encode("utf-8"))
        for file in files:
            arcname = os.path.relpath(file, project_dir)
            zf.write(file, arcname)
    print(f"Created zip file: {zip_name}")

def zip_extract_file(zip_path: str, zip_src_path: str):
    full_path = os.path.join(project_dir, zip_src_path)
    try:
        print(f"Extracting file: {zip_src_path}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.setpassword(config.PROJECT_DIR_ID.encode("utf-8"))
            zf.extract(zip_src_path, project_dir)
    except:
        unreal.log_warning(f"Unable to extract file: {zip_src_path}, Skip.")

def log_version(file_name, zip_name, metadata):
    log_data = {
        'file_name': file_name,
        'zip_name': zip_name,
        'timestamp': str(datetime.now()),
        'metadata': metadata
    }

    log_file = os.path.join(version_dir, 'log.txt')
    if os.path.exists(log_file):
        with open(log_file, 'a') as f:
            json.dump(log_data, f, indent=4)
            f.write('\n')
    else:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=4)
            f.write('\n')
    print(f"Logged version to {log_file}")

def update_version_zip():
    files_df = load_files_data()
    #print('.\n' + files_df.to_string())

    push_df = files_df[files_df['sync_push']]
    push_df = push_df.drop_duplicates(subset='file_path', keep='first')
    del_df = files_df[files_df['size_bytes'] <= 0 & files_df['is_deleted']]
    del_df = del_df.drop_duplicates(subset='file_path', keep='first')
    #print('push_df\n' + push_df.to_string())
    #print('del_df\n' + del_df.to_string())
    push_files = [i for i in push_df['file_path'].tolist() if os.path.exists(i)]

    # Create 0 bytes files
    del_files = [i for i in del_df['file_path'].tolist()]
    for fp in [i for i in del_files if not os.path.exists(i)]:
        print(f'write mock file: {os.path.abspath(fp)}')
        with open(fp, 'wb') as f:
            f.close()

    updated_files = push_files + del_files
    now_fmt = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    usr = getpass.getuser().lower()
    zip_path = os.path.join(version_dir, f'{now_fmt}__{usr}.zip')
    if updated_files:
        print(f"found {len(updated_files)} assets to update.")
        zip_files_with_hierarchy(updated_files, zip_path)
        log_version(content_dir, zip_path, {'files': updated_files})
        print(os.path.abspath(zip_path))
    else:
        print("No updates found.")

    [os.remove(i) for i in del_files]  # Remove 0 bytes files
    if os.path.exists(zip_path):
        return zip_path
    else:
        return None

def load_files_data():
    editor_asset_library = unreal.EditorAssetLibrary()
    asset_tools = unreal.AssetToolsHelpers().get_asset_tools()
    migrate_option = unreal.MigrationOptions(ignore_dependencies=True, orphan_folder=r'D:\works\Unreal Projects\Sample_Project_5_5\Test')
    usr = getpass.getuser().lower()
    files_rec = []

    # read current
    for root, dirs, files in os.walk(content_dir):
        for file in files:
            fp = os.path.join(root, file)
            if not file.lower().split('.')[-1] in extension_ls:
                continue

            name, ext = os.path.basename(fp).split('.')[0], os.path.basename(fp).split('.')[-1]
            asset_path = os.path.abspath(fp).replace(os.path.abspath(content_dir), '')
            asset_path = '/Game' + asset_path.replace('\\', '/')
            package_name = os.path.dirname(asset_path)+ f'/{name}'
            asset = editor_asset_library.load_asset(package_name)
            asset_data = editor_asset_library.find_asset_data(package_name)
            if asset_data.asset_name and asset_data.is_redirector():
                os.remove(fp)
                continue
            #if not asset_data.is_valid():
                #continue

            data = {
                'base_name': os.path.basename(fp),
                'file_path': fp.replace('\\', '/'),
                'md5_hash': get_md5_file_path(fp),
                'st_mtime': int(os.stat(fp).st_mtime),
                'source': None,
                'src_name': None,
                'size_bytes': os.stat(fp).st_size
            }
            files_rec.append(data)

    # read backup
    zip_path_ls = sorted(glob.glob(f'{version_dir}/*.zip'))
    for z_fp in zip_path_ls:
        with zipfile.ZipFile(z_fp, 'r') as zip_ref:
            for info in zip_ref.infolist():
                fn = info.filename
                dt = datetime(*info.date_time)
                dt_utc = dt.replace(tzinfo=timezone.utc)
                with zip_ref.open(fn) as f:
                    md5_hash = get_md5_file_obj(f)
                data = {
                    'base_name': os.path.basename(fn),
                    'file_path': os.path.join(project_dir, fn).replace('\\', '/'),
                    'md5_hash': md5_hash,
                    'st_mtime': int(os.stat(z_fp).st_mtime),
                    'source': z_fp.replace('\\', '/'),
                    'src_name': fn.replace('\\', '/'),
                    'size_bytes': info.file_size
                }
                files_rec.append(data)

    # dataframe
    files_rec = sorted(files_rec, key=lambda x: (x['st_mtime'], x['file_path'], x['md5_hash']), reverse=True)
    files_df = pd.DataFrame.from_records(files_rec)
    files_df['user'] = files_df['source'].str.split('__').str[-1].str.split('.').str[0]
    files_df['user'] = files_df['user'].fillna(usr)

    # Keep 2 comparision version of both
    files_df = files_df.groupby('file_path', group_keys=False).head(2)
    files_df = files_df.sort_values(['file_path', 'st_mtime'], ascending=[False, False])
    files_df.reset_index(drop=True, inplace=True)

    # Sync logic
    unique_grp = ['file_path', 'md5_hash', 'size_bytes']
    max_src_mtime = files_df[files_df['source'].notnull()]['st_mtime'].max()
    files_df['unique_n'] = files_df.groupby(unique_grp)['md5_hash'].transform('count')
    files_df['from_zip'] = files_df['source'].notna()
    files_df['remote_exists'] = (
        (files_df['file_path'].apply(os.path.exists) & files_df['from_zip'])
    )
    files_df['remote_exists'] = files_df.groupby(unique_grp)['md5_hash'].transform('any')
    files_df['local_exists'] = (
            files_df['file_path'].apply(os.path.exists)
    )
    files_df['is_last'] = (
            ((files_df['st_mtime'] > max_src_mtime) | pd.isna(max_src_mtime)) &
            (files_df['unique_n'] <= 1)
    )
    files_df['is_lost'] = ~files_df['local_exists']
    files_df['is_deleted'] = False
    files_df.loc[(files_df['user'] == usr) & (files_df['is_lost']), 'is_deleted'] = True

    # Sync dicision
    files_df['sync_push'] = files_df['is_last'] & ~files_df['from_zip']
    files_df['sync_pull'] = (
        files_df['from_zip'] & (
            (files_df['remote_exists'] & files_df['is_lost']) &
            ~files_df['is_deleted']
        )
    )
    files_df.loc[files_df['size_bytes'] <= 0, 'sync_pull'] = False
    files_df['size_bytes'] <= 0
    # add more condition if another user already delete and it will show 'size_bytes' <= 0 to prevent PULL
    files_df['sync_delete'] = ~files_df['sync_push'] & ~files_df['sync_pull']

    #print('.\n' + files_df.to_string())
    return files_df