# -*- coding: utf-8 -*-
__version__ = "0.1.7"

import json, os, sys, time, subprocess, glob, shutil
import unreal
from importlib import reload

# --------------------------------
print(f"{__name__}  version: {__version__}")
print(f"python version: {sys.version}")

# -------------------------------
# Package imports
# -------------------------------
from . import config

print("importing..")
from . import menu

print("gd_util")
from . import gd_utils

print("ver_util")
from . import ver_utils

# Reload only utility modules (safe)
print("reloading..")
reload(gd_utils)
reload(ver_utils)

# -------------------------------
# Paths
# -------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
system_library = unreal.SystemLibrary
project_dir = system_library.get_project_directory()

gdrive = None

if __name__ != "__main__":
    print(
        ".\nStarting...\n"
        + """'

  _   _ _____     ____ ____  ____  _____     _______   _____ ___   ___  _     ____  
 | | | | ____|   / ___|  _ \|  _ \|_ _\ \   / / ____| |_   _/ _ \ / _ \| |   / ___| 
 | | | |  _|    | |  _| | | | |_) || | \ \ / /|  _|     | || | | | | | | |   \___ \ 
 | |_| | |___   | |_| | |_| |  _ < | |  \ V / | |___    | || |_| | |_| | |___ ___) |
  \___/|_____|   \____|____/|_| \_\___|  \_/  |_____|   |_| \___/ \___/|_____|____/ 


    """
    )


class editor_utils:
    editor_load_save_util = unreal.EditorLoadingAndSavingUtils
    editor_asset_library = unreal.EditorAssetLibrary()

    @staticmethod
    def get_asset_from_file(full_file_path):
        """
        :param full_file_path:
        :return: asset object
        """
        print(full_file_path)
        project_dir = config.PROJECT_DIR.replace("\\", "/")
        print(project_dir)
        asset_dir = os.path.dirname(full_file_path).replace("\\", "/")
        print(asset_dir)
        assert full_file_path.count(".") == 1
        name, ext = os.path.basename(full_file_path).split(".")
        asset_path = "/".join([asset_dir, name])
        print(asset_path)
        asset_path = asset_path.replace("\\", "/").replace(project_dir, "")
        print(asset_path)
        asset_path = asset_path.replace("Content/", "/Game/")
        print(asset_path)
        asset = editor_utils.editor_asset_library.load_asset(asset_path)
        print(asset)
        return asset

    @staticmethod
    def get_dirty_list():
        cont_dirty_package_ls = (
            editor_utils.editor_load_save_util.get_dirty_content_packages()
        )
        map_dirty_package_ls = (
            editor_utils.editor_load_save_util.get_dirty_map_packages()
        )
        package_path_ls = [
            i.get_path_name() for i in cont_dirty_package_ls + map_dirty_package_ls
        ]
        return package_path_ls

    @staticmethod
    def is_asset_dirty(asset):
        """
        :param asset:
        :return: bool
        """
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
    """
    :return:
    """
    print(".\n--------\nCommit_new_version\n--------\n")
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
        unreal.EditorDialog.show_message(
            title="Upload Successful",
            message="Your latest changes were successfully committed and uploaded to Google Drive!",
            message_type=unreal.AppMsgType.OK,
            default_value=unreal.AppReturnType.OK
        )
    else:
        os.remove(zip_path)


def _get_package_update():
    """
    :return:
    """

    def fetch_all_versions():
        print(".\n--------\nFetch_all_versions\n--------\n")
        global gdrive
        gdrive = gd_utils.drive_handler() if not gdrive else gdrive
        file_items = gdrive.list_files_in_drive(config.PROJECT_DIR_ID)
        version_dir_id = file_items.get(os.path.basename(config.VERSION_DIR))
        if not version_dir_id:
            raise Warning("Fetch failed")
        file_items = gdrive.list_files_in_drive(version_dir_id)
        for fn in file_items:
            f_id = file_items[fn]
            dest_path = os.path.join(config.VERSION_DIR, fn).replace("\\", "/")
            if not os.path.exists(dest_path):
                gdrive.download_file(f_id, dest_path)

    def run_restart_cli():
        print("Python exists:", os.path.exists(config.PYTHON_PATH))
        print("CLI exists:", os.path.exists(config.CLI_PATH))
        cmd = [
            config.PYTHON_PATH,
            config.CLI_PATH,
            "restart",
            "-file_path",
            config.PULL_VERSION_LIST_PATH,
            "-ueditor_path",
            sys.executable,
            "-project_path",
            config.PROJECT_PATH,
        ]
        subprocess.Popen(cmd)
        system_library = unreal.SystemLibrary
        system_library.quit_editor()

    print(".\n--------\nGet_package_update\n--------\n")
    fetch_all_versions()
    db = ver_utils.database()
    pull_df = db.get_pull()
    pull_del_df = db.get_pull_deleted()

    ver_utils.log_file.delete_pull_version()
    if pull_df.height == 0 and pull_del_df.height == 0:
        _commit_new_version()
        print(".\n--------\nProject: All assets have already Up to Date!\n--------\n")
        return
    else:
        print(
            ".\n--------\nProject: Found new modified, About to reload UEditor.\n--------\n"
        )

        for row in pull_df.iter_rows(named=True):
            zip_path = row["zip_path"]
            if not zip_path:
                continue
            sub_path = row["src_name"]
            print(f"> Add pull update task: {sub_path}")
            ver_utils.log_file.pull_version(zip_path, sub_path, 1)

        for row in pull_del_df.iter_rows(named=True):
            zip_path = row["zip_path"]
            if not zip_path:
                continue
            sub_path = row["src_name"]
            print(f"> Add pull delete task: {sub_path}")
            ver_utils.log_file.pull_version(zip_path, sub_path, 0)

        ed = unreal.EditorDialog.show_message(
            title="Confirm Action",
            message="Found new asset update\nWant to reload?",
            message_type=unreal.AppMsgType.YES_NO,
            default_value=unreal.AppReturnType.NO,
        )
        if ed == unreal.AppReturnType.YES:
            editor_utils.save_all_with_dialog()
            run_restart_cli()


def save():
    _commit_new_version()


def load():
    _get_package_update()


def sync():
    _commit_new_version()
    _get_package_update()


def init_tool_menus():
    try:
        ui = menu.UI()
        ui._clear_sub_menu()
        ui._create_tool_menus()
        unreal.log("gDrive UI initialized successfully.")
    except Exception as e:
        unreal.log_error(f"Failed to initialize gDrive UI: {e}")
