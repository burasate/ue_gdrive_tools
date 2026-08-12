# -*- coding: utf-8 -*-
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(__file__))
import config
import unreal

binaries_dir = config.BINARIES_DIR
python_path = config.PYTHON_PATH
pip_path = config.PIP_PATH
tool_dir = config.ROOT_DIR
pip_requirements_path = tool_dir + os.sep + 'requirements.txt'
assert os.path.exists(pip_requirements_path)

'''
import ue_gdrive_tools.core as ugdrive
ugdrive.init_tool_menus()
'''

def _create_tool_python(*_):
    cmd = '''
import sys, os, builtins, importlib
import unreal

### Environment ###
with open(\'{2}\') as f:
    pth = f.read()
if not \'{0}\' in sys.path:
    sys.path.insert(0, \'{0}\')

module_name = \'{1}.core\'
ugdrive = importlib.import_module(module_name)
builtins.ugdrive = ugdrive
ugdrive.init_tool_menus()
'''.strip().format(
        os.path.dirname(config.ROOT_DIR).replace('\\', '/'),
        os.path.basename(config.ROOT_DIR),
        config.TOOL_PTH_DESIRE_PATH.replace('\\', '/')
    )

    with open(config.TOOL_INIT_PATH, 'w') as f:
        f.write(cmd)

def _create_init_unreal():
    cmd = """
# ------------------------------- 
# gDrive Tools Starting up 
# -------------------------------
import unreal
import os

tools_dir = os.path.dirname(__file__)
tool_path = os.path.join(tools_dir, \"{0}.py\")
install_path = os.path.join(tools_dir, \"ue_{0}\", "install.py")

editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor_world = editor_subsystem.get_editor_world()

if os.path.exists(tool_path):
    cmd = 'py ' + tool_path
else:
    cmd = 'py ' + install_path
unreal.SystemLibrary.execute_console_command(editor_world, cmd)
""".strip().format(
        config.TOOL_MODULE_NAME
    )
    with open(config.INIT_UNREAL_PATH, 'w') as f:
            f.write(cmd)

def run_install(*_):
    # call pip install
    #r = subprocess.run([python_path, "-m", "pip", 'install', "-r", pip_requirements_path], capture_output=True)
    r = subprocess.run(
        [python_path, "-m", "pip", "install", "--force-reinstall", "-r", pip_requirements_path],
        capture_output=True)
    #print(r.stdout.decode())

    # call module list
    r = subprocess.run([python_path, "-m", "pip", "list"], capture_output=True)
    #print(r.stdout.decode())

    # test env
    #if not os.path.dirname(tool_dir) in sys.path:
        #sys.path.insert(0, os.path.dirname(tool_dir))

    # sys path list
    for fp in sys.path:
        print([int(os.path.exists(fp)), fp])

    # set path desire
    with open(config.TOOL_PTH_DESIRE_PATH, 'w') as f:
        f.write(f'{tool_dir}')

    # init_tool.py
    _create_tool_python()
    _create_init_unreal()

    print('.\n=============\nINSTALLATION\'S DONE\n=============')

    # Restart U-Editor
    import unreal, time
    system_library = unreal.SystemLibrary
    project_dir = system_library.get_project_directory()
    u_proj_path_ls = [os.path.join(project_dir, i) for i in os.listdir(project_dir) if i.endswith('.uproject')]
    cur_proj = u_proj_path_ls[0]
    print(f'Reloading UProject {os.path.basename(cur_proj)}')
    subprocess.Popen([sys.executable, cur_proj])
    time.sleep(5)
    system_library.quit_editor()

if __name__ == '__main__':
    if os.path.exists(config.TOOL_INIT_PATH):
        print("UE GDrive Tools is already installed.")
        sys.exit(0)
        
    ed = unreal.EditorDialog.show_message(
        title="Confirm Action",
        message="Do you want to proceed installation \"UE GDrive Tools\" on this PROJECT?",
        message_type=unreal.AppMsgType.YES_NO,
        default_value=unreal.AppReturnType.NO
    )
    if ed == unreal.AppReturnType.YES:
        run_install()