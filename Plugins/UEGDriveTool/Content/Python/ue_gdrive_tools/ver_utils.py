# -*- coding: utf-8 -*-
import os, sys, hashlib, json, getpass, glob, time
from datetime import datetime, timezone
from importlib import reload
import zipfile36 as zipfile
from . import config

import polars as pl
#print(f'polars version: {pl.show_versions()}')

pl.Config.set_tbl_cols(-1)  # show all columns
pl.Config.set_tbl_width_chars(1000)

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
    push_df = push_df.unique(subset='file_path', keep='first')
    push_del_df = db.get_push_deleted()
    push_del_df = push_del_df.unique(subset='file_path', keep='first')
    #print('PUSH DF\n' + push_df.to_string())
    #print('PUSH DELETE DF\n' + push_del_df.to_string())

    # Create 0 bytes files to inform the other that files were deleted
    del_files = [i for i in push_del_df['file_path'].to_list()]
    for fp in [i for i in del_files if not os.path.exists(i)]:
        print(f'create delete mock up file: {os.path.abspath(fp)}')
        dir_name = os.path.dirname(fp)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        os.chmod(dir_name, 0o777)
        with open(fp, 'wb') as f:
            f.close()

    push_files = [i for i in push_df['file_path'].to_list() if os.path.exists(i)]
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
        temp_df = pl.DataFrame(files_rec)
        #temp_df = temp_df.with_columns(temp_df['zip_path'].str.split('__').list.get(-1).str.split('.').list.get(0).alias('user'))
        temp_df = temp_df.with_columns(
        pl.col("zip_path").cast(pl.Utf8)
        .str.split("__").list.get(-1)
        .str.split(".").list.get(0)
        .alias("user"))   
        temp_df = temp_df.with_columns(pl.col('user').fill_null(usr))

        backup_df = (temp_df.filter(pl.col('zip_path').is_not_null()).sort('st_mtime', descending=True))
        backup_df = backup_df.sort('st_mtime', descending=True).unique(subset='file_path', keep='first')
        #backup_df = backup_df.drop('index').with_row_count(name='index')

        local_df = (temp_df.filter(pl.col('zip_path').is_null()).sort('st_mtime', descending=True))
        local_df = local_df.sort('st_mtime', descending=True).unique(subset='file_path', keep='first')
        #local_df = local_df.drop('index').with_row_count(name='index')

        df = pl.concat([local_df, backup_df])
        df = df.sort(['file_path', 'st_mtime'], descending=[True, True])
        #df = df.drop('index').with_row_count(name='index')

        # SYNC LOGIC #------------------------------------------------------
        hash_grp = ['file_path', 'md5_hash', 'size_bytes']
        name_grp = ['file_path']
        max_src_mtime = df.filter(pl.col('zip_path').is_not_null())['st_mtime'].max()
        hash_dup_n = df.select(pl.count('md5_hash').over(hash_grp).alias('hash_dup_n'))['hash_dup_n']
        df = df.with_columns((hash_dup_n >= 2).alias('hash_similar'))
        name_dup_n = df.select(pl.count('file_path').over(name_grp).alias('name_dup_n'))['name_dup_n']
        df = df.with_columns((name_dup_n >= 2).alias('name_similar'))

        df = df.with_columns(pl.col('zip_path').is_not_null().alias('zip'))
        df = df.with_columns(pl.Series('local_exists', [os.path.exists(p) for p in df['file_path']]))
        df = df.with_columns((~pl.col('local_exists')).alias('is_lost'))

        df = df.with_columns(((pl.col('user') == usr) & pl.col('is_lost')).alias('is_deleted'))

        local_latest = (
            df.filter(~pl.col('zip'))
            .sort(['file_path', 'st_mtime'], descending=[False, True])
            .unique(subset='file_path', keep='first')
            .select(['file_path', 'st_mtime'])
            .rename({'st_mtime': 'local_st_mtime'})
        )
        df = df.join(local_latest, on='file_path', how='left')

        df = df.with_columns(
            (
                    (pl.col('st_mtime') == pl.col('local_st_mtime')) &
                    (pl.col('size_bytes') > 0) &
                    ~pl.col('is_deleted') &
                    (pl.col('hash_similar') == False)
            ).alias('is_last')
        )

        # CONDITIONS #------------------------------------------------------
        is_owner = pl.col('user') == usr
        is_local = ~pl.col('zip') & is_owner
        is_remote = pl.col('zip')
        exists_local = pl.col('local_exists')
        lost_local = ~exists_local & is_local
        deleted_local = pl.col('is_deleted')
        same_file = pl.col('hash_similar')
        different_file = ~same_file
        is_not_zero = pl.col('size_bytes') > 0
        is_zero = pl.col('size_bytes') == 0
        remote_is_newer = pl.col('st_mtime') > pl.col('local_st_mtime')

        # PUSH #------------------------------------------------------
        df = df.with_columns(
            (is_local & exists_local & different_file & is_not_zero).alias('sync_push')
        )
        df = df.with_columns(pl.col('sync_push').any().over(name_grp).alias('sync_push'))

        # PULL #------------------------------------------------------
        df = df.with_columns(
            (is_remote & (~deleted_local) & (lost_local | different_file) & is_not_zero).alias('sync_pull')
        )
        df = df.with_columns(pl.col('sync_pull').any().over(name_grp).alias('sync_pull'))

        # PUSH DELETE #------------------------------------------------------
        df = df.with_columns(
            (is_local & deleted_local).alias('sync_push_delete')
        )
        df = df.with_columns(pl.col('sync_push_delete').any().over(name_grp).alias('sync_push_delete'))

        # PULL DELETE #------------------------------------------------------
        df = df.with_columns(
            (
                    is_remote &
                    is_zero &
                    exists_local &
                    ~is_owner &
                    remote_is_newer
            ).alias('sync_pull_delete')
        )
        df = df.with_columns(pl.col('sync_pull_delete').any().over(name_grp).alias('sync_pull_delete'))

        if debug:
            dbug_df = df.clone()
            bool_cols = [c for c, dtype in zip(dbug_df.columns, dbug_df.dtypes) if dtype == pl.Boolean]
            for col in bool_cols:
                dbug_df = dbug_df.with_columns(pl.col(col).cast(pl.Int32))
            drop_col_ls = ['file_path', 'zip_path', 'src_name']
            print('ALL DATA FRAME STRING\n' + dbug_df.drop(drop_col_ls).to_string())
        return df

    def get_pull(self):
        df = self.get_all()
        return df.filter(pl.col('sync_pull') & pl.col('zip_path').is_not_null())

    def get_push(self):
        df = self.get_all()
        return df.filter(pl.col('sync_push') & pl.col('local_exists'))

    def get_push_deleted(self):
        df = self.get_all()
        return df.filter(pl.col('sync_push_delete'))

    def get_pull_deleted(self):
        df = self.get_all()
        return df.filter(pl.col('sync_pull_delete'))