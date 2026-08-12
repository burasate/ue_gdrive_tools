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
def get_hash_file_path(file_path):
    hash_md5 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_hash_file_obj(file_obj):
    hash_md5 = hashlib.sha256()
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
    ACTION_NOOP = 'noop'
    ACTION_PUSH = 'push'
    ACTION_PULL = 'pull'
    ACTION_PUSH_DELETE = 'push_delete'
    ACTION_PULL_DELETE = 'pull_delete'

    def __init__(self):
        self._cache_df = None

    @staticmethod
    def _is_tracked_path(path):
        return os.path.splitext(path)[1].lstrip('.').lower() in config.EXTENSION_LS

    @staticmethod
    def _parse_zip_metadata(zip_path):
        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        parts = zip_name.split('__', 1)
        ts_part = parts[0]
        user = parts[1].lower() if len(parts) > 1 and parts[1] else None
        try:
            commit_ts = int(datetime.strptime(ts_part, '%Y%m%d_%H%M%S').timestamp())
        except Exception:
            commit_ts = int(os.stat(zip_path).st_mtime)
        return commit_ts, user

    @staticmethod
    def _remote_record_is_newer(candidate, current):
        if current is None:
            return True
        candidate_key = (candidate['remote_commit_ts'], candidate['zip_path'])
        current_key = (current['remote_commit_ts'], current['zip_path'])
        return candidate_key > current_key

    @staticmethod
    def _empty_df():
        return pl.DataFrame({
            'file_path': pl.Series('file_path', [], dtype=pl.Utf8),
            'base_name': pl.Series('base_name', [], dtype=pl.Utf8),
            'local_exists': pl.Series('local_exists', [], dtype=pl.Boolean),
            'local_hash': pl.Series('local_hash', [], dtype=pl.Utf8),
            'local_st_mtime': pl.Series('local_st_mtime', [], dtype=pl.Int64),
            'local_size_bytes': pl.Series('local_size_bytes', [], dtype=pl.Int64),
            'zip_path': pl.Series('zip_path', [], dtype=pl.Utf8),
            'src_name': pl.Series('src_name', [], dtype=pl.Utf8),
            'remote_hash': pl.Series('remote_hash', [], dtype=pl.Utf8),
            'remote_commit_ts': pl.Series('remote_commit_ts', [], dtype=pl.Int64),
            'remote_size_bytes': pl.Series('remote_size_bytes', [], dtype=pl.Int64),
            'user': pl.Series('user', [], dtype=pl.Utf8),
            'remote_is_tombstone': pl.Series('remote_is_tombstone', [], dtype=pl.Boolean),
            'same_hash': pl.Series('same_hash', [], dtype=pl.Boolean),
            'sync_action': pl.Series('sync_action', [], dtype=pl.Utf8),
            'sync_reason': pl.Series('sync_reason', [], dtype=pl.Utf8),
        })

    def _scan_local_assets(self):
        import unreal

        editor_asset_library = unreal.EditorAssetLibrary()
        local_assets = {}
        file_path_ls = glob.glob(os.path.join(content_dir, '**', '*'), recursive=True)
        file_path_ls = [fp.replace('\\', '/') for fp in file_path_ls if os.path.isfile(fp)]
        file_path_ls = [fp for fp in file_path_ls if self._is_tracked_path(fp)]

        for fp in file_path_ls:
            stat = os.stat(fp)
            if stat.st_size <= 1:
                continue

            name = os.path.splitext(os.path.basename(fp))[0]
            asset_path = os.path.abspath(fp).replace(os.path.abspath(content_dir), '')
            asset_path = '/Game' + asset_path.replace('\\', '/')
            package_name = os.path.dirname(asset_path) + f'/{name}'

            try:
                asset_data = editor_asset_library.find_asset_data(package_name)
                if asset_data.asset_name and asset_data.is_redirector():
                    continue
            except Exception:
                pass

            local_assets[fp] = {
                'file_path': fp,
                'base_name': os.path.basename(fp),
                'local_hash': get_hash_file_path(fp),
                'local_st_mtime': int(stat.st_mtime),
                'local_size_bytes': int(stat.st_size),
            }
        return local_assets

    def _scan_remote_heads(self, current_user):
        remote_heads = {}
        zip_path_ls = sorted(glob.glob(f'{version_dir}/*.zip'))
        for z_fp in zip_path_ls:
            commit_ts, parsed_user = self._parse_zip_metadata(z_fp)
            remote_user = parsed_user or current_user
            with zipfile.ZipFile(z_fp, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    fn = info.filename.replace('\\', '/')
                    if fn.endswith('/') or not self._is_tracked_path(fn):
                        continue

                    file_path = os.path.join(project_dir, fn).replace('\\', '/')
                    with zip_ref.open(info.filename) as f:
                        remote_hash = get_hash_file_obj(f)

                    candidate = {
                        'file_path': file_path,
                        'base_name': os.path.basename(fn),
                        'zip_path': z_fp.replace('\\', '/'),
                        'src_name': fn,
                        'remote_hash': remote_hash,
                        'remote_commit_ts': commit_ts,
                        'remote_size_bytes': int(info.file_size),
                        'remote_is_tombstone': int(info.file_size) == 0,
                        'user': remote_user,
                    }
                    current = remote_heads.get(file_path)
                    if self._remote_record_is_newer(candidate, current):
                        remote_heads[file_path] = candidate
        return remote_heads

    def _decide_action(self, local_rec, remote_rec, current_user):
        if local_rec and not remote_rec:
            return self.ACTION_PUSH, 'local_only'

        if not local_rec and not remote_rec:
            return self.ACTION_NOOP, 'missing_both'

        if not local_rec and remote_rec:
            if remote_rec['remote_is_tombstone']:
                return self.ACTION_NOOP, 'remote_tombstone_only'
            if remote_rec['user'] == current_user:
                return self.ACTION_PUSH_DELETE, 'local_missing_remote_owned_by_current_user'
            return self.ACTION_PULL, 'local_missing_remote_exists'

        if local_rec and remote_rec['remote_is_tombstone']:
            if remote_rec['remote_commit_ts'] >= local_rec['local_st_mtime']:
                return self.ACTION_PULL_DELETE, 'remote_tombstone_newer'
            return self.ACTION_PUSH, 'local_restores_remote_tombstone'

        same_hash = (
            local_rec['local_hash'] == remote_rec['remote_hash']
            and local_rec['local_size_bytes'] == remote_rec['remote_size_bytes']
        )
        if same_hash:
            return self.ACTION_NOOP, 'matching_hash'

        local_ts = local_rec['local_st_mtime']
        remote_ts = remote_rec['remote_commit_ts']
        if local_ts >= remote_ts:
            reason = 'local_newer' if local_ts > remote_ts else 'local_tie_break'
            return self.ACTION_PUSH, reason
        return self.ACTION_PULL, 'remote_newer'

    def _build_all(self):
        usr = getpass.getuser().lower()
        local_assets = self._scan_local_assets()
        remote_heads = self._scan_remote_heads(usr)
        all_paths = sorted(set(local_assets) | set(remote_heads))

        if not all_paths:
            return self._empty_df()

        records = []
        for file_path in all_paths:
            local_rec = local_assets.get(file_path)
            remote_rec = remote_heads.get(file_path)
            sync_action, sync_reason = self._decide_action(local_rec, remote_rec, usr)
            same_hash = bool(
                local_rec and remote_rec
                and not remote_rec['remote_is_tombstone']
                and local_rec['local_hash'] == remote_rec['remote_hash']
                and local_rec['local_size_bytes'] == remote_rec['remote_size_bytes']
            )
            records.append({
                'file_path': file_path,
                'base_name': os.path.basename(file_path),
                'local_exists': local_rec is not None,
                'local_hash': None if not local_rec else local_rec['local_hash'],
                'local_st_mtime': None if not local_rec else local_rec['local_st_mtime'],
                'local_size_bytes': None if not local_rec else local_rec['local_size_bytes'],
                'zip_path': None if not remote_rec else remote_rec['zip_path'],
                'src_name': None if not remote_rec else remote_rec['src_name'],
                'remote_hash': None if not remote_rec else remote_rec['remote_hash'],
                'remote_commit_ts': None if not remote_rec else remote_rec['remote_commit_ts'],
                'remote_size_bytes': None if not remote_rec else remote_rec['remote_size_bytes'],
                'user': usr if not remote_rec else remote_rec['user'],
                'remote_is_tombstone': False if not remote_rec else remote_rec['remote_is_tombstone'],
                'same_hash': same_hash,
                'sync_action': sync_action,
                'sync_reason': sync_reason,
            })
        empty_schema = self._empty_df().schema
        return pl.DataFrame(records, schema=empty_schema)

    def get_all(self, debug=False, refresh=False):
        if refresh or self._cache_df is None:
            self._cache_df = self._build_all()
        df = self._cache_df
        if debug:
            print('ALL DATA FRAME STRING\n' + str(df))
        return df

    def get_pull(self):
        df = self.get_all()
        return df.filter(pl.col('sync_action') == self.ACTION_PULL)

    def get_push(self):
        df = self.get_all()
        return df.filter(pl.col('sync_action') == self.ACTION_PUSH)

    def get_push_deleted(self):
        df = self.get_all()
        return df.filter(pl.col('sync_action') == self.ACTION_PUSH_DELETE)

    def get_pull_deleted(self):
        df = self.get_all()
        return df.filter(pl.col('sync_action') == self.ACTION_PULL_DELETE)