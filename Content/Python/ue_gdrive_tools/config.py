# -*- coding: utf-8 -*-
import os, sys, shutil, json, tempfile
import unreal

EXTENSION_LS = ['uproject', 'umap', 'uasset']

#------------------------------------------------------------
# UE SYS PATH
#------------------------------------------------------------
assert os.path.basename(sys.executable) == 'UnrealEditor.exe', 'Please run the script on Unreal Editor'
BINARIES_DIR = os.path.abspath(sys.executable).split(os.sep)[:-2]
BINARIES_DIR = os.sep.join(BINARIES_DIR)
PYTHON_PATH = os.path.abspath(  BINARIES_DIR + os.sep + 'ThirdParty\\Python3\\Win64\\python.exe' )
assert os.path.exists(PYTHON_PATH)
PIP_PATH = os.path.abspath( BINARIES_DIR + os.sep + 'ThirdParty\\Python3\\Win64\\Scripts\\pip.exe' )
assert os.path.exists(PIP_PATH)

#------------------------------------------------------------
# TOOL PATH
#------------------------------------------------------------
ROOT_DIR = os.path.dirname( os.path.abspath(__file__) )
PROJECT_DIR = unreal.SystemLibrary.get_project_directory()
uproject_files = [os.path.join(PROJECT_DIR, fp) for fp in os.listdir(PROJECT_DIR) if fp.endswith('.uproject')]
if not uproject_files:
    raise FileNotFoundError(f"No .uproject file found in {PROJECT_DIR}")
PROJECT_PATH = uproject_files[0]
del uproject_files
PROJECT_PATH = [os.path.join(PROJECT_DIR, fp) for fp in os.listdir(PROJECT_DIR) if fp.endswith('.uproject')][0]
CONTENT_DIR = os.path.join(PROJECT_DIR, 'Content')
VERSION_DIR = os.path.join(PROJECT_DIR, '_version_')
os.makedirs(VERSION_DIR, exist_ok=True)
LOG_DIR = os.path.join(ROOT_DIR, 'log')
os.makedirs(LOG_DIR, exist_ok=True)

TOOL_MODULE_NAME = 'gdrive_tools'
CONTENT_PYTHON_DIR = os.path.join(CONTENT_DIR, 'Python')
os.makedirs(CONTENT_PYTHON_DIR, exist_ok=True)
TOOL_PTH_DESIRE_PATH = os.path.join(CONTENT_PYTHON_DIR, f'{TOOL_MODULE_NAME}__pth')
TOOL_INIT_PATH = os.path.join(CONTENT_PYTHON_DIR, TOOL_MODULE_NAME + '.py')
INIT_UNREAL_PATH = os.path.join(CONTENT_PYTHON_DIR, 'init_unreal.py')

#------------------------------------------------------------
# CLI PATH
#------------------------------------------------------------
PULL_VERSION_LIST_PATH = os.path.join(LOG_DIR, 'package_pull_version.json')
CLI_PATH = os.path.join(ROOT_DIR, 'tools_cli.py')

#------------------------------------------------------------
# APIs
#------------------------------------------------------------
SETTING_DIR = os.path.join(CONTENT_PYTHON_DIR, f'{TOOL_MODULE_NAME}__setting')
os.makedirs(SETTING_DIR, exist_ok=True)
SA_PATH = os.path.join(SETTING_DIR, 'service_account')
SA_BIN_PATH = os.path.join(SETTING_DIR, 'service_account.bin')
PROJECT_DIR_ID_PATH =  os.path.join(SETTING_DIR, 'gdrive_folder_id')
if not os.path.exists(PROJECT_DIR_ID_PATH):
    with open(PROJECT_DIR_ID_PATH, 'x') as f:
        f.close()
PROJECT_DIR_ID = None if not open(PROJECT_DIR_ID_PATH).read() else open(PROJECT_DIR_ID_PATH).read()
#------------------------------------------------------------