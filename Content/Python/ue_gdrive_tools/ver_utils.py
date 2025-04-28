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

'''--------------------'''
# Init
'''--------------------'''
base_dir = os.path.dirname( os.path.abspath(__file__) )
project_dir = config.PROJECT_DIR
content_dir = config.CONTENT_DIR
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
    assert isinstance(files, list)
    files = set(list(files))
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            arcname = os.path.relpath(file, project_dir)
            zf.write(file, arcname)
    print(f"Created zip file: {zip_name}")

def zip_extract_file(zip_path: str, zip_src_path: str):
    full_path = os.path.join(project_dir, zip_src_path)
    try:
        print(f"Extracting file: {zip_src_path}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extract(zip_src_path, project_dir)
    except:
        import traceback
        print(f"Unable to extract file: {zip_src_path}, Skip.")

class log_file:
    pull_ls_path = config.PULL_VERSION_LIST_PATH

    @staticmethod
    def pull_version(zip_path, zip_src_path, mode=1):
        '''
        :param zip_path:
        :param zip_src_path:
        :param mode: 0 is to delete file, 1 is to replace file
        :return:
        '''
        rec = []
        if os.path.exists(log_file.pull_ls_path):
            with open(log_file.pull_ls_path) as f_read:
                rec = json.load(f_read)
        rec.append([zip_path, zip_src_path, mode])
        with open(log_file.pull_ls_path, 'w') as f_write:
            json.dump(rec, f_write, indent=4)
        return rec

    @staticmethod
    def delete_pull_version():
        if os.path.exists(log_file.pull_ls_path):
            os.remove(log_file.pull_ls_path)

    @staticmethod
    def read_pull_version():
        if os.path.exists(log_file.pull_ls_path):
            with open(log_file.pull_ls_path) as f_read:
                rec = json.load(f_read)
                return rec
        else:
            return None

def update_version_zip():
    db = database()
    files_df = db.get_all(debug=0)
    #print('ALL DF\n' + files_df.to_string())

    push_df = db.get_push()
    push_df = push_df.drop_duplicates(subset='file_path', keep='first')
    push_del_df = db.get_push_deleted()
    push_del_df = push_del_df.drop_duplicates(subset='file_path', keep='first')
    #print('PUSH DF\n' + push_df.to_string())
    #print('PUSH DELETE DF\n' + push_del_df.to_string())

    # Create 0 bytes files to inform the other that files were deleted
    del_files = [i for i in push_del_df['file_path'].tolist()]
    for fp in [i for i in del_files if not os.path.exists(i)]:
        print(f'create delete mock up file: {os.path.abspath(fp)}')
        dir_name = os.path.dirname(fp)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        os.chmod(dir_name, 0o777)
        with open(fp, 'wb') as f:
            f.close()

    push_files = [i for i in push_df['file_path'].tolist() if os.path.exists(i)]
    updated_files = push_files + del_files
    now_fmt = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    usr = getpass.getuser().lower()
    zip_path = os.path.join(version_dir, f'{now_fmt}__{usr}.zip')
    if updated_files:
        print(f"Found {len(updated_files)} assets to commit. ( Updated: {len(push_files)} | Deleted {len(del_files)} )")
        zip_files_with_hierarchy(updated_files, zip_path)
        print(os.path.abspath(zip_path))
    else:
        print("No updates found.")

    [os.remove(i) for i in del_files]  # Remove 0 bytes files
    if os.path.exists(zip_path):
        return zip_path
    else:
        return None

class database:
    def get_all(self, debug=False):
        import unreal
        editor_asset_library = unreal.EditorAssetLibrary()
        asset_tools = unreal.AssetToolsHelpers().get_asset_tools()
        usr = getpass.getuser().lower()

        # Files
        file_path_ls = glob.glob(os.path.join(content_dir, '**', '*'), recursive=True)
        file_path_ls = [fp.replace('\\', '/') for fp in file_path_ls if os.path.isfile(fp)]
        ext_ls = [os.path.basename(i).split('.')[-1] for i in file_path_ls]
        file_path_ls = [file_path_ls[i] for i in range(len(file_path_ls)) if ext_ls[i] in config.EXTENSION_LS]
        assert len(file_path_ls) >= 2, 'File count less than 2'

        # Read Exists
        files_rec = []
        for fp in file_path_ls:
            if os.stat(fp).st_size <= 1:
                os.remove(fp)
                continue

            name, ext = os.path.basename(fp).split('.')[0], os.path.basename(fp).split('.')[-1]
            asset_path = os.path.abspath(fp).replace(os.path.abspath(content_dir), '')
            asset_path = '/Game' + asset_path.replace('\\', '/')
            package_name = os.path.dirname(asset_path) + f'/{name}'
            asset = editor_asset_library.load_asset(package_name)
            asset_data = editor_asset_library.find_asset_data(package_name)
            if asset_data.asset_name and asset_data.is_redirector():
                editor_asset_library.delete_asset(package_name)
                continue
            # if not asset_data.is_valid():
            # continue

            data = {
                'file_path': fp.replace('\\', '/'),
                'zip_path': None,
                'src_name': None,
                'base_name': os.path.basename(fp),
                'md5_hash': get_md5_file_path(fp),
                'st_mtime': int(os.stat(fp).st_mtime),
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
                        'file_path': os.path.join(project_dir, fn).replace('\\', '/'),
                        'zip_path': z_fp.replace('\\', '/'),
                        'src_name': fn.replace('\\', '/'),
                        'base_name': os.path.basename(fn),
                        'md5_hash': md5_hash,
                        'st_mtime': int(os.stat(z_fp).st_mtime),
                        'size_bytes': info.file_size
                    }
                    files_rec.append(data)

        # DATAFRAME #------------------------------------------------------
        files_rec = sorted(files_rec, key=lambda x: (x['st_mtime'], x['file_path'], x['md5_hash']), reverse=True)
        temp_df = pd.DataFrame.from_records(files_rec)
        temp_df['user'] = temp_df['zip_path'].str.split('__').str[-1].str.split('.').str[0]
        temp_df['user'] = temp_df['user'].fillna(usr)

        backup_df = temp_df[temp_df['zip_path'].notna()].sort_values('st_mtime', ascending=False)
        backup_df = backup_df.groupby('file_path', group_keys=False).head(1)
        backup_df.reset_index(drop=True, inplace=True)

        local_df = temp_df[temp_df['zip_path'].isna()].sort_values('st_mtime', ascending=False)
        local_df = local_df.groupby('file_path', group_keys=False).head(1)
        local_df.reset_index(drop=True, inplace=True)

        df = pd.concat([local_df, backup_df], ignore_index=True)
        df = df.sort_values(['file_path', 'st_mtime'], ascending=[False, False])
        df.reset_index(drop=True, inplace=True)

        # SYNC LOGIC #------------------------------------------------------
        hash_grp = ['file_path', 'md5_hash', 'size_bytes']
        name_grp = ['file_path']
        max_src_mtime = df[df['zip_path'].notnull()]['st_mtime'].max()
        hash_dup_n = df.groupby(hash_grp)['md5_hash'].transform('count')
        df['hash_similar'] = (hash_dup_n == 2)
        name_dup_n = df.groupby(name_grp)['file_path'].transform('count')
        df['name_similar'] = (name_dup_n == 2)

        df['zip'] = df['zip_path'].notna()
        df['local_exists'] = df['file_path'].apply(os.path.exists)
        df['is_lost'] = ~df['local_exists']

        df['is_deleted'] = False
        df.loc[(df['user'] == usr) & df['is_lost'], 'is_deleted'] = True

        df['is_last'] = (
                ((df['st_mtime'] > max_src_mtime) | pd.isna(max_src_mtime)) &
                ~df['hash_similar'] &
                ~df['is_deleted']
        )

        # CONDITIONS #------------------------------------------------------
        is_local = df['zip'] == False
        is_remote = df['zip'] == True
        exists_local = df['local_exists'] == True
        lost_local = ~exists_local & is_local
        deleted_local = df['is_deleted'] == True
        same_file = df['hash_similar'] == True
        different_file = ~same_file
        is_not_zero = df['size_bytes'] > 0
        is_zero = df['size_bytes'] == 0

        # PUSH #------------------------------------------------------
        df['sync_push'] = (
                is_local & exists_local & different_file & is_not_zero
        )
        df['sync_push'] = df.groupby(name_grp)['sync_push'].transform('any')

        # PULL #------------------------------------------------------
        df['sync_pull'] = (
                is_remote &
                ~deleted_local &
                (lost_local | different_file) &
                is_not_zero
        )
        df['sync_pull'] = df.groupby(name_grp)['sync_pull'].transform('any')

        # PUSH DELETE #------------------------------------------------------
        df['sync_push_delete'] = (
                is_remote & deleted_local & is_not_zero
        )
        df['sync_push_delete'] = df.groupby(name_grp)['sync_push_delete'].transform('any')

        # PULL DELETE #------------------------------------------------------
        df['sync_pull_delete'] = (
                is_remote & is_zero & exists_local
        )
        df['sync_pull_delete'] = df.groupby(name_grp)['sync_pull_delete'].transform('any')

        if debug:
            dbug_df = df.copy()
            bool_cols = dbug_df.select_dtypes(include='bool').columns
            dbug_df[bool_cols] = dbug_df[bool_cols].astype(int)
            drop_col_ls = ['file_path', 'zip_path', 'src_name']
            print('ALL DATA FRAME STRING\n' + dbug_df.drop(columns=drop_col_ls).to_string())
        return df

    def get_pull(self):
        df = self.get_all()
        return df[df['sync_pull'] & df['zip_path'].notna()]

    def get_push(self):
        df = self.get_all()
        return df[df['sync_push'] & df['local_exists']]

    def get_push_deleted(self):
        df = self.get_all()
        return df[df['sync_push_delete']]

    def get_pull_deleted(self):
        df = self.get_all()
        return df[df['sync_pull_delete']]