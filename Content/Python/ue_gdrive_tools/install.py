# -*- coding: utf-8 -*-
import sys, os, subprocess, unreal
assert os.path.basename(sys.executable) == 'UnrealEditor.exe', 'Please run the script on Unreal Editor'

binaries_dir = os.path.abspath(sys.executable).split(os.sep)[:-2]
binaries_dir = os.sep.join(binaries_dir)
python_path = os.path.abspath(  binaries_dir + os.sep + 'ThirdParty\\Python3\\Win64\\python.exe' )
assert os.path.exists(python_path)
pip_path = os.path.abspath( binaries_dir + os.sep + 'ThirdParty\\Python3\\Win64\\Scripts\\pip.exe' )
assert os.path.exists(pip_path)

tool_dir = os.path.dirname( os.path.abspath(__file__) )
pip_requirements_path = tool_dir + os.sep + 'requirements.txt'
assert os.path.exists(pip_requirements_path)

# call pip install
r = subprocess.run([python_path, "-m", "pip", 'install', "-r", pip_requirements_path], capture_output=True)
#print(r.stdout.decode())

# call module list
r = subprocess.run([python_path, "-m", "pip", "list"], capture_output=True)
#print(r.stdout.decode())

# test env
if not os.path.dirname(tool_dir) in sys.path:
    sys.path.insert(0, os.path.dirname(tool_dir))

# sys path list
for fp in sys.path:
    print([int(os.path.exists(fp)), fp])

print('.\n=============\nINSTALLATION\'S DONE\n=============')

# Restart U-Editor
system_library = unreal.SystemLibrary
project_dir = system_library.get_project_directory()
u_proj_path_ls = [os.path.join(project_dir, i) for i in os.listdir(project_dir) if i.endswith('.uproject')]
cur_proj = u_proj_path_ls[0]
print(f'Reloading UProject {os.path.basename(cur_proj)}')
subprocess.Popen([sys.executable, cur_proj])
system_library.quit_editor()
