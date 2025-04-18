# -*- coding: utf-8 -*-
from importlib import reload
import unreal
import json, os, sys, time

from . import gd_utils
from . import ver_utils
from . import config
reload(gd_utils)
reload(ver_utils)
reload(config)

base_dir = os.path.dirname( os.path.abspath(__file__) )
system_library = unreal.SystemLibrary
project_dir = system_library.get_project_directory()
gdrive = None

class editor_utils:
    @staticmethod
    def save_all():
        ls_util = unreal.EditorLoadingAndSavingUtils
        ls_util.save_dirty_packages_with_dialog(True, True)

def commit_new_version():
    '''
    :return:
    '''
    print('.\n--------\nCommit_new_version\n--------\n')
    editor_utils.save_all()
    zip_path = ver_utils.update_version_zip()
    if not zip_path:
        return

    global gdrive
    gdrive = gd_utils.drive_handler() if not gdrive else gdrive
    file_items = gdrive.list_files_in_drive(config.PROJECT_DIR_ID)
    version_dir_id = file_items.get(os.path.basename(config.VERSION_DIR))
    if version_dir_id:
        gdrive.upload_file(zip_path, version_dir_id)
    else:
        os.remove(zip_path)

def get_package_update():
    '''
    :return:
    '''
    def fetch_all_versions():
        print('.\n--------\nFetch_all_versions\n--------\n')
        global gdrive
        gdrive = gd_utils.drive_handler() if not gdrive else gdrive
        file_items = gdrive.list_files_in_drive(config.PROJECT_DIR_ID)
        version_dir_id = file_items.get(os.path.basename(config.VERSION_DIR))
        if not version_dir_id:
            raise Warning('Fetch failed')
        file_items = gdrive.list_files_in_drive(version_dir_id)
        for fn in file_items:
            f_id = file_items[fn]
            dest_path = os.path.join(config.VERSION_DIR, fn).replace('\\', '/')
            if not os.path.exists(dest_path):
                gdrive.download_file(f_id, dest_path)
        ver_utils.update_version_zip()

    print('.\n--------\nGet_package_update\n--------\n')
    fetch_all_versions()
    time.sleep(3)
    files_df = ver_utils.load_files_data()
    pull_df = files_df[files_df['sync_pull']]
    if not pull_df.index.tolist():
        print('Already up to date.')
        return
    for i in pull_df.index.tolist():
        row = pull_df.loc[i]
        fp = row['file_path']
        print(fp, row['sync_pull'])
        ver_utils.zip_extract_file(row['source'], row['src_name'])

def run(): # Dev test
    get_package_update()
    commit_new_version()
