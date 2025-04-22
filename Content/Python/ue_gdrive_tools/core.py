# -*- coding: utf-8 -*-
import json, os, sys, time, subprocess, glob, shutil
from importlib import reload
import unreal

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

pycache_dirs = glob.glob(os.path.join(base_dir, "**", "__pycache__"), recursive=True)
for path in pycache_dirs:
    try:
        shutil.rmtree(path)
    except:
        pass

class editor_utils:
    editor_load_save_util = unreal.EditorLoadingAndSavingUtils
    editor_asset_library = unreal.EditorAssetLibrary()

    @staticmethod
    def get_asset_from_file(full_file_path):
        '''
        :param full_file_path:
        :return: asset object
        '''
        print(full_file_path)
        project_dir = config.PROJECT_DIR.replace('\\', '/')
        print(project_dir)
        asset_dir = os.path.dirname(full_file_path).replace('\\', '/')
        print(asset_dir)
        assert full_file_path.count('.') == 1
        name, ext = os.path.basename(full_file_path).split('.')
        asset_path = '/'.join([asset_dir, name])
        print(asset_path)
        asset_path = asset_path.replace('\\', '/').replace(project_dir, '')
        print(asset_path)
        asset_path = asset_path.replace('Content/', '/Game/')
        print(asset_path)
        asset = editor_utils.editor_asset_library.load_asset(asset_path)
        print(asset)
        return asset

    @staticmethod
    def get_dirty_list():
        cont_dirty_package_ls = editor_utils.editor_load_save_util.get_dirty_content_packages()
        map_dirty_package_ls = editor_utils.editor_load_save_util.get_dirty_map_packages()
        package_path_ls = [i.get_path_name() for i in cont_dirty_package_ls + map_dirty_package_ls]
        return package_path_ls

    @staticmethod
    def is_asset_dirty(asset):
        '''
        :param asset:
        :return: bool
        '''
        package_path_ls = editor_utils.get_dirty_list()
        if asset.get_path_name() in package_path_ls:
            return True
        else:
            return False

    @staticmethod
    def save_all_with_dialog():
        editor_utils.editor_load_save_util.save_dirty_packages_with_dialog(True, True)

    @staticmethod
    def save_all():
        editor_utils.editor_load_save_util.save_dirty_packages_with_dialog(True, True)


def _commit_new_version():
    '''
    :return:
    '''
    print('.\n--------\nCommit_new_version\n--------\n')
    if editor_utils.get_dirty_list():
        editor_utils.save_all_with_dialog()

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

def _get_package_update():
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

    def run_restart_cli():
        print("Python exists:", os.path.exists(config.PYTHON_PATH))
        print("CLI exists:", os.path.exists(config.CLI_PATH))
        cmd = [
            config.PYTHON_PATH, config.CLI_PATH, 'restart',
            '-file_path', config.PULL_VERSION_LIST_PATH,
            '-ueditor_path', sys.executable,
            '-project_path', config.PROJECT_PATH
        ]
        subprocess.Popen(cmd)
        system_library = unreal.SystemLibrary
        system_library.quit_editor()

    print('.\n--------\nGet_package_update\n--------\n')
    fetch_all_versions()
    db = ver_utils.database()
    pull_df = db.get_pull()
    pull_del_df = db.get_pull_deleted()

    ver_utils.log_file.delete_pull_version()
    if not pull_df.index.tolist() and not pull_del_df.index.tolist():
        _commit_new_version()
        print('.\n--------\nProject: Already Up to Date!\n--------\n')
        return
    else:
        print('.\n--------\nProject: Found new modified, About to reload UEditor.\n--------\n')

        for i in pull_df.index.tolist():
            row = pull_df.loc[i]
            zip_path = row['zip_path']
            if not row['zip_path']: continue
            sub_path = row['src_name']
            print(f'> Add pull update task: {sub_path}')
            log_pull = ver_utils.log_file.pull_version(zip_path, sub_path, 1)

        for i in pull_del_df.index.tolist():
            row = pull_del_df.loc[i]
            zip_path = row['zip_path']
            if not row['zip_path']: continue
            sub_path = row['src_name']
            print(f'> Add pull delete task: {sub_path}')
            log_pull = ver_utils.log_file.pull_version(zip_path, sub_path, 0)

        ed = unreal.EditorDialog.show_message(
            title="Confirm Action",
            message="Found new asset update\nWant to reload?",
            message_type=unreal.AppMsgType.YES_NO,
            default_value=unreal.AppReturnType.NO
        )
        if ed == unreal.AppReturnType.YES:
            editor_utils.save_all_with_dialog()
            run_restart_cli()

def save():
    _commit_new_version()

def load():
    _get_package_update()

def run(): # Dev test
    save()
    load()