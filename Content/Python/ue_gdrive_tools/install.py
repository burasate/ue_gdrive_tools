# -*- coding: utf-8 -*-
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import config

binaries_dir = config.BINARIES_DIR
python_path = config.PYTHON_PATH
pip_path = config.PIP_PATH
tool_dir = config.ROOT_DIR
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
import unreal, time
system_library = unreal.SystemLibrary
project_dir = system_library.get_project_directory()
u_proj_path_ls = [os.path.join(project_dir, i) for i in os.listdir(project_dir) if i.endswith('.uproject')]
cur_proj = u_proj_path_ls[0]
print(f'Reloading UProject {os.path.basename(cur_proj)}')
subprocess.Popen([sys.executable, cur_proj])
time.sleep(5)
system_library.quit_editor()
