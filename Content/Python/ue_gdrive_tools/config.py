# -*- coding: utf-8 -*-
import os, sys, shutil, json
import unreal

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
CONTENT_DIR = os.path.join(PROJECT_DIR, 'Content')
VERSION_DIR = os.path.join(PROJECT_DIR, '_version_')
os.makedirs(VERSION_DIR, exist_ok=True)

#------------------------------------------------------------
# APIs
#------------------------------------------------------------
#APPDATA_DIR = os.getenv('APPDATA')
#APPDATA_TOOL_DIR = os.path.join(APPDATA_DIR, 'UG_DriveTool')
SETTING_DIR = os.path.join(ROOT_DIR, 'setting')
os.makedirs(SETTING_DIR, exist_ok=True)
CREDS_PATH = os.path.join(SETTING_DIR, 'client_secret.json')
TOKEN_PATH = os.path.join(SETTING_DIR, 'token.json')
PROJECT_DIR_ID_PATH =  os.path.join(SETTING_DIR, 'gdrive_folder_id.txt')
if not os.path.exists(PROJECT_DIR_ID_PATH):
    with open(PROJECT_DIR_ID_PATH, 'x') as f:
        f.close()
PROJECT_DIR_ID = None if not open(PROJECT_DIR_ID_PATH).read() else open(PROJECT_DIR_ID_PATH).read()
#------------------------------------------------------------